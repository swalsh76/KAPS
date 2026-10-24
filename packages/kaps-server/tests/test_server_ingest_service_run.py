"""The ingest service run as a whole against a real PostgreSQL, with a fake feed and a quiet Kalshi,
and the ingest role: it does what the ingest needs and nothing else."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import asyncpg
import pytest
from dbhelpers import dsn
from ingestfixtures import lifecycle, ticker, trade
from kaps_core.endpoints import TypedPage
from kaps_core.models import ExchangeSchedule, ExchangeStatus
from kaps_core.ws import FeedEvent
from kaps_server.admin import managed
from kaps_server.db.migrate import HEAD
from kaps_server.ingest import state
from kaps_server.ingest.service import (
    CHANNELS,
    STOPPED_REASON,
    DiskFull,
    ServiceConfig,
    ServiceError,
    check_schema,
    parse_config,
    record_stop,
    run_service,
)
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.db

CONFIG = parse_config(
    'environment = "production"\nsocket_directory = "/unused"\nport = 5432\n'
    'database = "kaps"\nrole = "kaps_ingest"\ndata_directory = "/"\n'
)


class LiveFeed:
    """What run_service needs from the feed: start, subscribe, events until closed, close."""

    def __init__(self, *events: FeedEvent | Exception) -> None:
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        for event in events:
            self.queue.put_nowait(event)
        self.started = self.closed = False
        self.subscribed: list[tuple[str, list[str] | None]] = []

    async def start(self) -> None:
        self.started = True

    async def subscribe(self, channel: str, market_tickers: list[str] | None = None) -> int:
        self.subscribed.append((channel, market_tickers))
        return len(self.subscribed)

    async def close(self) -> None:
        self.closed = True
        self.queue.put_nowait(None)

    async def events(self) -> AsyncIterator[FeedEvent]:
        while True:
            item = await self.queue.get()
            if item is None:
                return
            if isinstance(item, Exception):
                raise item
            yield item

    def channel_of(self, sid: int) -> str | None:
        return {1: "ticker", 2: "trade", 3: "market_lifecycle_v2"}.get(sid)


class QuietData:
    """A Kalshi with nothing new to say: empty listings, an open exchange, no trades."""

    async def markets(self, **_: Any) -> AsyncIterator[TypedPage[Any]]:
        page: TypedPage[Any]
        for page in ():
            yield page

    async def series_list(self) -> list[Any]:
        return []

    async def series_fee_changes(self) -> list[Any]:
        return []

    async def exchange_status(self) -> ExchangeStatus:
        return ExchangeStatus.model_validate(
            {"exchange_active": True, "trading_active": True, "exchange_index_statuses": []}
        )

    async def exchange_schedule(self) -> ExchangeSchedule:
        return ExchangeSchedule.model_validate({"standard_hours": [], "maintenance_windows": []})

    async def historical_cutoff(self) -> Any:
        raise RuntimeError("no backfill is expected")

    def trades(self, **_: Any) -> AsyncIterator[Any]:
        raise RuntimeError("no backfill is expected")


def connector(url: str, **login: Any) -> Callable[[], Awaitable[asyncpg.Connection]]:
    async def connect() -> asyncpg.Connection:
        if login:
            return await asyncpg.connect(**login)
        return await asyncpg.connect(dsn(url))

    return connect


async def rows(url: str, statement: str, *args: Any) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(dsn(url))
    try:
        return list(await conn.fetch(statement, *args))
    finally:
        await conn.close()


async def never() -> None:
    await asyncio.Event().wait()


async def until(check: Callable[[], Awaitable[bool]], seconds: float = 10.0) -> bool:
    for _ in range(int(seconds / 0.05)):
        if await check():
            return True
        await asyncio.sleep(0.05)
    return False


async def run_until_stopped(
    url: str, feed: LiveFeed, wait_for: str, *, connect: Any = None, config: ServiceConfig = CONFIG
) -> None:
    """Run the service, wait until ``wait_for`` (a SQL query) returns a row, then stop it."""
    stop = asyncio.Event()
    connect = connect or connector(url)
    task = asyncio.create_task(
        run_service(
            config, None, stop,  # type: ignore[arg-type]
            connect=connect, feed=feed, market_data=(QuietData(), QuietData()), guard=never,
        )
    )  # fmt: skip

    async def arrived() -> bool:
        return bool(await rows(url, wait_for)) or task.done()

    try:
        await until(arrived)
    finally:
        stop.set()
    await asyncio.wait_for(task, 30)


# --- a whole run ----------------------------------------------------------------------------------


async def test_the_service_records_what_the_feed_delivers_and_stops_cleanly(migrated: str) -> None:
    feed = LiveFeed(ticker(), trade("t-1"), lifecycle())
    await run_until_stopped(
        migrated, feed, "SELECT 1 FROM trade JOIN ticker USING (ticker) LIMIT 1"
    )
    assert feed.started and feed.closed
    assert [c for c, _ in feed.subscribed] == list(CHANNELS)
    assert all(tickers is None for _, tickers in feed.subscribed)  # every market
    assert [r["trade_id"] for r in await rows(migrated, "SELECT trade_id FROM trade")] == ["t-1"]
    beat = await rows(migrated, "SELECT value FROM ingest_state WHERE key = $1", state.HEARTBEAT)
    assert beat and int(beat[0]["value"]) > 0  # the pump saved a heartbeat as it closed
    reason = await rows(migrated, "SELECT value FROM ingest_state WHERE key = $1", STOPPED_REASON)
    assert reason[0]["value"] == "running"  # main() writes the final word, not run_service


async def test_a_full_disk_ends_the_run_with_disk_full_and_closes_the_feed(migrated: str) -> None:
    feed = LiveFeed()

    async def full() -> None:
        await asyncio.sleep(0.2)
        raise DiskFull("the data drive is 91.0% full")

    with pytest.raises(DiskFull):
        await asyncio.wait_for(
            run_service(
                CONFIG, None, asyncio.Event(),  # type: ignore[arg-type]
                connect=connector(migrated), feed=feed,
                market_data=(QuietData(), QuietData()), guard=full,
            ),
            30,
        )  # fmt: skip
    assert feed.closed


async def test_a_part_that_fails_for_good_ends_the_run_so_systemd_restarts_it(
    migrated: str,
) -> None:
    feed = LiveFeed(RuntimeError("the feed fell over"))
    with pytest.raises(RuntimeError, match="fell over"):
        await asyncio.wait_for(
            run_service(
                CONFIG, None, asyncio.Event(),  # type: ignore[arg-type]
                connect=connector(migrated), feed=feed,
                market_data=(QuietData(), QuietData()), guard=never,
            ),
            30,
        )  # fmt: skip
    assert feed.closed


async def test_a_database_the_migrations_have_not_reached_is_refused_before_the_feed_starts(
    migrated: str,
) -> None:
    await rows(migrated, "UPDATE alembic_version SET version_num = '0001'")
    feed = LiveFeed()
    try:
        with pytest.raises(ServiceError, match="kaps-admin migrate"):
            await run_service(
                CONFIG, None, asyncio.Event(),  # type: ignore[arg-type]
                connect=connector(migrated), feed=feed,
                market_data=(QuietData(), QuietData()), guard=never,
            )  # fmt: skip
    finally:  # the next test's downgrade must find the revision the tables are really at
        await rows(migrated, f"UPDATE alembic_version SET version_num = '{HEAD}'")
    assert not feed.started


async def test_the_final_word_is_stored_and_a_failure_to_store_it_hides_nothing(
    migrated: str,
) -> None:
    await record_stop(connector(migrated), "disk full: 91%")
    stored = await rows(migrated, "SELECT value FROM ingest_state WHERE key = $1", STOPPED_REASON)
    assert stored[0]["value"] == "disk full: 91%"

    async def broken() -> asyncpg.Connection:
        raise OSError("the database is away")

    await record_stop(broken, "failed")  # must not raise


async def test_the_schema_check_accepts_the_current_revision(migrated: str) -> None:
    await check_schema(connector(migrated))


# --- the ingest role ------------------------------------------------------------------------------

ROLE, PASSWORD = "kaps_ingest_t", "ingest-test-pw"  # noqa: S105 (a throwaway test role)


@pytest.fixture
async def ingest_login(migrated: str) -> AsyncIterator[dict[str, Any]]:
    """A login for a role with exactly the grants install gives the ingest role."""
    url = make_url(migrated)
    owner = url.username or "postgres"
    admin = await asyncpg.connect(dsn(migrated))
    try:
        if await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", ROLE):
            await admin.execute(f"DROP OWNED BY {ROLE}")  # left by an interrupted run
            await admin.execute(f"DROP ROLE {ROLE}")
        await admin.execute(f"CREATE ROLE {ROLE} LOGIN PASSWORD '{PASSWORD}'")  # noqa: S608
        check = managed.render_ingest_grants_check(ROLE, str(url.database), owner)
        assert await admin.fetchval(check) > 0  # before the grants, privileges are missing
        await admin.execute(managed.render_ingest_grants(ROLE, str(url.database), owner))
        assert await admin.fetchval(check) == 0  # and after, none is
        host = url.query.get("host") or url.host
        yield {
            "host": host, "port": url.port, "user": ROLE, "password": PASSWORD,
            "database": url.database,
        }  # fmt: skip
        await admin.execute(f"DROP OWNED BY {ROLE}")
        await admin.execute(f"DROP ROLE {ROLE}")
    finally:
        await admin.close()


async def test_the_whole_service_runs_as_the_ingest_role(
    migrated: str, ingest_login: dict[str, Any]
) -> None:
    feed = LiveFeed(ticker(), trade("t-9"), lifecycle())
    await run_until_stopped(
        migrated,
        feed,
        "SELECT 1 FROM trade JOIN ticker USING (ticker) LIMIT 1",
        connect=connector(migrated, **ingest_login),
    )
    assert [r["trade_id"] for r in await rows(migrated, "SELECT trade_id FROM trade")] == ["t-9"]
    assert await rows(migrated, "SELECT 1 FROM market_lifecycle")  # the lifecycle frame was kept


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE intruder (x int)",
        "DELETE FROM trade",
        "TRUNCATE trade",
        "DROP TABLE gap_log",
        "ALTER TABLE trade ADD COLUMN y int",
        "UPDATE alembic_version SET version_num = '0000'",
        "CREATE ROLE intruder",
    ],
)
async def test_the_ingest_role_can_change_nothing_else(
    migrated: str, ingest_login: dict[str, Any], statement: str
) -> None:
    conn = await asyncpg.connect(**ingest_login)
    try:
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(statement)
        # and what it does need still works
        await conn.execute("SELECT version_num FROM alembic_version")
    finally:
        await conn.close()


async def test_tables_a_later_migration_creates_are_open_to_the_ingest_role_at_once(
    migrated: str, ingest_login: dict[str, Any]
) -> None:
    admin = await asyncpg.connect(dsn(migrated))
    conn = await asyncpg.connect(**ingest_login)
    try:
        # default privileges cover tables the owner creates, which is how migrations run
        await admin.execute("CREATE TABLE later_table (x int)")
        await conn.execute("INSERT INTO later_table VALUES (1)")
    finally:
        await conn.close()
        await admin.execute("DROP TABLE IF EXISTS later_table")
        await admin.close()
