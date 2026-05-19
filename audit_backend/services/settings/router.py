import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.core.responses import Result
from audit_backend.deps import get_audit_db
from audit_backend.middleware.auth import require_role
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.settings.schemas import (
    AdminListResponse,
    AdminUserResponse,
    CreateAdminRequest,
    RetentionPolicyResponse,
    UpdateAdminRequest,
    UpdateRetentionPolicyRequest,
)
from audit_backend.services.settings.service import SettingsService

router = APIRouter(prefix="/api/v1/audit", tags=["audit-settings"])


@router.get("/settings/admins")
async def list_admins(
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(require_role("superadmin")),
):
    svc = SettingsService(session)
    admins = await svc.list_admins()
    return Result.ok(AdminListResponse(
        items=[AdminUserResponse(**a) for a in admins]
    ))


@router.post("/settings/admins")
async def create_admin(
    req: CreateAdminRequest,
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(require_role("superadmin")),
):
    svc = SettingsService(session)
    created = await svc.create_admin(
        username=req.username,
        password=req.password,
        display_name=req.display_name,
        role=req.role,
    )
    return Result.ok(AdminUserResponse(**created))


@router.put("/settings/admins/{admin_id}")
async def update_admin(
    admin_id: str,
    req: UpdateAdminRequest,
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(require_role("superadmin")),
):
    svc = SettingsService(session)
    updated = await svc.update_admin(
        admin_id=uuid.UUID(admin_id),
        username=req.username,
        password=req.password,
        display_name=req.display_name,
        role=req.role,
        is_active=req.is_active,
    )
    return Result.ok(AdminUserResponse(**updated))


@router.delete("/settings/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(require_role("superadmin")),
):
    svc = SettingsService(session)
    await svc.delete_admin(uuid.UUID(admin_id))
    return Result.ok(None)


@router.get("/settings/retention")
async def get_retention_policies(
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(require_role("superadmin")),
):
    svc = SettingsService(session)
    policies = await svc.get_retention_policies()
    return Result.ok([RetentionPolicyResponse(**p) for p in policies])


@router.put("/settings/retention/{policy_id}")
async def update_retention_policy(
    policy_id: str,
    req: UpdateRetentionPolicyRequest,
    session: AsyncSession = Depends(get_audit_db),
    admin: AuditAdminUser = Depends(require_role("superadmin")),
):
    svc = SettingsService(session)
    updated = await svc.update_retention_policy_by_id(
        policy_id=uuid.UUID(policy_id),
        name=req.name,
        hot_days=req.hot_days,
        warm_days=req.warm_days,
        cold_days=req.cold_days,
        is_active=req.is_active,
    )
    return Result.ok(RetentionPolicyResponse(**updated))
