import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_event import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        discussion_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        event_type: str,
        payload: dict,
    ) -> AuditEvent:
        event = AuditEvent(
            discussion_id=discussion_id,
            user_id=user_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def query(
        self,
        discussion_id: uuid.UUID,
        after: str | None = None,
        page_size: int = 50,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        stmt = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.discussion_id == discussion_id,
        ).order_by(AuditEvent.created_at.asc())

        if after:
            stmt = stmt.where(AuditEvent.created_at > datetime.fromisoformat(after))
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)

        stmt = stmt.limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
