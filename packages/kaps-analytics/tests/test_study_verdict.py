"""The whole study on synthetic worlds whose true answer is known."""

from pathlib import Path

import polars as pl
import pytest
from kaps_analytics.study.config import StudyConfig
from kaps_analytics.study.dataset import tag_trades
from kaps_analytics.study.segments import Prereg, PreregistrationError, Segment
from kaps_analytics.study.session import Study
from kaps_analytics.study.synthetic import World, write_world
from kaps_analytics.study.verdict import GO, INCONCLUSIVE, NO_GO
from studyhelpers import earliest, latest

CONFIG = StudyConfig(min_events=40, resamples=2000)
LONGSHOT_BUYS_NO = Segment(price_lo_e6=40_000, price_hi_e6=200_000, side="no")
LONGSHOT_BUYS_YES = Segment(price_hi_e6=250_000, side="yes")


def world_root(factory: pytest.TempPathFactory, world: World, name: str) -> Path:
    root = factory.mktemp(name) / "kalshi"
    write_world(world, root)
    return root


@pytest.fixture(scope="module")
def biased_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return world_root(
        tmp_path_factory, World(events=7000, trades_per_market=8, bias=0.15, seed=21), "biased"
    )


@pytest.fixture(scope="module")
def null_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return world_root(
        tmp_path_factory, World(events=7000, trades_per_market=8, bias=0.0, seed=22), "null"
    )


@pytest.fixture(scope="module")
def informed_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    world = World(events=7000, trades_per_market=8, bias=0.15, drift=1.0, noise=0.0, seed=23)
    return world_root(tmp_path_factory, world, "informed")


def study(root: Path, ledger: Path) -> Study:
    """A study over a world's files with its own ledger, so each test starts unlocked."""
    return Study(tag_trades(root, CONFIG), CONFIG, ledger / "prereg.json")


@pytest.fixture
def biased(biased_root: Path, tmp_path: Path) -> Study:
    return study(biased_root, tmp_path)


@pytest.fixture
def null(null_root: Path, tmp_path: Path) -> Study:
    return study(null_root, tmp_path)


@pytest.fixture
def informed(informed_root: Path, tmp_path: Path) -> Study:
    return study(informed_root, tmp_path)


def test_a_planted_longshot_bias_is_found_as_a_taker_edge(biased: Study) -> None:
    verdict = biased.verdict(Prereg((LONGSHOT_BUYS_NO,), CONFIG))
    result = verdict.segments[0]
    assert verdict.outcome == GO
    assert result.taker_go
    taker = result.estimates["taker"]
    assert taker.lower_e6 > 0
    assert taker.events >= CONFIG.min_events
    # the planted gross edge is about 2.5 to 4 cents a contract at these prices, less the fee
    assert 10_000 < taker.point_e6 < 60_000


def test_with_no_bias_the_taker_pays_the_fee_and_there_is_no_go(null: Study) -> None:
    verdict = null.verdict(Prereg((LONGSHOT_BUYS_NO, LONGSHOT_BUYS_YES, Segment()), CONFIG))
    assert verdict.outcome in (NO_GO, INCONCLUSIVE)
    assert all(not r.taker_go and not r.maker_go for r in verdict.segments)
    assert verdict.segments[2].estimates["taker"].point_e6 < 0  # fees only cost


def test_an_edge_that_exists_only_under_the_optimistic_fill_rule_is_not_a_go(
    informed: Study,
) -> None:
    verdict = informed.verdict(Prereg((LONGSHOT_BUYS_YES,), CONFIG))
    result = verdict.segments[0]
    assert result.estimates["mk_opt_cons"].lower_e6 > 0
    assert result.estimates["mk_pess_cons"].lower_e6 <= 0
    assert result.optimistic_only
    assert not result.maker_go
    assert verdict.outcome == INCONCLUSIVE


def test_without_informed_flow_the_maker_edge_survives_the_pessimistic_rule(
    biased: Study,
) -> None:
    result = biased.verdict(Prereg((LONGSHOT_BUYS_YES,), CONFIG)).segments[0]
    assert result.estimates["mk_opt_cons"].lower_e6 > 0
    assert result.estimates["mk_pess_cons"].point_e6 > 0


def test_a_segment_short_of_events_makes_the_verdict_inconclusive(null: Study) -> None:
    rare = Segment(price_hi_e6=40_000, side="yes", category="politics", tleft_hi_s=600)
    result = null.verdict(Prereg((rare,), CONFIG)).segments[0]
    assert result.short_of_events
    assert result.events < CONFIG.min_events
    assert null.verdict(Prereg((rare,), CONFIG)).outcome == INCONCLUSIVE


def test_the_pre_registration_is_locked_once_the_test_is_opened(biased: Study) -> None:
    biased.verdict(Prereg((LONGSHOT_BUYS_NO,), CONFIG))
    with pytest.raises(PreregistrationError, match="locked"):
        biased.verdict(Prereg((LONGSHOT_BUYS_NO, LONGSHOT_BUYS_YES), CONFIG))
    with pytest.raises(PreregistrationError):
        biased.ladder(Prereg((LONGSHOT_BUYS_YES,), CONFIG))


def test_the_test_part_is_not_exposed_except_through_the_lock(biased: Study) -> None:
    assert not hasattr(biased, "test")
    fit, validate = biased.fit.collect(), biased.validate.collect()
    assert set(fit["part"].unique()) == {"fit"}
    assert set(validate["part"].unique()) == {"validate"}


def test_the_parts_share_no_event_and_follow_in_time(biased: Study) -> None:
    prereg = Prereg((LONGSHOT_BUYS_NO,), CONFIG)
    fit, validate = biased.fit.collect(), biased.validate.collect()
    test = biased.open_test(prereg).collect()
    sets = [set(f["event_ticker"].unique()) for f in (fit, validate, test)]
    assert not (sets[0] & sets[1]) and not (sets[1] & sets[2]) and not (sets[0] & sets[2])
    assert latest(fit["ev_close"]) < earliest(validate["ev_close"])
    assert latest(validate["ev_close"]) < earliest(test["ev_close"])
    assert earliest(validate["ev_open"]) >= latest(fit["ev_close"])
    assert earliest(test["ev_open"]) >= latest(validate["ev_close"])


def test_the_band_correction_beats_the_raw_price_when_the_bias_is_real(biased: Study) -> None:
    ladder = biased.ladder(Prereg((LONGSHOT_BUYS_NO,), CONFIG))
    assert ladder.band_corrected.brier < ladder.raw.brier
    assert ladder.band_corrected.log_loss < ladder.raw.log_loss
    assert ladder.raw.contracts_e2 == ladder.band_corrected.contracts_e2 > 0


def test_the_band_correction_does_not_help_when_there_is_no_bias(null: Study) -> None:
    ladder = null.ladder(Prereg((LONGSHOT_BUYS_NO,), CONFIG))
    assert ladder.band_corrected.brier == pytest.approx(ladder.raw.brier, rel=0.02)


def test_the_naive_maker_loses_to_the_fee_when_nothing_is_mispriced(null: Study) -> None:
    ladder = null.ladder(Prereg((Segment(),), CONFIG))
    assert ladder.maker_optimistic_e6 < 5_000  # no better than a cent a contract
    assert ladder.maker_pessimistic_e6 < ladder.maker_optimistic_e6 + 1


def test_a_dataset_with_exclusions_still_runs(tmp_path: Path) -> None:
    root = tmp_path / "kalshi"
    write_world(World(events=300, trades_per_market=6, seed=2), root)
    tagged = tag_trades(root, CONFIG)
    assert tagged.filter(pl.col("exclusion").is_not_null()).collect().is_empty()


def test_across_many_worlds_with_no_edge_a_false_go_is_rare(tmp_path: Path) -> None:
    """The family rate is 2.5% a measure, so about 5% over taker and maker; sixteen worlds should
    hold at most three false GOs (a chance under one in a hundred if the true rate is 5%)."""
    config = StudyConfig(min_events=15, resamples=600)
    segments = (
        Segment(price_hi_e6=200_000, side="no"),
        Segment(price_hi_e6=200_000, side="yes"),
        Segment(price_lo_e6=800_000, side="yes"),
        Segment(price_lo_e6=800_000, side="no"),
    )
    false_go = 0
    for seed in range(16):
        root = tmp_path / f"w{seed}" / "kalshi"
        write_world(World(events=1800, trades_per_market=6, bias=0.0, seed=100 + seed), root)
        study_ = Study(tag_trades(root, config), config, tmp_path / f"w{seed}" / "prereg.json")
        false_go += study_.verdict(Prereg(segments, config)).outcome == GO
    assert false_go <= 3
