"""The snapshot, the time-reference measurement and the cell table."""

import datetime as dt
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from kaps_analytics.history.schemas import MARKETS_SCHEMA
from kaps_analytics.study.cells import CELL, cell_table
from kaps_analytics.study.dataset import StudyDataError
from kaps_analytics.study.reference import measure_reference
from kaps_analytics.study.snapshot import (
    MAX_MISSING_SHARE,
    build_snapshot,
    days_table,
    window_for,
)
from kaps_analytics.study.synthetic import World, write_world

HOUR = dt.timedelta(hours=1)


def small_world(tmp_path: Path) -> tuple[Path, dict[str, int]]:
    root = tmp_path / "kalshi"
    return root, write_world(World(events=120, trades_per_market=6, seed=11), root)


def edit_markets(root: Path, change: Callable[[dict[str, list[Any]]], None]) -> None:
    path = root / "markets" / "historical" / "part-000000.parquet"
    columns = pq.read_table(path).to_pydict()
    change(columns)
    pq.write_table(pa.table(columns, schema=MARKETS_SCHEMA), path)


# --- snapshot -------------------------------------------------------------------------------------


def test_a_complete_download_gives_a_window_over_all_its_days(tmp_path: Path) -> None:
    root, counts = small_world(tmp_path)
    days = days_table(root)
    assert days["trades"].sum() == counts["trades"]
    assert days["market_missing"].sum() == 0
    window = window_for(days)
    assert window is not None
    first, after_last = window
    assert first == "2026-01-02"
    assert after_last == "2026-01-08"


def test_the_window_ends_before_days_whose_markets_have_not_settled(tmp_path: Path) -> None:
    root, _ = small_world(tmp_path)
    cut = dt.datetime(2026, 1, 6, 12, tzinfo=dt.UTC)

    def forget_late_markets(columns: dict[str, list[Any]]) -> None:
        keep = [i for i, close in enumerate(columns["close_time"]) if close < cut]
        for name in columns:
            columns[name] = [columns[name][i] for i in keep]

    edit_markets(root, forget_late_markets)
    days = days_table(root)
    assert days.filter(pl.col("day") == dt.date(2026, 1, 7))["missing_share"][0] > 0.5
    window = window_for(days)
    assert window is not None
    assert window[1] <= "2026-01-07"  # the days that are mostly unlabelled are left out


def test_no_day_below_the_limit_gives_no_window() -> None:
    days = pl.DataFrame(
        {
            "day": [dt.date(2026, 1, 1)],
            "trades": [10],
            "market_missing": [5],
            "missing_share": [0.5],
        }
    )
    assert window_for(days) is None
    assert MAX_MISSING_SHARE == 0.005


def test_the_snapshot_suggests_the_window_and_a_share_under_the_ceiling(tmp_path: Path) -> None:
    root, counts = small_world(tmp_path)
    snapshot = build_snapshot(root, ceiling=counts["trades"] // 2)
    suggested = snapshot["suggested"]
    assert suggested["window_start"] == "2026-01-02"
    assert suggested["used_trades"] == counts["trades"]
    assert suggested["sample_share"] == pytest.approx(0.5, abs=0.01)
    assert snapshot["exclusions"] == {"used": counts["trades"]}
    assert len(snapshot["trade_days"]) == 6
    assert build_snapshot(root)["suggested"]["sample_share"] == 1.0


def test_the_snapshot_without_a_usable_day_suggests_nothing(tmp_path: Path) -> None:
    root, _ = small_world(tmp_path)

    def forget_all(columns: dict[str, list[Any]]) -> None:
        for name in columns:
            columns[name] = columns[name][:1]

    edit_markets(root, forget_all)
    assert build_snapshot(root)["suggested"] == {"window_start": None, "window_end": None}


# --- the time reference ---------------------------------------------------------------------------


def test_each_field_wins_where_it_sits_nearer_the_last_trade(tmp_path: Path) -> None:
    root, _ = small_world(tmp_path)

    def separate(columns: dict[str, list[Any]]) -> None:
        for i, series in enumerate(columns["series_ticker"]):
            close = columns["close_time"][i]
            if series == "KXSYN0":  # sports: the close time is a week late
                columns["close_time"][i] = close + 7 * 24 * HOUR
            else:  # politics: the expected time is a week late
                columns["expected_expiration_time"][i] = close + 7 * 24 * HOUR

    edit_markets(root, separate)
    table = measure_reference(root)
    nearer = dict(zip(table["category"], table["nearer"], strict=True))
    # the late close_time of the sports markets also pushes them outside the measured days
    assert nearer.get("politics") == "close_time"
    assert table.filter(pl.col("category") == "politics")["expected_median"][0] > 6 * 86400


def test_the_reference_measure_counts_missing_expected_times(tmp_path: Path) -> None:
    root, _ = small_world(tmp_path)

    def blank(columns: dict[str, list[Any]]) -> None:
        columns["expected_expiration_time"] = [None] * len(columns["ticker"])

    edit_markets(root, blank)
    table = measure_reference(root)
    assert all(share == 1.0 for share in table["expected_null"])
    assert all(m > 0 for m in table["markets"])


# --- the cell table -------------------------------------------------------------------------------


def edge_frame() -> pl.LazyFrame:
    """Two events in one cell. Taker edge sums 10 and 30 over 1 and 2 contracts."""
    rows = {
        "price_band": [3, 3, 3],
        "tleft_band": [1, 1, 1],
        "category": ["x", "x", "x"],
        "taker_yes": [True, True, True],
        "event_ticker": ["A", "A", "B"],
    }
    measures = {
        "e_taker": [4, 6, 30],
        "c": [100, 100, 200],
        "e_mk_opt_cons": [0, 0, 0],
        "e_mk_pess_cons": [0, 0, 0],
        "c_pess": [0, 0, 0],
    }
    return pl.DataFrame({**rows, **measures}).lazy()


def test_a_cell_gives_the_ratio_and_the_clustered_standard_error() -> None:
    table = cell_table(edge_frame(), minimum_events=1)
    assert table.height == 1
    row = table.row(0, named=True)
    # sums per event: A (10, 200), B (30, 200); ratio 40 / 400 = 0.1
    assert row["events"] == 2
    assert row["trades"] == 3
    assert row["taker_e6"] == pytest.approx(0.1)
    residuals = (10 - 0.1 * 200) ** 2 + (30 - 0.1 * 200) ** 2  # 100 + 100
    assert row["taker_se_e6"] == pytest.approx(math.sqrt(residuals) / 400)
    assert row["taker_z"] == pytest.approx(0.1 / (math.sqrt(residuals) / 400))


def test_cells_with_too_few_events_are_left_out() -> None:
    assert cell_table(edge_frame(), minimum_events=3).is_empty()


def test_the_cell_columns_are_the_grid() -> None:
    assert CELL == ["price_band", "tleft_band", "category", "taker_yes"]


def test_markets_found_only_in_the_live_folder_are_measured_too(tmp_path: Path) -> None:
    root, _ = small_world(tmp_path)
    source = root / "markets" / "historical" / "part-000000.parquet"
    target = root / "markets" / "live" / "date=2026-01-05" / "markets.parquet"
    target.parent.mkdir(parents=True)
    source.rename(target)
    assert not measure_reference(root).is_empty()


def test_the_reference_measure_needs_some_market_files(tmp_path: Path) -> None:
    root, _ = small_world(tmp_path)
    (root / "markets" / "historical" / "part-000000.parquet").unlink()
    with pytest.raises(StudyDataError, match="markets"):
        measure_reference(root)


def test_report_cents_shows_a_missing_value_as_not_available() -> None:
    from kaps_analytics.study.report import cents

    assert cents(None) == "n/a"
    assert cents(float("nan")) == "n/a"
    assert cents(25_000) == "+2.50"
    assert cents(-10_000) == "-1.00"
