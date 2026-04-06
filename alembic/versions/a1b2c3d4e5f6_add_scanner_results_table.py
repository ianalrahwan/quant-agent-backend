"""add scanner_results table

Revision ID: a1b2c3d4e5f6
Revises: e45197919585
Create Date: 2026-04-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "e45197919585"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "scanner_results",
        sa.Column("symbol", sa.String(10), primary_key=True),
        sa.Column("scores", sa.JSON, nullable=False),
        sa.Column("composite", sa.Float, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_scanner_results_created_at", "scanner_results", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_scanner_results_created_at", table_name="scanner_results")
    op.drop_table("scanner_results")
