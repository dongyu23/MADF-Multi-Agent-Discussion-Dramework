from fastapi import APIRouter, Depends, Query

from backend.core.responses import Result
from backend.services.audit.schemas import AuditEventResponse, AuditQueryParams
from backend.services.audit.service import AuditService, get_audit_service

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/discussions/{discussion_id}/audit")
async def query_audit(
    discussion_id: str,
    after: str | None = None,
    page_size: int = Query(default=50, ge=1, le=100),
    event_type: str | None = None,
    svc: AuditService = Depends(get_audit_service),
) -> Result[list[AuditEventResponse]]:
    params = AuditQueryParams(after=after, page_size=page_size, event_type=event_type)
    events = await svc.query_discussion(discussion_id, params)
    return Result.ok(events)
