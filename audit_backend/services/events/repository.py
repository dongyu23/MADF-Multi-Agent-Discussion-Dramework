import uuid
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.models.audit_event import AuditEvent
from audit_backend.services.events.schemas import EventQueryParams


class AuditEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def query_events(
        self, params: EventQueryParams
    ) -> tuple[list[AuditEvent], bool]:
        stmt = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None),
        )

        if params.after:
            stmt = stmt.where(AuditEvent.created_at > datetime.fromisoformat(params.after))
        if params.before:
            stmt = stmt.where(AuditEvent.created_at < datetime.fromisoformat(params.before))
        if params.event_type:
            stmt = stmt.where(AuditEvent.event_type == params.event_type)
        if params.user_id:
            stmt = stmt.where(AuditEvent.user_id == uuid.UUID(params.user_id))
        if params.discussion_id:
            stmt = stmt.where(AuditEvent.discussion_id == uuid.UUID(params.discussion_id))
        if params.level:
            stmt = stmt.where(AuditEvent.level == params.level)
        if params.keyword:
            search = f"%{params.keyword}%"
            stmt = stmt.where(
                AuditEvent.event_type.ilike(search)
                | func.cast(AuditEvent.payload, text("text")).ilike(search)
            )

        stmt = stmt.order_by(AuditEvent.created_at.desc())

        stmt = stmt.limit(params.page_size + 1)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > params.page_size
        return rows[:params.page_size], has_more

    async def get_event(self, event_id: uuid.UUID) -> AuditEvent | None:
        stmt = select(AuditEvent).where(
            AuditEvent.id == event_id,
            AuditEvent.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_context(self, discussion_id: uuid.UUID) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.discussion_id == discussion_id,
                AuditEvent.deleted_at.is_(None),
            )
            .order_by(AuditEvent.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_event_types(self) -> list[str]:
        stmt = (
            select(AuditEvent.event_type)
            .where(AuditEvent.deleted_at.is_(None))
            .distinct()
            .order_by(AuditEvent.event_type)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
