import datetime as dt

import polars as pl
import pytest
from kaps_analytics.study.config import StudyConfig
from kaps_analytics.study.split import SplitError, assign_parts
from studyhelpers import earliest, latest

T0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def events(closes: list[int], opens: list[int] | None = None) -> pl.LazyFrame:
    """One trade per event; event i closes at hour closes[i] and opens at hour opens[i]."""
    opens = opens if opens is not None else [c - 1 for c in closes]
    return pl.DataFrame(
        {
            "event_ticker": [f"E{i}" for i in range(len(closes))],
            "ev_open": [T0 + dt.timedelta(hours=h) for h in opens],
            "ev_close": [T0 + dt.timedelta(hours=h) for h in closes],
        }
    ).lazy()


def parts(frame: pl.LazyFrame, config: StudyConfig | None = None) -> dict[str, list[str]]:
    out, _ = assign_parts(frame, config or StudyConfig())
    rows = out.collect()
    return {
        name: rows.filter(pl.col("part") == name)["event_ticker"].to_list()
        for name in ("fit", "validate", "test")
    }


def test_events_split_seventy_fifteen_fifteen_by_close_time() -> None:
    out, bounds = assign_parts(events(list(range(100))), StudyConfig())
    assert bounds.events == {"fit": 70, "validate": 15, "test": 15, "dropped": 0}
    rows = out.collect()
    assert latest(rows.filter(pl.col("part") == "fit")["ev_close"]) < earliest(
        rows.filter(pl.col("part") == "validate")["ev_close"]
    )
    assert latest(rows.filter(pl.col("part") == "validate")["ev_close"]) < earliest(
        rows.filter(pl.col("part") == "test")["ev_close"]
    )


def test_the_order_of_the_input_does_not_matter() -> None:
    closes = list(range(100))
    shuffled = closes[::-1]
    assert parts(events(closes))["test"] != []
    assert {k: sorted(v) for k, v in parts(events(shuffled)).items()}["test"] == sorted(
        f"E{99 - i}" for i in range(85, 100)
    )


def test_an_event_that_opened_before_its_part_began_is_dropped() -> None:
    closes = list(range(100))
    opens = [c - 1 for c in closes]
    opens[90] = 10  # closes in the test part but opened during the fit part
    opens[75] = 10  # closes in the validate part but opened during the fit part
    out, bounds = assign_parts(events(closes, opens), StudyConfig())
    rows = out.collect()
    assert rows.filter(pl.col("event_ticker") == "E90")["part"][0] is None
    assert rows.filter(pl.col("event_ticker") == "E75")["part"][0] is None
    assert bounds.events["dropped"] == 2


def test_a_long_event_in_the_fit_part_is_kept() -> None:
    opens = [c - 1 for c in range(100)]
    opens[5] = -500
    out, _ = assign_parts(events(list(range(100)), opens), StudyConfig())
    assert out.collect().filter(pl.col("event_ticker") == "E5")["part"][0] == "fit"


def test_all_trades_of_an_event_land_in_the_same_part() -> None:
    frame = pl.concat([events(list(range(30))), events(list(range(30)))])
    rows = assign_parts(frame, StudyConfig())[0].collect()
    assert (
        rows.group_by("event_ticker")
        .agg(pl.col("part").n_unique())
        .filter(pl.col("part") > 1)
        .is_empty()
    )


def test_other_fractions_are_honoured() -> None:
    config = StudyConfig(fractions=(0.5, 0.25, 0.25))
    _, bounds = assign_parts(events(list(range(100))), config)
    assert (bounds.events["fit"], bounds.events["validate"], bounds.events["test"]) == (50, 25, 25)


def test_too_few_events_cannot_be_split() -> None:
    with pytest.raises(SplitError):
        assign_parts(events([1, 2]), StudyConfig())
