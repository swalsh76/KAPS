"""Calibration: how often the yes outcome happened at each price, by band, time and category.

Weighted by contracts, so a cell reads as "of the contracts bought at about this price, this share
settled yes". ``gap`` is the observed yes rate minus the mean price: positive means the market
under-priced yes. The columns that cluster the intervals by event live in :mod:`bootstrap`.
"""

import polars as pl

from kaps_analytics.study.config import StudyConfig

E6 = 1_000_000


def calibration_table(frame: pl.LazyFrame, by: list[str]) -> pl.DataFrame:
    """One row per cell of ``by`` (columns of the banded frame, such as ``price_band``)."""
    return (
        frame.group_by(by)
        .agg(
            pl.len().alias("trades"),
            pl.col("event_ticker").n_unique().alias("events"),
            pl.col("c").sum().alias("contracts_e2"),
            (pl.col("p").cast(pl.Float64) * pl.col("c")).sum().alias("_price_weight"),
            (pl.col("y").cast(pl.Float64) * pl.col("c")).sum().alias("_yes_weight"),
        )
        .with_columns(
            (pl.col("_price_weight") / pl.col("contracts_e2") / E6).alias("mean_price"),
            (pl.col("_yes_weight") / pl.col("contracts_e2")).alias("yes_rate"),
        )
        .with_columns((pl.col("yes_rate") - pl.col("mean_price")).alias("gap"))
        .drop("_price_weight", "_yes_weight")
        .sort(by)
        .collect()
    )


def band_labels(config: StudyConfig) -> list[str]:
    """Readable names of the price bands, in cents, in band-number order."""
    edges = [e // 10_000 for e in config.price_edges_e6]
    return [f"{lo}-{hi}c" for lo, hi in zip(edges, edges[1:], strict=False)]
