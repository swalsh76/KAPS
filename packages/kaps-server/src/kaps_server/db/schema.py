"""The tables as Python objects: the current shape of the schema.

The migrations are the history and this module is the present: a database test compares the two, so
they cannot drift. The columns follow the downloader's Parquet files (``kaps_analytics.history``),
so K2's import is a copy: same names, and integers stay integers (``int`` for ``int32``, ``bigint``
for ``int64``).
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

metadata = sa.MetaData()

TIMESTAMPTZ = sa.TIMESTAMP(timezone=True)

series = sa.Table(
    "series",
    metadata,
    sa.Column("ticker", sa.Text, primary_key=True),
    sa.Column("title", sa.Text),
    sa.Column("category", sa.Text),
    sa.Column("frequency", sa.Text),
    sa.Column("tags", postgresql.ARRAY(sa.Text)),
    sa.Column("exchange_index", sa.Integer),
    sa.Column("fee_type", sa.Text),
    sa.Column("fee_multiplier_e6", sa.BigInteger),
    sa.Column("fetched_at", TIMESTAMPTZ),
)

fee_change = sa.Table(
    "fee_change",
    metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("series_ticker", sa.Text, nullable=False),
    sa.Column("fee_type", sa.Text),
    sa.Column("fee_multiplier_e6", sa.BigInteger),
    sa.Column("scheduled_ts", TIMESTAMPTZ),
    sa.Column("fetched_at", TIMESTAMPTZ),
)

MARKET_TEXT = [
    "event_ticker",
    "series_ticker",
    "source",
    "label",
    "status",
    "result",
    "market_type",
    "title",
    "yes_sub_title",
    "no_sub_title",
    "rules_primary",
    "rules_secondary",
    "early_close_condition",
    "strike_type",
    "floor_strike",
    "cap_strike",
    "price_level_structure",
]
MARKET_TIMES = [
    "created_time",
    "open_time",
    "close_time",
    "expected_expiration_time",
    "expiration_time",
    "latest_expiration_time",
    "occurrence_datetime",
    "settlement_ts",
    "updated_time",
]
MARKET_BIGINTS = [
    "settlement_value_e6",
    "last_price_e6",
    "previous_price_e6",
    "yes_bid_e6",
    "yes_ask_e6",
    "no_bid_e6",
    "no_ask_e6",
    "yes_bid_size_e2",
    "yes_ask_size_e2",
    "volume_e2",
    "volume_24h_e2",
    "open_interest_e2",
    "notional_value_e6",
]

LABELS = ("yes", "no", "scalar", "other_settled", "unsettled")

market = sa.Table(
    "market",
    metadata,
    sa.Column("ticker", sa.Text, primary_key=True),
    *[sa.Column(name, sa.Text) for name in MARKET_TEXT],
    sa.Column("exchange_index", sa.Integer),
    sa.Column("can_close_early", sa.Boolean),
    *[sa.Column(name, TIMESTAMPTZ) for name in MARKET_TIMES],
    *[sa.Column(name, sa.BigInteger) for name in MARKET_BIGINTS],
    sa.Column("raw_json", postgresql.JSONB),
    sa.CheckConstraint(
        "label IN ('yes', 'no', 'scalar', 'other_settled', 'unsettled')", name="market_label"
    ),
)

trade = sa.Table(
    "trade",
    metadata,
    sa.Column("trade_id", sa.Text, nullable=False),
    sa.Column("ticker", sa.Text, nullable=False),
    sa.Column("created_time", TIMESTAMPTZ, nullable=False),
    sa.Column("yes_price_e6", sa.Integer, nullable=False),
    sa.Column("count_e2", sa.BigInteger, nullable=False),
    sa.Column("taker_side", sa.Text, nullable=False),
    sa.Column("is_block_trade", sa.Boolean, nullable=False, server_default=sa.false()),
    # a hypertable's primary key must include its time column
    sa.PrimaryKeyConstraint("ticker", "trade_id", "created_time", name="trade_pkey"),
    sa.CheckConstraint("yes_price_e6 BETWEEN 0 AND 1000000", name="trade_price"),
    sa.CheckConstraint("count_e2 >= 0", name="trade_count"),
    sa.CheckConstraint("taker_side IN ('yes', 'no')", name="trade_side"),
)

gap_log = sa.Table(
    "gap_log",
    metadata,
    sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
    sa.Column("kind", sa.Text, nullable=False),
    sa.Column("source", sa.Text, nullable=False),
    sa.Column("started_at", TIMESTAMPTZ, nullable=False),
    sa.Column("ended_at", TIMESTAMPTZ),
    sa.Column("note", sa.Text),
    sa.CheckConstraint("kind IN ('ticker', 'orderbook', 'trades', 'all')", name="gap_kind"),
)
