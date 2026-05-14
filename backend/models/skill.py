import uuid

from sqlalchemy import UUID, Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class Skill(BaseMixin, Base):
    __tablename__ = "skills"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ready"
    )
    source_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('generating', 'ready', 'error')", name="ck_skills_status"),
        Index("idx_skills_owner_created", "owner_id", "created_at"),
        Index(
            "idx_skills_owner_name_unique",
            "owner_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_skills_public_created",
            "is_public",
            "created_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
