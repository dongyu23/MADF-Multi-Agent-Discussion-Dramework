"""backfill audit level — align with AGENTS.md section 12

Revision ID: c91f4e8a3d2d
Revises: 7883e7a9b2c1
Create Date: 2026-05-17 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c91f4e8a3d2d'
down_revision: Union[str, Sequence[str], None] = '7883e7a9b2c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 默认 P2
    op.execute("UPDATE audit_events SET level = 'P2'")

    # P0 — 安全事件 + 资源消耗
    op.execute("""
        UPDATE audit_events SET level = 'P0'
        WHERE event_type IN ('user.login', 'user.login_failed', 'skill.generate')
    """)

    # P1 — 生命周期 + 数据变更 + 跨用户操作
    op.execute("""
        UPDATE audit_events SET level = 'P1'
        WHERE event_type IN (
            'user.register', 'skill.generate_complete', 'skill.generate_error',
            'skill.delete', 'skill.copy', 'discussion.create', 'discussion.error'
        )
    """)


def downgrade() -> None:
    op.execute("UPDATE audit_events SET level = 'P2'")
