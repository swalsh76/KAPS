"""``kaps-admin``: the command line for a production role.

    kaps-admin preflight [--answers install.toml]
    kaps-admin install --answers install.toml [--dry-run]     (as root)
    kaps-admin verify --answers install.toml
    kaps-admin migrate --answers install.toml                 (as the service account)

``preflight`` and ``verify`` are read-only. ``install`` runs only from an answer file, never
prompts, and is idempotent: a second run changes nothing. ``migrate`` brings the ``kaps``
database to the newest schema over the local socket. Exit codes: 0 fine, 1 bad command line,
answer file or a step that failed, 2 a check refused or failed, 3 the role is not available yet.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from kaps_server.admin import managed
from kaps_server.admin.answers import Answers, AnswersError, RoleUnavailable, load_answers
from kaps_server.admin.install import (
    InstallRefused,
    plan_install,
    render_outcomes,
    render_plan,
    run_install,
)
from kaps_server.admin.preflight import refused, render, run_preflight
from kaps_server.admin.system import Host, LocalHost, LocalSystem, System
from kaps_server.admin.verify import run_verify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kaps-admin", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="read-only checks; changes nothing")
    pre.add_argument("--answers", type=Path, help="also check the budget, ports and share")
    inst = sub.add_parser("install", help="install from an answer file (as root)")
    inst.add_argument("--answers", type=Path, required=True)
    inst.add_argument("--dry-run", action="store_true", help="validate and print the plan only")
    ver = sub.add_parser("verify", help="read-only: is the machine what install would make")
    ver.add_argument("--answers", type=Path, required=True)
    mig = sub.add_parser("migrate", help="bring the database to the newest schema")
    mig.add_argument("--answers", type=Path, required=True)
    return parser


def _preflight(answers: Answers | None, system: System) -> int:
    answers_for_host = answers.database_host if answers is not None else None
    checks = run_preflight(system, answers_for_host)
    print(render(checks))
    return 2 if refused(checks) else 0


def _install(answers: Answers, dry_run: bool, host: Host) -> int:
    steps = plan_install(answers)  # raises RoleUnavailable for a role that cannot be installed
    if dry_run:
        print(render_plan(steps))
        print("Dry run: nothing was changed.")
        return 0
    try:
        print(render_outcomes(run_install(host, answers)))
    except InstallRefused as error:
        print(f"REFUSING: {error}", file=sys.stderr)
        return 2
    return 0


def _verify(answers: Answers, host: Host) -> int:
    checks = run_verify(host, answers.installable_host())
    print(render(checks))
    return 2 if refused(checks) else 0


def _migrate(answers: Answers) -> int:
    from kaps_server.db.migrate import current_revision, upgrade

    config = answers.installable_host()
    url = (
        f"postgresql+asyncpg://{managed.OWNER_ROLE}@/{managed.DATABASE}"
        f"?host={managed.SOCKET_DIRECTORY}&port={config.postgres.port}"
    )
    upgrade(url)
    print(f"the {managed.DATABASE} database is at revision {current_revision(url)}")
    return 0


def main(argv: Sequence[str] | None = None, system: System | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "preflight":
            answers = load_answers(args.answers) if args.answers is not None else None
            return _preflight(answers, system or LocalSystem())
        answers = load_answers(args.answers)
        host = cast(Host, system) if system is not None else LocalHost()
        if args.command == "install":
            return _install(answers, args.dry_run, host)
        if args.command == "verify":
            return _verify(answers, host)
        return _migrate(answers)
    except AnswersError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except RoleUnavailable as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
