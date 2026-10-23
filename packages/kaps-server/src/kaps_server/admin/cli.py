"""``kaps-admin``: the command line for a production role.

    kaps-admin preflight [--answers install.toml]
    kaps-admin install --answers install.toml --dry-run

``preflight`` is read-only and refuses ("REFUSING") when a prerequisite is missing. ``install`` runs
only from an answer file and never prompts. In K1a.1 it validates the file and prints its plan;
the install itself arrives in K1a.2. Exit codes: 0 fine, 1 bad command line or answer file,
2 preflight refused, 3 the role is not available yet.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from kaps_server.admin.answers import Answers, AnswersError, RoleUnavailable, load_answers
from kaps_server.admin.install import plan_install, render_plan
from kaps_server.admin.preflight import refused, render, run_preflight
from kaps_server.admin.system import LocalSystem, System


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kaps-admin", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="read-only checks; changes nothing")
    pre.add_argument("--answers", type=Path, help="also check the budget, ports and share")
    inst = sub.add_parser("install", help="install from an answer file")
    inst.add_argument("--answers", type=Path, required=True)
    inst.add_argument("--dry-run", action="store_true", help="validate and print the plan only")
    return parser


def _preflight(answers: Answers | None, system: System) -> int:
    answers_for_host = answers.database_host if answers is not None else None
    checks = run_preflight(system, answers_for_host)
    print(render(checks))
    return 2 if refused(checks) else 0


def _install(answers: Answers, dry_run: bool) -> int:
    steps = plan_install(answers)  # raises RoleUnavailable for a role that cannot be installed
    if not dry_run:
        print("error: the real install is built in K1a.2; use --dry-run for now", file=sys.stderr)
        return 1
    print(render_plan(steps))
    print("Dry run: nothing was changed.")
    return 0


def main(argv: Sequence[str] | None = None, system: System | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "preflight":
            answers = load_answers(args.answers) if args.answers is not None else None
            return _preflight(answers, system or LocalSystem())
        return _install(load_answers(args.answers), args.dry_run)
    except AnswersError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except RoleUnavailable as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
