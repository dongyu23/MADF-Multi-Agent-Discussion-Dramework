from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, BaseMixin


class User(BaseMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        Index("idx_users_username_unique", "username", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("idx_users_phone_unique", "phone", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )
