"""Command line for the edge study (K0.5.6).

    python -m kaps_analytics.study snapshot
    python -m kaps_analytics.study reference
    python -m kaps_analytics.study explore  --window-start D --window-end D --fit-end D
        --validate-end D [--share S]
    python -m kaps_analytics.study register --segments FILE --window-start D --window-end D
        --fit-end D --validate-end D --share S
    python -m kaps_analytics.study verdict  --segments FILE --window-start D --window-end D
        --fit-end D --validate-end D --share S --open-test
    python -m kaps_analytics.study report   [--out FILE]

Run it on the analytics node against the downloaded history (``--data-dir`` or ``KAPS_DATA_DIR``;
the study's outputs go in ``<data-dir>/study``, never in git). ``snapshot`` and ``reference`` read
everything; ``explore`` reads only the fit and validate parts; ``register`` only checks a segments
file; ``verdict`` is the one command that opens the test part, and refuses to run without
``--open-test`` and without every setting spelled out, because the pre-registration it locks must
be exactly the one that was approved. Exit codes: 0 fine, 1 bad command line or data.
"""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import polars as pl

from kaps_analytics.study import ladder as ladder_module
from kaps_analytics.study import report
from kaps_analytics.study.calibration import calibration_table
from kaps_analytics.study.cells import cell_table
from kaps_analytics.study.config import StudyConfig
from kaps_analytics.study.dataset import StudyDataError, exclusion_counts, tag_trades, used
from kaps_analytics.study.reference import measure_reference
from kaps_analytics.study.sample import DEFAULT_CEILING, share_for
from kaps_analytics.study.segments import Prereg, PreregistrationError, Segment
from kaps_analytics.study.session import Study
from kaps_analytics.study.snapshot import build_snapshot
from kaps_analytics.study.split import SplitError

COMMANDS = ("snapshot", "reference", "explore", "register", "verdict", "report")


class UsageError(Exception):
    """A bad or incomplete command line."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kaps_analytics.study", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path(os.environ.get("KAPS_DATA_DIR", "data"))
    )
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--window-start", help="UTC date; events opened on or after it")
    parser.add_argument("--window-end", help="UTC date; events closed before it")
    parser.add_argument("--fit-end", help="UTC date; events closing before it are the fit part")
    parser.add_argument("--validate-end", help="UTC date; events closing before it are validate")
    parser.add_argument(
        "--share", type=float, help="share of events sampled (default: from the ceiling)"
    )
    parser.add_argument("--max-trades", type=int, default=DEFAULT_CEILING)
    parser.add_argument("--sample-seed", type=int, default=1)
    parser.add_argument("--resamples", type=int, default=10_000)
    parser.add_argument("--min-events", type=int, default=300)
    parser.add_argument("--segments", type=Path, help="JSON file of the pre-registered segments")
    parser.add_argument("--open-test", action="store_true", help="allow verdict to open the test")
    parser.add_argument("--out", type=Path, help="report: write to this file instead of stdout")
    return parser


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _config(args: argparse.Namespace, root: Path, *, explicit: bool) -> StudyConfig:
    """The study's settings; ``explicit`` demands that nothing is worked out from the data."""
    if explicit and (args.window_start is None or args.window_end is None or args.share is None):
        raise UsageError("--window-start, --window-end and --share must all be given")
    if args.fit_end is None or args.validate_end is None:
        raise UsageError("--fit-end and --validate-end must both be given")
    base = StudyConfig(
        window_start=args.window_start,
        window_end=args.window_end,
        fit_end=args.fit_end,
        validate_end=args.validate_end,
        sample_seed=args.sample_seed,
        resamples=args.resamples,
        min_events=args.min_events,
    )
    share = args.share
    if share is None:
        trades = int(used(tag_trades(root, base)).select(pl.len()).collect().item())
        share = share_for(trades, args.max_trades)
    return StudyConfig(
        window_start=args.window_start,
        window_end=args.window_end,
        fit_end=args.fit_end,
        validate_end=args.validate_end,
        sample_share=share,
        sample_seed=args.sample_seed,
        resamples=args.resamples,
        min_events=args.min_events,
    )


def _segments(path: Path | None) -> tuple[Segment, ...]:
    if path is None:
        raise UsageError("--segments is required")
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        Segment(**{k: v for k, v in item.items() if k != "reason"}) for item in data["segments"]
    )


def _study(
    args: argparse.Namespace, root: Path, out: Path, *, explicit: bool
) -> tuple[Study, StudyConfig]:
    config = _config(args, root, explicit=explicit)
    return Study(tag_trades(root, config), config, out / "prereg-ledger.json"), config


def _snapshot(args: argparse.Namespace, root: Path, out: Path) -> int:
    snapshot = build_snapshot(
        root, ceiling=args.max_trades, window_start=args.window_start, window_end=args.window_end
    )
    _write_json(out / "snapshot.json", snapshot)
    print(report.snapshot_section(snapshot))
    return 0


def _reference(args: argparse.Namespace, root: Path, out: Path) -> int:
    table = measure_reference(root)
    _write_json(out / "reference.json", table.to_dicts())
    print(report.reference_section(table.to_dicts()))
    return 0


def _explore(args: argparse.Namespace, root: Path, out: Path) -> int:
    study, config = _study(args, root, out, explicit=False)
    tagged = tag_trades(root, config)
    cells = cell_table(study.validate)
    out.mkdir(parents=True, exist_ok=True)
    cells.write_csv(out / "cells-validate.csv")
    result: dict[str, Any] = {
        "config": asdict(config),
        "digest": config.digest(),
        "split": {
            "events": study.boundaries.events,
            "fit_end": study.boundaries.fit_end,
            "validate_end": study.boundaries.validate_end,
        },
        "exclusions": exclusion_counts(tagged),
        "calibration_fit": calibration_table(study.fit, ["price_band"]).to_dicts(),
        "calibration_validate": calibration_table(study.validate, ["price_band"]).to_dicts(),
        "calibration_by_category_validate": calibration_table(
            study.validate, ["category"]
        ).to_dicts(),
        "ladder_validate": asdict(ladder_module.ladder(study.fit, study.validate)),
    }
    _write_json(out / "explore.json", result)
    print(f"config {config.digest()[:12]}  split {study.boundaries.events}")
    print(report.ladder_section(result["ladder_validate"]))
    print(cells.head(15))
    return 0


def _prereg(args: argparse.Namespace, root: Path) -> Prereg:
    config = _config(args, root, explicit=True)
    return Prereg(_segments(args.segments), config)


def _register(args: argparse.Namespace, root: Path, out: Path) -> int:
    prereg = _prereg(args, root)
    print(f"{len(prereg.segments)} segments, one-sided tail each {prereg.alpha():.5f}")
    print(f"pre-registration digest {prereg.digest()}")
    return 0


def _verdict(args: argparse.Namespace, root: Path, out: Path) -> int:
    if not args.open_test:
        raise UsageError("verdict opens the test part: pass --open-test to confirm")
    prereg = _prereg(args, root)
    study = Study(tag_trades(root, prereg.config), prereg.config, out / "prereg-ledger.json")
    verdict = study.verdict(prereg)
    result: dict[str, Any] = {
        "digest": prereg.digest(),
        "config": asdict(prereg.config),
        "verdict": asdict(verdict),
        "ladder": asdict(study.ladder(prereg)),
    }
    _write_json(out / "verdict.json", result)
    print(report.verdict_section(result["verdict"]))
    return 0


def _report(args: argparse.Namespace, root: Path, out: Path) -> int:
    text = report.render(out)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.data_dir / "kalshi"
    out = args.data_dir / "study"
    handlers = {
        "snapshot": _snapshot,
        "reference": _reference,
        "explore": _explore,
        "register": _register,
        "verdict": _verdict,
        "report": _report,
    }
    try:
        return handlers[args.command](args, root, out)
    except (UsageError, StudyDataError, SplitError, PreregistrationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
