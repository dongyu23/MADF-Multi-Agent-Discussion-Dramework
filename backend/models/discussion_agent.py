import uuid

from sqlalchemy import UUID, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class DiscussionAgent(BaseMixin, Base):
    __tablename__ = "discussion_agents"

    discussion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index("idx_da_discussion", "discussion_id"),
        Index("idx_da_skill", "skill_id"),
    )
