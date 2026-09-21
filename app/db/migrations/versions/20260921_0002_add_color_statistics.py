"""Add transactional global colour statistics.

Revision ID: 20260921_0002
Revises: 20260921_0001
Create Date: 2026-09-21 12:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260921_0002"
down_revision: str | None = "20260921_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "color_statistics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_red", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_green", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_blue", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("total_red >= 0", name="ck_color_statistics_total_red_nonnegative"),
        sa.CheckConstraint("total_green >= 0", name="ck_color_statistics_total_green_nonnegative"),
        sa.CheckConstraint("total_blue >= 0", name="ck_color_statistics_total_blue_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO color_statistics (id, total_red, total_green, total_blue) "
        "VALUES ('00000000-0000-0000-0000-000000000001', 0, 0, 0)"
    )


def downgrade() -> None:
    op.drop_table("color_statistics")
