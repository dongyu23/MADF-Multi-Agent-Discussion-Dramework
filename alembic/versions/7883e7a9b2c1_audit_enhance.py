"""audit enhance — level column + new audit tables

Revision ID: 7883e7a9b2c1
Revises: b6ffa9873793
Create Date: 2026-05-17 08:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7883e7a9b2c1'
down_revision: Union[str, Sequence[str], None] = 'b6ffa9873793'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # audit_events 增强
    op.add_column('audit_events', sa.Column('level', sa.String(4), nullable=True))
    op.execute("UPDATE audit_events SET level = COALESCE(payload->>'level', 'P2')")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ae_level_created ON audit_events (level, created_at DESC) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ae_type_created ON audit_events (event_type, created_at DESC) WHERE deleted_at IS NULL")

    # 审计员表
    op.create_table('audit_admin_users',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('username', sa.String(64), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('display_name', sa.String(128)),
        sa.Column('role', sa.String(16), nullable=False, server_default='auditor'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # 自审计表
    op.create_table('audit_access_log',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('admin_user_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(64)),
        sa.Column('query_params', postgresql.JSONB()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_acl_admin_created', 'audit_access_log', ['admin_user_id', 'created_at'], postgresql_using='btree')

    # 保留策略表
    op.create_table('audit_retention_policy',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('level', sa.String(4), nullable=False),
        sa.Column('hot_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('warm_days', sa.Integer(), nullable=False, server_default='365'),
        sa.Column('archive_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('archive_method', sa.String(16), nullable=False, server_default='delete'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # 默认插入三条策略
    op.execute("""
        INSERT INTO audit_retention_policy (id, name, level, hot_days, warm_days) VALUES
        (uuid_generate_v4(), 'P0 安全事件', 'P0', 180, 730),
        (uuid_generate_v4(), 'P1 业务事件', 'P1', 90, 365),
        (uuid_generate_v4(), 'P2 一般事件', 'P2', 30, 90)
    """)

    # 完整性校验规则表
    op.create_table('audit_integrity_rules',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('trigger_event', sa.String(64), nullable=False),
        sa.Column('expected_event', sa.String(64), nullable=False),
        sa.Column('max_delay_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("""
        INSERT INTO audit_integrity_rules (id, name, trigger_event, expected_event, max_delay_hours) VALUES
        (uuid_generate_v4(), '讨论创建必须结束', 'discussion.create', 'discussion_end', 24),
        (uuid_generate_v4(), '角色生成必须完成', 'skill.generate', 'skill.generate_complete', 2)
    """)

    # 种子：默认超级管理员 (admin / audit123)
    op.execute(f"""
        INSERT INTO audit_admin_users (id, username, password_hash, display_name, role, is_active)
        VALUES (uuid_generate_v4(), 'admin', '$2b$12$s612XbaIrkOBi86a2xaNWOURxZhdI4FvX4RazNU2DLvoycVH9cB8K', '超级管理员', 'superadmin', true)
    """)


def downgrade() -> None:
    op.drop_table('audit_integrity_rules')
    op.drop_table('audit_retention_policy')
    op.drop_index('idx_acl_admin_created', 'audit_access_log')
    op.drop_table('audit_access_log')
    op.drop_table('audit_admin_users')
    op.drop_index('idx_ae_type_created', 'audit_events')
    op.drop_index('idx_ae_level_created', 'audit_events')
    op.drop_column('audit_events', 'level')
