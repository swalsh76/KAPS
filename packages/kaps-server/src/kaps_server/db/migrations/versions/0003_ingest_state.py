"""Where the ingest remembers things across a restart: discovery bookmarks, the feed's heartbeat.

One small table of text values by key. The heartbeat is the time of the last frame the feed
delivered, written every few seconds, so that after a restart the gap is known exactly instead of
guessed from the newest stored trade. Written out in full on purpose: a migration is a frozen
record of what was run, and must not follow ``schema.py``.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_state",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingest_state")
