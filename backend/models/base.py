import uuid
from datetime import datetime, timezone

from sqlalchemy import UUID, DateTime, Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class BaseMixin:
    """所有数据库实体的通用字段 Mixin。

    - id: UUID v4 主键
    - created_at: 创建时间（数据库自动维护）
    - updated_at: 更新时间（数据库自动维护，ON UPDATE）
    - deleted_at: 软删除标记（NULL 表示未删除）
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
