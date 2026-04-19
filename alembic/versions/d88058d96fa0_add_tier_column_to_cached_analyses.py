"""add tier column to cached_analyses

Revision ID: d88058d96fa0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-18 22:02:26.441507

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d88058d96fa0"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "cached_analyses",
        sa.Column("tier", sa.String(8), nullable=False, server_default="pro"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cached_analyses", "tier")
