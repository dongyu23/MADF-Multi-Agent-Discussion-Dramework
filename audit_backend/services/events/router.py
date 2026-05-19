import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.core.responses import Result
from audit_backend.deps import get_audit_db
from audit_backend.middleware.auth import get_current_admin
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.events.repository import AuditEventRepository
from audit_backend.services.events.schemas import (
    EventContextResponse,
    EventDetailResponse,
    EventQueryParams,
    EventQueryResponse,
)
from audit_backend.services.events.service import AuditEventService

router = APIRouter(prefix="/api/v1/audit", tags=["audit-events"])


@router.get("/events")
async def list_events(
    after: str | None = Query(None, description="Cursor: created_at ISO timestamp"),
    before: str | None = Query(None),
    page_size: int = Query(50, ge=1, le=100),
    level: str | None = Query(None, description="P0/P1/P2"),
    event_type: str | None = Query(None),
    user_id: str | None = Query(None),
    discussion_id: str | None = Query(None),
    keyword: str | None = Query(None),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    repo = AuditEventRepository(session)
    svc = AuditEventService(repo)
    params = EventQueryParams(
        after=after,
        before=before,
        page_size=page_size,
        level=level,
        event_type=event_type,
        user_id=user_id,
        discussion_id=discussion_id,
        keyword=keyword,
        sort=sort,
    )
    events, has_more = await svc.query_events(params, admin.role)
    return Result.ok(EventQueryResponse(
        items=[_to_detail(e) for e in events],
        has_more=has_more,
    ))


@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    repo = AuditEventRepository(session)
    svc = AuditEventService(repo)
    event = await svc.get_event(uuid.UUID(event_id), admin.role)
    if event is None:
        from audit_backend.core.exceptions import NotFoundException
        raise NotFoundException("审计事件不存在")
    return Result.ok(_to_detail(event))


@router.get("/events/context/{discussion_id}")
async def get_event_context(
    discussion_id: str,
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    repo = AuditEventRepository(session)
    svc = AuditEventService(repo)
    events = await svc.get_context(uuid.UUID(discussion_id))
    return Result.ok(EventContextResponse(
        discussion_id=discussion_id,
        events=[_to_detail(e) for e in events],
        total=len(events),
    ))


@router.get("/event-types")
async def list_event_types(
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    repo = AuditEventRepository(session)
    types = await repo.get_event_types()
    return Result.ok(types)


def _to_detail(event) -> EventDetailResponse:
    return EventDetailResponse(
        id=str(event.id),
        discussion_id=str(event.discussion_id) if event.discussion_id else None,
        user_id=str(event.user_id) if event.user_id else None,
        event_type=event.event_type,
        payload=event.payload,
        level=event.level if hasattr(event, "level") else None,
        created_at=event.created_at.isoformat() if event.created_at else None,
    )
