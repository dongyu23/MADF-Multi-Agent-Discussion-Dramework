import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_username(self, username: str) -> User | None:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.username == username,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_phone(self, phone: str) -> User | None:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.phone == phone,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, username: str, password_hash: str, phone: str | None) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            phone=phone,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
