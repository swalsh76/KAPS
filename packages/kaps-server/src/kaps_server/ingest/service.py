"""The ingest service: the one process that records Kalshi's live data into the database.

``python -m kaps_server.ingest`` runs it under ``systemd`` as the ``kaps`` account. It joins the
pieces built in K1a.5 to K1a.7: the signed feed, the batched writer, discovery, the exchange
poller, the trade backfill and the event pump. Any of them failing for good ends the process with
a non-zero status and ``systemd`` starts it again; the pump then records the outage as gaps from the
last heartbeat, so a crash costs a gap row and not silence.

* **Key.** The data-only key reaches the process only as ``systemd`` credentials (decrypted by the
  machine's TPM into a private directory); no environment variable and no file in ``/etc`` holds it.
* **Database.** The service connects over the local socket as a role of its own that can write the
  ingest tables and change nothing else; peer authentication means it keeps no password.
* **Disk.** There is no retention or governor yet (K1b), so above ``disk_stop_percent`` on the data
  drive the service stops and is *not* restarted (exit status ``EXIT_DISK_FULL``), rather than fill
  the drive under PostgreSQL. The reason is stored in ``ingest_state`` for ``ingest-status``.
"""

import asyncio
import contextlib
import logging
import os
import shutil
import signal
import tomllib
from collections.abc import Awaitable, Callable, Coroutine
from pathlib import Path
from typing import Any, Literal

import asyncpg
from kaps_core.auth import AuthError, DataSigner, load_private_key
from kaps_core.config import Environment, KalshiConfig
from kaps_core.endpoints import MarketData
from kaps_core.rest import KalshiPublicClient
from kaps_core.ws import FeedConfig, KalshiFeed
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from kaps_server.db.migrate import HEAD
from kaps_server.ingest import state
from kaps_server.ingest.backfill import Backfiller
from kaps_server.ingest.discovery import Discovery, DiscoveryRunner
from kaps_server.ingest.exchange import ExchangePoller
from kaps_server.ingest.pump import EventPump
from kaps_server.ingest.writer import IngestWriter, WriterConfig

log = logging.getLogger(__name__)

CONFIG_PATH = "/etc/kaps/ingest.toml"
KEY_ID_CREDENTIAL = "kalshi-key-id"
KEY_CREDENTIAL = "kalshi-private-key"
STOPPED_REASON = "service.stopped_reason"  # why the last run ended, for ingest-status
EXIT_DISK_FULL = 75  # EX_TEMPFAIL: the unit lists it in RestartPreventExitStatus
EXIT_REFUSED = 78  # EX_CONFIG: a prerequisite is wrong; restarting would not help
CHANNELS = (
    "ticker",
    "trade",
    "market_lifecycle_v2",
)  # every non-combo market, no order-book deltas


class ServiceError(Exception):
    """The service cannot start; the message says what to fix."""


class DiskFull(Exception):
    """The data drive is above the stop level."""


class ServiceConfig(BaseModel):
    """``/etc/kaps/ingest.toml``, rendered by ``kaps-admin install`` from the answer file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Literal["production"]  # the demo site has no live market data worth recording
    socket_directory: str = Field(pattern=r"^/[^\s]*$")
    port: int = Field(ge=1024, le=65535)
    database: str = Field(pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    role: str = Field(pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    data_directory: str = Field(pattern=r"^/[^\s]*$")  # the drive the disk guard watches
    disk_stop_percent: int = Field(default=90, ge=50, le=99)
    disk_check_seconds: float = Field(default=60.0, gt=0)
    backfill_rate_per_second: float = Field(default=2.0, gt=0)  # the shares of PLAN decision 22
    discovery_rate_per_second: float = Field(default=1.5, gt=0)


def parse_config(text: str) -> ServiceConfig:
    try:
        return ServiceConfig.model_validate(tomllib.loads(text))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise ServiceError(f"{CONFIG_PATH} is not valid: {error}") from error


def load_signer(credentials: Path | None) -> DataSigner:
    """The data key from the credentials directory ``systemd`` provides (never printed)."""
    if credentials is None:
        raise ServiceError("no credentials directory: run the service from its systemd unit")
    try:
        key_id = (credentials / KEY_ID_CREDENTIAL).read_text(encoding="utf-8").strip()
        return DataSigner(key_id, load_private_key(credentials / KEY_CREDENTIAL))
    except (OSError, AuthError):
        # the message must not carry the path or the cause: either could name the key
        raise ServiceError(
            f"the data key credentials ({KEY_ID_CREDENTIAL}, {KEY_CREDENTIAL}) are missing or "
            "unusable; see the server guide, step 'The ingest service'"
        ) from None


def used_percent(path: str, usage: Callable[[str], Any] = shutil.disk_usage) -> float:
    total = usage(path)
    return float(100.0 * total.used / total.total)


async def disk_guard(
    config: ServiceConfig,
    *,
    usage: Callable[[str], Any] = shutil.disk_usage,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Raise ``DiskFull`` once the data drive is at or above the stop level."""
    while True:
        percent = used_percent(config.data_directory, usage)
        if percent >= config.disk_stop_percent:
            raise DiskFull(
                f"{config.data_directory} is {percent:.1f}% full, at or above "
                f"{config.disk_stop_percent}%"
            )
        await sleep(config.disk_check_seconds)


Connect = Callable[[], Awaitable[asyncpg.Connection]]


def connector(config: ServiceConfig) -> Connect:
    async def connect() -> asyncpg.Connection:
        return await asyncpg.connect(
            host=config.socket_directory,
            port=config.port,
            user=config.role,
            database=config.database,
        )

    return connect


async def check_schema(connect: Connect) -> None:
    """Refuse to run against a database the migrations have not brought to this release."""
    conn = await connect()
    try:
        found = await conn.fetchval("SELECT version_num FROM alembic_version")
    finally:
        await conn.close()
    if found != HEAD:
        raise ServiceError(
            f"the database is at revision {found!r} but this release needs {HEAD!r}: "
            "run kaps-admin migrate first"
        )


async def record_stop(connect: Connect, reason: str) -> None:
    with contextlib.suppress(Exception):  # the reason is a courtesy; never mask the real exit
        conn = await connect()
        try:
            await state.put(conn, STOPPED_REASON, reason[:300])
        finally:
            await conn.close()


async def run_service(
    config: ServiceConfig,
    signer: DataSigner,
    stop: asyncio.Event,
    *,
    connect: Connect | None = None,
    feed: Any | None = None,
    market_data: tuple[Any, Any] | None = None,
    writer_config: WriterConfig | None = None,
    guard: Callable[[], Coroutine[Any, Any, None]] | None = None,
) -> None:
    """Run until ``stop`` is set (a clean stop) or a part fails for good (raises).

    The keyword arguments let the tests supply fakes; ``systemd`` runs it with none of them.
    """
    connect = connect or connector(config)
    await check_schema(connect)
    await record_stop(connect, "running")
    async with contextlib.AsyncExitStack() as stack:
        if market_data is None:
            environment = Environment(config.environment)
            clients = []
            for rate in (config.backfill_rate_per_second, config.discovery_rate_per_second):
                settings = KalshiConfig(
                    environment=environment, rate_limit_per_second=rate, burst_requests=rate
                )
                clients.append(await stack.enter_async_context(KalshiPublicClient(settings)))
            market_data = (MarketData(clients[0]), MarketData(clients[1]))
        backfill_data, other_data = market_data
        feed = feed or KalshiFeed(signer, FeedConfig())
        writer = await stack.enter_async_context(IngestWriter(connect, writer_config))
        backfiller = Backfiller(backfill_data, writer, connect)
        discovery = DiscoveryRunner(Discovery(other_data, connect))
        poller = ExchangePoller(other_data, connect)
        pump = EventPump(feed, writer, connect, backfiller, discovery)
        await feed.start()
        for channel in CHANNELS:
            await feed.subscribe(channel)
        pump_task = asyncio.create_task(pump.run(), name="pump")
        helpers = [
            asyncio.create_task(backfiller.run(), name="backfill"),
            asyncio.create_task(discovery.run(), name="discovery"),
            asyncio.create_task(poller.run(), name="exchange"),
            asyncio.create_task((guard or (lambda: disk_guard(config)))(), name="disk"),
        ]
        waiter = asyncio.create_task(stop.wait(), name="stop")
        everything = {pump_task, waiter, *helpers}
        failure: BaseException | None = None
        try:
            done, _ = await asyncio.wait(everything, return_when=asyncio.FIRST_COMPLETED)
            for task in done - {waiter}:
                failure = failure or task.exception() or ServiceError(f"{task.get_name()} ended")
        finally:
            # the feed closes first, so the pump drains what it already holds and saves the
            # heartbeat; then the helpers stop; the writer flushes as the stack unwinds
            await feed.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(asyncio.shield(pump_task), 30)
            for task in [*helpers, waiter, pump_task]:
                task.cancel()
            await asyncio.gather(*helpers, waiter, pump_task, return_exceptions=True)
        if failure is not None:
            raise failure


async def supervise(
    config: ServiceConfig, signer: DataSigner, stop: asyncio.Event, **parts: Any
) -> int:
    """Run the service and turn how it ended into the process's exit status and its stored reason.

    ``parts`` are the fakes ``run_service`` accepts; the process passes none."""
    connect = parts.pop("connect", None) or connector(config)
    try:
        await run_service(config, signer, stop, connect=connect, **parts)
    except DiskFull as error:
        log.error("stopping, and not restarting: %s", error)
        await record_stop(connect, f"disk full: {error}")
        return EXIT_DISK_FULL
    except ServiceError as error:
        log.error("%s", error)
        return EXIT_REFUSED
    except Exception as error:
        log.exception("the ingest failed")
        await record_stop(connect, f"failed: {type(error).__name__}: {error}")
        return 1
    await record_stop(connect, "stopped cleanly")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )  # journald adds the time
    config_path = Path((argv or [CONFIG_PATH])[0])
    try:
        config = parse_config(config_path.read_text(encoding="utf-8"))
        credentials = os.environ.get("CREDENTIALS_DIRECTORY")
        signer = load_signer(Path(credentials) if credentials else None)
    except (OSError, ServiceError) as error:
        log.error("%s", error)
        return EXIT_REFUSED

    async def run() -> int:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signum, stop.set)
        return await supervise(config, signer, stop)

    return asyncio.run(run())
