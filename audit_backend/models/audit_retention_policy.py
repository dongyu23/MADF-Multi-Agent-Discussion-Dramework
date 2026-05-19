import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from audit_backend.models.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditRetentionPolicy(Base):
    __tablename__ = "audit_retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hot_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    warm_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    cold_days: Mapped[int] = mapped_column(Integer, nullable=False, default=730)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow, nullable=False
    )
