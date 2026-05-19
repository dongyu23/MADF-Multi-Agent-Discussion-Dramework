from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.core.responses import Result
from audit_backend.deps import get_audit_db
from audit_backend.middleware.auth import get_current_admin
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.auth.schemas import LoginRequest
from audit_backend.services.auth.service import AuthService

router = APIRouter(prefix="/api/v1/audit/auth", tags=["audit-auth"])


@router.post("/login")
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_audit_db),
):
    svc = AuthService(session)
    result = await svc.login(req.username, req.password)
    return Result.ok(result)


@router.get("/me")
async def me(
    admin: AuditAdminUser = Depends(get_current_admin),
    session: AsyncSession = Depends(get_audit_db),
):
    svc = AuthService(session)
    result = await svc.get_me(admin.id)
    return Result.ok(result)


@router.post("/refresh")
async def refresh(
    admin: AuditAdminUser = Depends(get_current_admin),
):
    token = AuthService._create_token(admin)
    return Result.ok({"token": token, "token_type": "bearer"})
