"""What the downloaded data holds, and the window and sample the run should use (D16, D17).

The snapshot is the manifest of a run: the days of trades present, how many trades have no market
record yet (markets that had not settled when the market listing ran), and the exclusion counts.
The window ends at the newest day where fewer than 0.5% of the trades lack a market record, and the
sample share keeps about ``ceiling`` trades.
"""

import datetime as dt
from pathlib import Path
from typing import Any, cast

import polars as pl

from kaps_analytics.study.config import StudyConfig
from kaps_analytics.study.dataset import exclusion_counts, tag_trades, used
from kaps_analytics.study.sample import DEFAULT_CEILING, share_for

MAX_MISSING_SHARE = 0.005  # D17


def days_table(root: Path) -> pl.DataFrame:
    """Per day of trades: trades, trades with no market record, and that share."""
    tagged = tag_trades(root, StudyConfig())
    return (
        tagged.group_by(pl.col("t").dt.date().alias("day"))
        .agg(
            pl.len().alias("trades"),
            (pl.col("exclusion") == "market_missing").sum().alias("market_missing"),
        )
        .with_columns((pl.col("market_missing") / pl.col("trades")).alias("missing_share"))
        .sort("day")
        .collect()
    )


def window_for(days: pl.DataFrame) -> tuple[str, str] | None:
    """The first and one past the last day of the window, or None when no day qualifies.

    The window starts at the oldest day present (an event that opened on or after it has all its
    trades) and ends after the newest day whose missing share is below the limit.
    """
    ready = days.filter(pl.col("missing_share") < MAX_MISSING_SHARE)
    if ready.is_empty():
        return None
    first = cast(dt.date, days["day"].min())  # the column is dates, so these are dates
    last = cast(dt.date, ready["day"].max())
    return first.isoformat(), (last + dt.timedelta(days=1)).isoformat()


def build_snapshot(root: Path, ceiling: int = DEFAULT_CEILING) -> dict[str, Any]:
    days = days_table(root)
    suggestion: dict[str, Any] = {"window_start": None, "window_end": None}
    window = window_for(days)
    if window is not None:
        config = StudyConfig(window_start=window[0], window_end=window[1])
        trades = int(used(tag_trades(root, config)).select(pl.len()).collect().item())
        suggestion = {
            "window_start": window[0],
            "window_end": window[1],
            "used_trades": trades,
            "ceiling": ceiling,
            "sample_share": share_for(trades, ceiling),
        }
    return {
        "root_name": root.name,
        "polars_version": pl.__version__,
        "trade_days": days.to_dicts(),
        "exclusions": exclusion_counts(tag_trades(root, StudyConfig())),
        "suggested": suggestion,
    }
