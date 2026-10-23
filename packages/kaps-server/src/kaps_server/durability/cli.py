"""``python -m kaps_server.durability``: the ledger, the writer and the check for the power cut.

Exit codes: 0 fine, 1 bad command line or the writer refused, 2 a check failed.
"""

import argparse
import asyncio
import contextlib
import sys
from collections.abc import Sequence
from pathlib import Path

from kaps_server.durability.ledger import SILENCE_SECONDS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kaps_server.durability", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    led = sub.add_parser("ledger", help="record acknowledged commits (on another machine)")
    led.add_argument("--directory", type=Path, required=True)
    led.add_argument("--host", required=True, help="the address to listen on")
    led.add_argument("--port", type=int, required=True)
    led.add_argument("--silence", type=float, default=SILENCE_SECONDS)
    wri = sub.add_parser("writer", help="commit rows and report each one (on the server host)")
    wri.add_argument("--url", required=True, help="a test database; the guard refuses others")
    wri.add_argument("--run", type=int, required=True, help="a new number for every power cut")
    wri.add_argument("--ledger-host", required=True)
    wri.add_argument("--ledger-port", type=int, required=True)
    wri.add_argument("--seconds", type=float, help="stop after this long (default: until cut)")
    ver = sub.add_parser("verify", help="check the database against every ledger")
    ver.add_argument("--url", required=True)
    ver.add_argument("--ledger-directory", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ledger":
        from kaps_server.durability.ledger import serve_forever

        print(f"ledger listening on {args.host}:{args.port}, writing to {args.directory}")
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(serve_forever(args.directory, args.host, args.port, args.silence))
        return 0
    if args.command == "writer":
        from kaps_server.db.guard import NotATestDatabase
        from kaps_server.durability.writer import WriterRefused, run_writer

        try:
            stats = asyncio.run(
                run_writer(args.url, args.run, args.ledger_host, args.ledger_port, args.seconds)
            )
        except (WriterRefused, NotATestDatabase) as error:
            print(f"REFUSING: {error}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 0
        print(f"done: {stats.summary()}")
        return 0
    from kaps_server.admin.preflight import refused, render
    from kaps_server.db.guard import NotATestDatabase
    from kaps_server.durability.verify import run_verify

    try:
        checks = asyncio.run(run_verify(args.url, args.ledger_directory))
    except NotATestDatabase as error:
        print(f"REFUSING: {error}", file=sys.stderr)
        return 1
    print(render(checks))
    return 2 if refused(checks) else 0
