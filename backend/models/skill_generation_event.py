import uuid

from sqlalchemy import UUID, BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class SkillGenerationEvent(BaseMixin, Base):
    __tablename__ = "skill_generation_events"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("skill_id", "seq", name="uq_sge_skill_seq"),
        Index("idx_sge_skill_seq", "skill_id", "seq"),
        Index("idx_sge_owner_created", "owner_id", "created_at"),
    )
