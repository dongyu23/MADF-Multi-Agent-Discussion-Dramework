"""add skill generation events

Revision ID: 20260524_01
Revises: c91f4e8a3d2d
Create Date: 2026-05-24 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260524_01"
down_revision: Union[str, Sequence[str], None] = "c91f4e8a3d2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skill_generation_events",
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("skill_id", "seq", name="uq_sge_skill_seq"),
    )
    op.create_index("idx_sge_skill_seq", "skill_generation_events", ["skill_id", "seq"], unique=False)
    op.create_index("idx_sge_owner_created", "skill_generation_events", ["owner_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_sge_owner_created", table_name="skill_generation_events")
    op.drop_index("idx_sge_skill_seq", table_name="skill_generation_events")
    op.drop_table("skill_generation_events")
