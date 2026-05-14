import uuid
from datetime import datetime

from sqlalchemy import UUID, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin, utcnow


class Discussion(BaseMixin, Base):
    __tablename__ = "discussions"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)  # seconds
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'starting', 'running', 'completed', 'error')",
            name="ck_discussions_status",
        ),
        Index("idx_discussions_user_created", "owner_id", "created_at"),
    )
