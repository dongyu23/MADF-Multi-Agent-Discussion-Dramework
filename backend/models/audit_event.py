import uuid

from sqlalchemy import UUID, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class AuditEvent(BaseMixin, Base):
    __tablename__ = "audit_events"

    discussion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discussions.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    level: Mapped[str] = mapped_column(String(4), nullable=False, default="P2")

    __table_args__ = (
        Index("idx_ae_discussion_created", "discussion_id", "created_at"),
        Index("idx_ae_user_created", "user_id", "created_at"),
    )
