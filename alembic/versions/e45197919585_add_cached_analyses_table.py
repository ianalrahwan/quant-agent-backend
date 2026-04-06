"""add cached_analyses table

Revision ID: e45197919585
Revises:
Create Date: 2026-04-06 03:56:05.306408

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e45197919585"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cached_analyses",
        sa.Column("symbol", sa.String(10), primary_key=True),
        sa.Column("scanner_signals", sa.JSON, nullable=False),
        sa.Column("narrative", sa.Text, nullable=False, server_default=""),
        sa.Column("trade_recs", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("vol_surface", sa.JSON, nullable=True),
        sa.Column("phases_log", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("total_time", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_cached_analyses_created_at", "cached_analyses", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_cached_analyses_created_at", table_name="cached_analyses")
    op.drop_table("cached_analyses")
