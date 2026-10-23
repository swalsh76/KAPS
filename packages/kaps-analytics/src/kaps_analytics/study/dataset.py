"""One row per trade, with its outcome, fee, time to expiry and event, from the downloaded files.

Every trade is kept in the tagged frame with an ``exclusion`` reason (or null for a trade the
study uses), so the counts of what was left out are exact and nothing is dropped silently.

The fee in force at a trade is the series' fee type and multiplier. For a series with recorded fee
changes it is the latest change at or before the trade; a trade before the first recorded change
has no known fee and is excluded as ``fee_unknown``. A series with no recorded change keeps its
current fee, on the assumption (checked in K0.5.6) that the change history is complete.
"""

from pathlib import Path

import polars as pl
from kaps_core.fees import MAKER_SHARE_E2

from kaps_analytics.study.config import StudyConfig
from kaps_analytics.study.feecalc import maker_fee_expr, taker_fee_expr

MARKET_TIME_FIELDS = (
    "expected_expiration_time",
    "close_time",
    "occurrence_datetime",
    "expiration_time",
    "latest_expiration_time",
)
REASONS = (
    "bad_side",
    "market_missing",
    "not_binary",
    "fee_unknown",
    "time_unknown",
    "event_time_unknown",
)


class StudyDataError(Exception):
    """The data folder lacks something the study needs."""


def _markets(root: Path, traded: pl.LazyFrame) -> pl.LazyFrame:
    """Every downloaded market that has a trade, once each (the historical row wins)."""
    columns = (
        "ticker",
        "event_ticker",
        "series_ticker",
        "label",
        "open_time",
        "created_time",
        *MARKET_TIME_FIELDS,
    )
    parts = []
    historical = root / "markets" / "historical"
    if historical.exists() and any(historical.glob("part-*.parquet")):
        parts.append(
            pl.scan_parquet(historical / "part-*.parquet")
            .select(columns)
            .with_columns(rank=pl.lit(0))
        )
    live = root / "markets" / "live"
    if live.exists() and any(live.glob("date=*/markets.parquet")):
        parts.append(
            pl.scan_parquet(live / "date=*" / "markets.parquet")
            .select(columns)
            .with_columns(rank=pl.lit(1))
        )
    if not parts:
        raise StudyDataError(f"no markets found under {root / 'markets'}")
    return (
        pl.concat(parts)
        .join(traded, on="ticker", how="semi")  # a day touches about 20 thousand of 18 million
        .sort("rank", maintain_order=True)  # a join does not keep order, so rank says who wins
        .unique(subset="ticker", keep="first", maintain_order=True)
        .drop("rank")
    )


def _reference_expr(config: StudyConfig, categories: list[str]) -> pl.Expr:
    """The market time the time to expiry is measured to: the first present field in the
    category's order (D10)."""
    default = pl.coalesce([pl.col(f) for f in config.reference_for("")])
    expr = default
    for category in categories:
        fields = config.reference_for(category)
        if fields != config.reference_for(""):
            expr = (
                pl.when(pl.col("category") == category)
                .then(pl.coalesce([pl.col(f) for f in fields]))
                .otherwise(expr)
            )
    return expr


def _with_fees(trades: pl.LazyFrame, root: Path) -> pl.LazyFrame:
    """Add ``fee_type`` and ``multiplier_e6`` as in force at each trade (null when unknown)."""
    series = pl.scan_parquet(root / "series.parquet").select(
        pl.col("ticker").alias("series_ticker"),
        pl.col("fee_type"),
        pl.col("fee_multiplier_e6").alias("multiplier_e6"),
    )
    changes_path = root / "fee_changes.parquet"
    changes = (
        pl.scan_parquet(changes_path).select(
            "series_ticker",
            pl.col("scheduled_ts"),
            pl.col("fee_type"),
            pl.col("fee_multiplier_e6").alias("multiplier_e6"),
        )
        if changes_path.exists()
        else None
    )
    changed = (
        changes.select("series_ticker").unique().collect()["series_ticker"].to_list()
        if changes is not None
        else []
    )
    plain = trades.filter(~pl.col("series_ticker").is_in(changed)).join(
        series, on="series_ticker", how="left"
    )
    if changes is None or not changed:
        return plain
    timeline = changes.sort("scheduled_ts")
    changing = (
        trades.filter(pl.col("series_ticker").is_in(changed))
        .sort("t")
        .join_asof(
            timeline,
            left_on="t",
            right_on="scheduled_ts",
            by="series_ticker",
            strategy="backward",
            check_sortedness=False,  # sorted by time just above, so within each series too
        )
        .drop("scheduled_ts")
    )
    return pl.concat([plain, changing.select(plain.collect_schema().names())])


def tag_trades(root: Path, config: StudyConfig) -> pl.LazyFrame:
    """The study's trade frame with an ``exclusion`` column (null = used).

    Columns: ``event_ticker ticker series_ticker category t p c taker_yes y tleft_s``
    ``tk_fee mk_fee_nom mk_fee_cons ev_open ev_close exclusion`` (``p`` the yes price in
    millionths, ``c`` the count in hundredths, ``y`` 1 when the market settled yes, fees in
    millionths of a dollar for the whole trade).
    """
    trades_pattern = root / "trades" / "date=*" / "trades.parquet"
    if not any(root.glob("trades/date=*/trades.parquet")):
        raise StudyDataError(f"no trades found at {trades_pattern}")
    trades = pl.scan_parquet(trades_pattern, hive_partitioning=False).select(
        pl.col("ticker"),
        pl.col("created_time").alias("t"),
        pl.col("yes_price_e6").cast(pl.Int64).alias("p"),
        pl.col("count_e2").alias("c"),
        pl.col("taker_side"),
    )
    if not (root / "series.parquet").exists():
        raise StudyDataError(f"no series.parquet found under {root}")
    markets = _markets(root, trades.select("ticker").unique())
    categories = (
        pl.scan_parquet(root / "series.parquet")
        .select(pl.col("ticker").alias("series_ticker"), pl.col("category"))
        .with_columns(pl.col("category").fill_null("unknown"))
    )
    category_names = categories.select("category").unique().collect()["category"].to_list()

    events = markets.group_by("event_ticker").agg(
        pl.coalesce("open_time", "created_time").min().alias("ev_open"),
        pl.coalesce("close_time", "expected_expiration_time").max().alias("ev_close"),
    )
    market_info = (
        markets.join(categories, on="series_ticker", how="left")
        .with_columns(pl.col("category").fill_null("unknown"))
        .with_columns(_reference_expr(config, category_names).alias("ref_time"))
        .select("ticker", "event_ticker", "series_ticker", "category", "label", "ref_time")
        .join(events, on="event_ticker", how="left")
    )
    frame = trades.join(market_info, on="ticker", how="left")
    frame = _with_fees(frame, root)
    nominal = pl.col("fee_type").replace_strict(MAKER_SHARE_E2, default=None, return_dtype=pl.Int64)
    conservative = (
        pl.when(nominal > 0)
        .then(pl.lit(config.verdict_maker_share_e2, dtype=pl.Int64))
        .otherwise(0)
    )
    known = nominal.is_not_null() & pl.col("multiplier_e6").is_not_null()
    frame = frame.with_columns(
        (pl.col("taker_side") == "yes").alias("taker_yes"),
        (pl.col("label") == "yes").cast(pl.Int8).alias("y"),
        ((pl.col("ref_time") - pl.col("t")).dt.total_seconds().clip(lower_bound=0)).alias(
            "tleft_s"
        ),
        pl.when(known)
        .then(taker_fee_expr(pl.col("multiplier_e6"), pl.col("c"), pl.col("p")))
        .alias("tk_fee"),
        pl.when(known)
        .then(maker_fee_expr(pl.col("multiplier_e6"), nominal, pl.col("c"), pl.col("p")))
        .alias("mk_fee_nom"),
        pl.when(known)
        .then(maker_fee_expr(pl.col("multiplier_e6"), conservative, pl.col("c"), pl.col("p")))
        .alias("mk_fee_cons"),
    )
    exclusion = (
        pl.when(~pl.col("taker_side").is_in(["yes", "no"]))
        .then(pl.lit("bad_side"))
        .when(pl.col("label").is_null())
        .then(pl.lit("market_missing"))
        .when(~pl.col("label").is_in(["yes", "no"]))
        .then(pl.lit("not_binary"))
        .when(pl.col("tk_fee").is_null())
        .then(pl.lit("fee_unknown"))
        .when(pl.col("ref_time").is_null())
        .then(pl.lit("time_unknown"))
        .when(pl.col("ev_open").is_null() | pl.col("ev_close").is_null())
        .then(pl.lit("event_time_unknown"))
    )
    return frame.with_columns(exclusion.alias("exclusion")).select(
        "event_ticker",
        "ticker",
        "series_ticker",
        "category",
        "t",
        "p",
        "c",
        "taker_yes",
        "y",
        "tleft_s",
        "tk_fee",
        "mk_fee_nom",
        "mk_fee_cons",
        "ev_open",
        "ev_close",
        "exclusion",
    )


def used(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.filter(pl.col("exclusion").is_null()).drop("exclusion")


def exclusion_counts(frame: pl.LazyFrame) -> dict[str, int]:
    """The number of trades by exclusion reason (``used`` for the kept ones)."""
    rows = (
        frame.group_by(pl.col("exclusion").fill_null("used"))
        .agg(pl.len().alias("trades"))
        .collect()
        .iter_rows()
    )
    return {reason: int(n) for reason, n in rows}
