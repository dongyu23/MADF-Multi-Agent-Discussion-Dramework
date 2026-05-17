import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessException, ErrorCode
from backend.models.skill import Skill


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        owner_id: uuid.UUID,
        name: str,
        description: str,
        file_path: str,
        tags: list[str] | None = None,
        is_public: bool = False,
        status: str = "generating",
        source_count: int | None = None,
        model_count: int | None = None,
    ) -> Skill:
        skill = Skill(
            owner_id=owner_id,
            name=name,
            description=description,
            file_path=file_path,
            tags=tags or [],
            is_public=is_public,
            status=status,
            source_count=source_count,
            model_count=model_count,
        )
        self.session.add(skill)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS)
        await self.session.refresh(skill)
        return skill

    async def find_by_id(self, skill_id: uuid.UUID) -> Skill | None:
        stmt = select(Skill).where(Skill.deleted_at.is_(None), Skill.id == skill_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_owner_and_name(self, owner_id: uuid.UUID, name: str) -> Skill | None:
        stmt = select(Skill).where(
            Skill.deleted_at.is_(None),
            Skill.owner_id == owner_id,
            Skill.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self, owner_id: uuid.UUID, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Skill], int]:
        base = select(Skill).where(Skill.deleted_at.is_(None), Skill.owner_id == owner_id)
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Skill.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_public_gallery(
        self, after: str | None, page_size: int, search: str | None = None, tag: str | None = None
    ) -> tuple[list[Skill], bool]:
        base = select(Skill).where(
            Skill.deleted_at.is_(None),
            Skill.is_public.is_(True),
            Skill.status == "ready",
        )
        if after:
            base = base.where(Skill.created_at < datetime.fromisoformat(after))
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )

        stmt = base.order_by(Skill.created_at.desc()).limit(page_size + 1)
        result = await self.session.execute(stmt)
        skills = list(result.scalars().all())
        has_more = len(skills) > page_size
        return skills[:page_size], has_more

    async def update(self, skill: Skill, **kwargs) -> Skill:
        for key, value in kwargs.items():
            if value is not None and hasattr(skill, key):
                setattr(skill, key, value)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def soft_delete(self, skill: Skill) -> None:
        skill.deleted_at = datetime.utcnow()
        await self.session.commit()

    async def set_status(self, skill_id: uuid.UUID, status: str, extra: dict | None = None) -> Skill | None:
        skill = await self.find_by_id(skill_id)
        if not skill:
            return None
        skill.status = status
        if extra:
            for k, v in extra.items():
                if hasattr(skill, k):
                    setattr(skill, k, v)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill
