from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.core.responses import Result
from audit_backend.deps import get_audit_db
from audit_backend.middleware.auth import get_current_admin
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.stats.service import StatsService

router = APIRouter(prefix="/api/v1/audit", tags=["audit-stats"])


@router.get("/stats/overview")
async def get_overview(
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    svc = StatsService(session)
    overview = await svc.get_overview()
    return Result.ok(overview)


@router.get("/stats/trend")
async def get_trend(
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    svc = StatsService(session)
    trend = await svc.get_trend(days=days)
    return Result.ok(trend)


@router.get("/stats/distribution")
async def get_distribution(
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(get_current_admin),
):
    svc = StatsService(session)
    dist = await svc.get_distribution()
    return Result.ok(dist)
