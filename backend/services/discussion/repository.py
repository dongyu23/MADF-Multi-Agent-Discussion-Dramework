import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.discussion import Discussion
from backend.models.discussion_agent import DiscussionAgent
from backend.models.discussion_message import DiscussionMessage


class DiscussionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_discussion(
        self, owner_id: uuid.UUID, topic: str, duration: int
    ) -> Discussion:
        disc = Discussion(owner_id=owner_id, topic=topic, duration=duration, status="pending")
        self.session.add(disc)
        await self.session.commit()
        await self.session.refresh(disc)
        return disc

    async def add_agents(self, discussion_id: uuid.UUID, skill_ids: list[uuid.UUID]) -> None:
        for sid in skill_ids:
            self.session.add(DiscussionAgent(discussion_id=discussion_id, skill_id=sid))
        await self.session.commit()

    async def start_discussion(self, discussion_id: uuid.UUID) -> Discussion | None:
        disc = await self.find_by_id(discussion_id)
        if disc:
            disc.status = "running"
            disc.started_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(disc)
        return disc

    async def end_discussion(self, discussion_id: uuid.UUID) -> Discussion | None:
        disc = await self.find_by_id(discussion_id)
        if disc:
            disc.status = "completed"
            disc.ended_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(disc)
        return disc

    async def set_error(self, discussion_id: uuid.UUID) -> None:
        disc = await self.find_by_id(discussion_id)
        if disc:
            disc.status = "error"
            disc.ended_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def find_by_id(self, discussion_id: uuid.UUID) -> Discussion | None:
        stmt = select(Discussion).where(
            Discussion.deleted_at.is_(None), Discussion.id == discussion_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self, owner_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Discussion], int]:
        base = select(Discussion).where(
            Discussion.deleted_at.is_(None), Discussion.owner_id == owner_id
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Discussion.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def add_message(
        self,
        discussion_id: uuid.UUID,
        round_number: int,
        agent_id: uuid.UUID | None,
        agent_name: str | None,
        message_type: str,
        content: str,
        confidence: float | None = None,
    ) -> DiscussionMessage:
        msg = DiscussionMessage(
            discussion_id=discussion_id,
            round_number=round_number,
            agent_id=agent_id,
            agent_name=agent_name,
            message_type=message_type,
            content=content,
            confidence=confidence,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def get_messages(
        self, discussion_id: uuid.UUID, after: str | None = None, limit: int = 50
    ) -> list[DiscussionMessage]:
        stmt = select(DiscussionMessage).where(
            DiscussionMessage.deleted_at.is_(None),
            DiscussionMessage.discussion_id == discussion_id,
        ).order_by(DiscussionMessage.created_at.asc())
        if after:
            stmt = stmt.where(DiscussionMessage.created_at > datetime.fromisoformat(after))
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, discussion_id: uuid.UUID) -> None:
        disc = await self.find_by_id(discussion_id)
        if disc:
            disc.deleted_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def get_agents(self, discussion_id: uuid.UUID) -> list[DiscussionAgent]:
        stmt = select(DiscussionAgent).where(
            DiscussionAgent.deleted_at.is_(None),
            DiscussionAgent.discussion_id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
