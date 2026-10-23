"""WebSocket frames: parsed once, exact money, unknown fields counted, bad messages kept."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from kaps_core.ws_models import (
    EventLifecycleMsg,
    MarketLifecycleMsg,
    TickerMsg,
    TradeMsg,
    known_keys,
    parse_frame,
)


def frame(kind: str, msg: Any, **envelope: Any) -> str:
    return json.dumps({"type": kind, "msg": msg, **envelope})


TICKER = {
    "market_ticker": "KXHIGHNY-26OCT24-T70",
    "market_id": "abc",
    "price_dollars": "0.5600",
    "yes_bid_dollars": "0.5500",
    "yes_ask_dollars": "0.5700",
    "yes_bid_size_fp": "120.00",
    "yes_ask_size_fp": "80.50",
    "volume_fp": "12345.00",
    "open_interest_fp": "999.00",
    "last_trade_size_fp": "3.00",
    "ts_ms": 1_792_785_174_669,
}
TRADE = {
    "trade_id": "t-1",
    "market_ticker": "KXHIGHNY-26OCT24-T70",
    "yes_price_dollars": "0.5600",
    "no_price_dollars": "0.4400",
    "count_fp": "3.00",
    "taker_side": "yes",
    "ts_ms": 1_792_785_174_000,
}


def test_a_ticker_becomes_fixed_point_integers() -> None:
    result = parse_frame(frame("ticker", TICKER, sid=2, seq=7, sending_ts_ms=5))
    assert result.error is None and result.unknown == ()
    ticker = result.payload
    assert isinstance(ticker, TickerMsg)
    assert (ticker.price_e6, ticker.yes_bid_e6, ticker.yes_ask_e6) == (560_000, 550_000, 570_000)
    assert (ticker.yes_bid_size_e2, ticker.yes_ask_size_e2) == (12_000, 8_050)
    assert (ticker.volume_e2, ticker.open_interest_e2, ticker.last_trade_size_e2) == (
        1_234_500,
        99_900,
        300,
    )
    assert ticker.ts_ms == 1_792_785_174_669
    assert (result.type, result.sid, result.seq, result.sending_ts_ms) == ("ticker", 2, 7, 5)


def test_a_ticker_with_only_some_fields_leaves_the_rest_empty() -> None:
    ticker = parse_frame(frame("ticker", {"market_ticker": "M", "yes_bid_dollars": "0.10"})).payload
    assert isinstance(ticker, TickerMsg)
    assert ticker.yes_bid_e6 == 100_000 and ticker.price_e6 is None and ticker.volume_e2 is None


def test_a_trade_is_parsed_and_its_prices_must_add_to_a_dollar() -> None:
    trade = parse_frame(frame("trade", TRADE, sid=3, seq=1)).payload
    assert isinstance(trade, TradeMsg)
    assert (trade.yes_price_e6, trade.no_price_e6, trade.count_e2) == (560_000, 440_000, 300)
    assert trade.taker_side == "yes" and trade.is_block_trade is False
    bad = parse_frame(frame("trade", {**TRADE, "no_price_dollars": "0.4500"}))
    assert bad.payload is None and "do not add to $1" in (bad.error or "")


def test_numbers_that_are_json_numbers_are_still_exact() -> None:
    """A price sent as a JSON number reaches the model as its text, never as a binary float."""
    raw = '{"type": "trade", "msg": {"trade_id": "t", "market_ticker": "M", '
    raw += '"yes_price_dollars": 0.56, "no_price_dollars": 0.44, "count_fp": 3.0}}'
    trade = parse_frame(raw).payload
    assert isinstance(trade, TradeMsg) and trade.yes_price_e6 == 560_000 and trade.count_e2 == 300


@pytest.mark.parametrize(
    "change",
    [
        {"yes_price_dollars": "0.5600001", "no_price_dollars": "0.4399999"},  # beyond a millionth
        {"count_fp": "3.001"},  # beyond a hundredth
        {"count_fp": "abc"},
        {"yes_price_dollars": True},
    ],
)
def test_a_value_more_precise_than_its_scale_is_refused_and_the_frame_is_kept(
    change: dict[str, Any],
) -> None:
    result = parse_frame(frame("trade", {**TRADE, **change}))
    assert result.payload is None and result.error
    assert result.raw["msg"]["trade_id"] == "t-1"  # what arrived is still there to be stored


def test_a_missing_required_field_names_the_field() -> None:
    result = parse_frame(frame("trade", {k: v for k, v in TRADE.items() if k != "trade_id"}))
    assert result.payload is None and "trade_id" in (result.error or "")


def test_fields_the_model_does_not_know_are_listed() -> None:
    result = parse_frame(frame("ticker", {**TICKER, "brand_new": 1, "another": {"x": 2}}))
    assert isinstance(result.payload, TickerMsg)
    assert result.unknown == ("another", "brand_new")


def test_a_field_read_under_its_alias_is_not_reported_as_unknown() -> None:
    assert "price_dollars" in known_keys(TickerMsg) and "price_e6" in known_keys(TickerMsg)
    assert parse_frame(frame("ticker", TICKER)).unknown == ()


def test_a_market_lifecycle_message_turns_seconds_into_times() -> None:
    life = {
        "market_ticker": "M",
        "event_type": "settled",
        "open_ts": 1_700_000_000,
        "settled_ts": 1_700_003_600,
        "result": "yes",
        "settlement_value": "1.0000",
        "is_deactivated": False,
        "additional_metadata": {"a": 1},
    }
    message = parse_frame(frame("market_lifecycle_v2", life, sid=4, seq=1)).payload
    assert isinstance(message, MarketLifecycleMsg)
    assert message.open_ts == datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)
    assert message.settled_ts == datetime(2023, 11, 14, 23, 13, 20, tzinfo=UTC)
    assert message.close_ts is None and message.result == "yes"
    assert message.settlement_value == "1.0000" and message.additional_metadata == {"a": 1}


def test_a_market_lifecycle_message_needs_an_event_type() -> None:
    assert "event_type" in (
        parse_frame(frame("market_lifecycle_v2", {"market_ticker": "M"})).error or ""
    )


def test_the_combo_lifecycle_channel_uses_the_same_model() -> None:
    result = parse_frame(frame("multivariate_market_lifecycle", {"event_type": "created"}))
    assert isinstance(result.payload, MarketLifecycleMsg)


def test_an_event_lifecycle_message() -> None:
    body = {"event_ticker": "EV", "series_ticker": "SE", "title": "T", "exchange_index": 0}
    message = parse_frame(frame("event_lifecycle", body)).payload
    assert isinstance(message, EventLifecycleMsg) and message.series_ticker == "SE"


def test_a_known_type_whose_message_is_not_an_object_is_kept_with_an_error() -> None:
    result = parse_frame(frame("ticker", [1, 2]))
    assert result.payload is None and "not an object" in (result.error or "")


def test_an_unmodelled_type_passes_through_untouched_without_an_error() -> None:
    result = parse_frame(frame("orderbook_delta", {"market_ticker": "M"}, sid=9, seq=3))
    assert result.payload is None and result.error is None and result.unknown == ()
    assert (result.sid, result.seq) == (9, 3)


def test_responses_are_recognised() -> None:
    result = parse_frame(
        json.dumps({"id": 4, "type": "subscribed", "msg": {"channel": "ticker", "sid": 2}})
    )
    assert result.is_response and result.id == 4
    assert not parse_frame(frame("ticker", TICKER)).is_response
    assert parse_frame(
        json.dumps({"id": 1, "type": "error", "msg": {"code": 6, "msg": "x"}})
    ).is_response


def test_envelope_numbers_must_really_be_integers() -> None:
    result = parse_frame(
        json.dumps({"type": "x", "sid": True, "seq": "5", "id": 1.5, "sending_ts_ms": None})
    )
    assert (result.sid, result.seq, result.id, result.sending_ts_ms) == (None, None, None, None)


@pytest.mark.parametrize(
    "raw", ["not json", "[1, 2]", "{}", '{"type": 5}', '{"msg": 1}', "", "null"]
)
def test_a_frame_that_is_not_an_object_with_a_type_raises_value_error(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_frame(raw)


def test_bytes_frames_parse_too() -> None:
    assert parse_frame(frame("ticker", TICKER).encode()).type == "ticker"
