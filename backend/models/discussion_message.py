import uuid

from sqlalchemy import UUID, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class DiscussionMessage(BaseMixin, Base):
    __tablename__ = "discussion_messages"

    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    agent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "message_type IN ('host_intro', 'host_summary', 'agent_think', 'agent_speak', 'user_intervene')",
            name="ck_dm_message_type",
        ),
        Index(
            "idx_dm_discussion_round_created",
            "discussion_id",
            "round_number",
            "created_at",
        ),
    )
