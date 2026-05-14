"""Unified audit event recording — cross-cutting infrastructure.

All modules call AuditService.record() to log business events.
The discussion orchestrator pushes events here for complete traceability.
"""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.deps import get_db
from backend.services.audit.repository import AuditRepository
from backend.services.audit.schemas import AuditEventResponse, AuditQueryParams


class AuditService:
    def __init__(self, session: AsyncSession):
        self.repo = AuditRepository(session)

    async def record(
        self,
        event_type: str,
        payload: dict,
        discussion_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AuditEventResponse:
        event = await self.repo.record(discussion_id, user_id, event_type, payload)
        return AuditService._to_response(event)

    async def query_discussion(self, discussion_id: str, params: AuditQueryParams) -> list[AuditEventResponse]:
        events = await self.repo.query(
            uuid.UUID(discussion_id),
            after=params.after,
            page_size=params.page_size,
            event_type=params.event_type,
        )
        return [AuditService._to_response(e) for e in events]

    @staticmethod
    def _to_response(e) -> AuditEventResponse:
        return AuditEventResponse(
            id=str(e.id),
            discussion_id=str(e.discussion_id) if e.discussion_id else None,
            user_id=str(e.user_id) if e.user_id else None,
            event_type=e.event_type,
            payload=e.payload or {},
            created_at=e.created_at.isoformat(),
        )


async def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(db)
