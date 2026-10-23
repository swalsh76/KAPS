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


def propose_split(
    root: Path, window_start: str, window_end: str, fractions: tuple[float, float, float]
) -> tuple[str, str] | None:
    """Fixed fit and validate boundary dates (D12), from the downloaded markets.

    The markets are complete for the whole window long before its trades are, so the boundaries
    taken from them are final today and do not move as trade days arrive. They are the close-time
    quantiles, by event count, of the settled events that traded and lie inside the window, rounded
    down to a UTC date. None when the events are too few to give two distinct dates.
    """
    columns = ["event_ticker", "label", "volume_e2", "open_time", "created_time"]
    columns += ["close_time", "expected_expiration_time"]
    parts = []
    historical = root / "markets" / "historical"
    if any(historical.glob("part-*.parquet")):
        parts.append(pl.scan_parquet(historical / "part-*.parquet").select(columns))
    live = root / "markets" / "live"
    if any(live.glob("date=*/markets.parquet")):
        parts.append(pl.scan_parquet(live / "date=*" / "markets.parquet").select(columns))
    if not parts:
        return None
    start = dt.datetime.fromisoformat(window_start).replace(tzinfo=dt.UTC)
    end = dt.datetime.fromisoformat(window_end).replace(tzinfo=dt.UTC)
    closes = (
        pl.concat(parts)
        .filter(pl.col("label").is_in(["yes", "no"]) & (pl.col("volume_e2") > 0))
        .group_by("event_ticker")
        .agg(
            pl.coalesce("open_time", "created_time").min().alias("ev_open"),
            pl.coalesce("close_time", "expected_expiration_time").max().alias("ev_close"),
        )
        .filter((pl.col("ev_open") >= start) & (pl.col("ev_close") < end))
        .sort("ev_close")
        .select("ev_close")
        .collect()["ev_close"]
    )
    n = closes.len()
    if n < 3:
        return None
    first, second, _ = fractions
    fit = cast(dt.datetime, closes[min(n - 1, int(first * n))]).date()
    validate = cast(dt.datetime, closes[min(n - 1, int((first + second) * n))]).date()
    if fit >= validate:
        return None
    return fit.isoformat(), validate.isoformat()


def build_snapshot(
    root: Path,
    ceiling: int = DEFAULT_CEILING,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, Any]:
    """The manifest; a window given by the caller is used as it stands, else the one proposed."""
    days = days_table(root)
    suggestion: dict[str, Any] = {"window_start": None, "window_end": None}
    window = (window_start, window_end) if window_start and window_end else window_for(days)
    if window is not None:
        config = StudyConfig(window_start=window[0], window_end=window[1])
        trades = int(used(tag_trades(root, config)).select(pl.len()).collect().item())
        split = propose_split(root, window[0], window[1], config.fractions)
        suggestion = {
            "window_start": window[0],
            "window_end": window[1],
            "fit_end": split[0] if split else None,
            "validate_end": split[1] if split else None,
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
