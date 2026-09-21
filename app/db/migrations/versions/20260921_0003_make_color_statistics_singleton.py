"""Make global colour statistics an explicit singleton.

Revision ID: 20260921_0003
Revises: 20260921_0002
Create Date: 2026-09-21 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_0003"
down_revision: str | None = "20260921_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "color_statistics_new",
        sa.Column("id", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("total_red", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_green", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_blue", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_color_statistics_singleton"),
        sa.CheckConstraint("total_red >= 0", name="ck_color_statistics_total_red_nonnegative"),
        sa.CheckConstraint("total_green >= 0", name="ck_color_statistics_total_green_nonnegative"),
        sa.CheckConstraint("total_blue >= 0", name="ck_color_statistics_total_blue_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO color_statistics_new (id, total_red, total_green, total_blue) "
        "SELECT 1, total_red, total_green, total_blue "
        "FROM color_statistics LIMIT 1"
    )
    op.drop_table("color_statistics")
    op.rename_table("color_statistics_new", "color_statistics")


def downgrade() -> None:
    op.create_table(
        "color_statistics_old",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("total_red", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_green", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_blue", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("total_red >= 0", name="ck_color_statistics_total_red_nonnegative"),
        sa.CheckConstraint("total_green >= 0", name="ck_color_statistics_total_green_nonnegative"),
        sa.CheckConstraint("total_blue >= 0", name="ck_color_statistics_total_blue_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO color_statistics_old (id, total_red, total_green, total_blue) "
        "SELECT '00000000-0000-0000-0000-000000000001', total_red, total_green, total_blue "
        "FROM color_statistics"
    )
    op.drop_table("color_statistics")
    op.rename_table("color_statistics_old", "color_statistics")
