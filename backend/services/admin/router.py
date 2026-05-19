import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.responses import Result
from backend.deps import get_db
from backend.middleware.admin_auth import verify_admin_service
from backend.services.admin.schemas import (
    AdminUserItem,
    AuditEventItem,
    AuditEventListResponse,
    CharacterAdminDetail,
    CharacterAdminItem,
    CharacterAdminListResponse,
    CreateAdminRequest,
    CreateUserRequest,
    DiscussionAdminDetail,
    DiscussionAdminItem,
    DiscussionAdminListResponse,
    DiscussionMessageInfo,
    DiscussionTokenUsageResponse,
    GalleryAdminItem,
    GalleryAdminListResponse,
    HealthErrorItem,
    HealthErrorListResponse,
    HealthLoadInfo,
    HealthOverview,
    OperationAuditItem,
    OperationAuditListResponse,
    OrphanDiscussion,
    ResetPasswordRequest,
    RestartResponse,
    SettingsResponse,
    StatsOverview,
    TokenTrendPoint,
    TokenUsageSummary,
    UpdateAdminRequest,
    UpdateCharacterVisibilityRequest,
    UpdatePhoneRequest,
    UpdateRetentionRequest,
    UpdateSettingsRequest,
    UpdateUserStatusRequest,
    UpdateUsernameRequest,
    UserAdminDetail,
    UserAdminItem,
    UserAdminListResponse,
)
from backend.services.admin.service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _get_svc(db: AsyncSession = Depends(get_db)) -> AdminService:
    return AdminService(db)


# ═══════════════════════════════════════════
# User Management (6)
# ═══════════════════════════════════════════

@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    sort_by: str | None = Query(default="created_at"),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[UserAdminListResponse]:
    data = await svc.list_users(page=page, page_size=page_size, search=search, sort_by=sort_by)
    return Result.ok(UserAdminListResponse(**data))


@router.post("/users")
async def create_user(
    req: CreateUserRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.create_user(req.username, req.password, req.phone, admin)
    return Result.ok(data)


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[UserAdminDetail]:
    data = await svc.get_user_detail(user_id, admin)
    if data is None:
        return Result.fail(2003, "User not found")
    return Result.ok(UserAdminDetail(**data))


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    req: UpdateUserStatusRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.update_user_status(user_id, req.status, admin)
    if data is None:
        return Result.fail(2003, "User not found")
    return Result.ok(data)


@router.put("/users/{user_id}/username")
async def change_username(
    user_id: str,
    req: UpdateUsernameRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.change_username(user_id, req.username, admin)
    if data is None:
        return Result.fail(2003, "User not found")
    return Result.ok(data)


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    req: ResetPasswordRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.reset_password(user_id, req.new_password, admin)
    if data is None:
        return Result.fail(2003, "User not found")
    return Result.ok(data)


@router.put("/users/{user_id}/phone")
async def update_user_phone(
    user_id: str,
    req: UpdatePhoneRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.update_user_phone(user_id, req.phone, admin)
    if data is None:
        return Result.fail(2003, "User not found")
    return Result.ok(data)


@router.get("/users/{user_id}/token-usage")
async def get_user_token_usage(
    user_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.get_user_token_usage(user_id)
    if data is None:
        return Result.fail(2003, "User not found")
    return Result.ok(data)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    ok = await svc.delete_user(user_id, admin)
    if not ok:
        return Result.fail(2003, "User not found")
    return Result.ok({"message": "User permanently deleted"})


# ═══════════════════════════════════════════
# Discussion Monitoring (6)
# ═══════════════════════════════════════════

@router.get("/discussions")
async def list_discussions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    username: str | None = Query(default=None),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[DiscussionAdminListResponse]:
    data = await svc.list_discussions(
        page=page, page_size=page_size, status=status, search=search, owner_id=owner_id,
        username=username,
    )
    return Result.ok(DiscussionAdminListResponse(**data))


@router.get("/discussions/{discussion_id}")
async def get_discussion_detail(
    discussion_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[DiscussionAdminDetail]:
    data = await svc.get_discussion_detail(discussion_id)
    if data is None:
        return Result.fail(4001, "Discussion not found")
    return Result.ok(DiscussionAdminDetail(**data))


@router.get("/discussions/{discussion_id}/stream")
async def get_discussion_stream(
    discussion_id: str,
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    return Result.ok({
        "message": "SSE streaming is available at /api/v1/discussions/{id}/stream on the main API.",
        "discussion_id": discussion_id,
        "note": "Connect to the main realtime SSE endpoint to receive streaming events.",
    })


@router.get("/discussions/{discussion_id}/messages")
async def get_discussion_messages(
    discussion_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[list[DiscussionMessageInfo]]:
    detail = await svc.get_discussion_detail(discussion_id)
    if detail is None:
        return Result.fail(4001, "Discussion not found")
    return Result.ok([DiscussionMessageInfo(**m) for m in detail.get("messages", [])])


@router.delete("/discussions/{discussion_id}")
async def delete_discussion(
    discussion_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    ok = await svc.delete_discussion(discussion_id, admin)
    if not ok:
        return Result.fail(4001, "Discussion not found")
    return Result.ok({"message": "Discussion soft-deleted successfully"})


@router.get("/discussions/{discussion_id}/token-usage")
async def get_discussion_token_usage(
    discussion_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[DiscussionTokenUsageResponse]:
    data = await svc.get_discussion_token_usage(discussion_id)
    if data is None:
        return Result.fail(4001, "Discussion not found")
    return Result.ok(DiscussionTokenUsageResponse(**data))


# ═══════════════════════════════════════════
# Character Management (4)
# ═══════════════════════════════════════════

@router.get("/characters")
async def list_characters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    is_public: bool | None = Query(default=None),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[CharacterAdminListResponse]:
    data = await svc.list_characters(
        page=page, page_size=page_size, search=search,
        status=status, owner_id=owner_id, is_public=is_public,
    )
    return Result.ok(CharacterAdminListResponse(**data))


@router.get("/characters/{character_id}")
async def get_character_detail(
    character_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[CharacterAdminDetail]:
    data = await svc.get_character_detail(character_id)
    if data is None:
        return Result.fail(3001, "Character not found")
    return Result.ok(CharacterAdminDetail(**data))


@router.put("/characters/{character_id}/visibility")
async def update_character_visibility(
    character_id: str,
    req: UpdateCharacterVisibilityRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.update_character_visibility(character_id, req.is_public, admin)
    if data is None:
        return Result.fail(3001, "Character not found")
    return Result.ok(data)


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    ok = await svc.delete_character(character_id, admin)
    if not ok:
        return Result.fail(3001, "Character not found")
    return Result.ok({"message": "Character soft-deleted successfully"})


# ═══════════════════════════════════════════
# Gallery Management (2)
# ═══════════════════════════════════════════

@router.get("/gallery")
async def list_gallery(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[GalleryAdminListResponse]:
    data = await svc.list_gallery(page=page, page_size=page_size, search=search)
    return Result.ok(GalleryAdminListResponse(**data))


@router.delete("/gallery/{gallery_id}")
async def unlist_gallery(
    gallery_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    ok = await svc.unlist_gallery(gallery_id, admin)
    if not ok:
        return Result.fail(3001, "Character not found")
    return Result.ok({"message": "Character removed from public gallery"})


# ═══════════════════════════════════════════
# Audit & Trace (4)
# ═══════════════════════════════════════════

@router.get("/audit/events")
async def list_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    event_type: str | None = Query(default=None),
    level: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    discussion_id: str | None = Query(default=None),
    after: str | None = Query(default=None),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[AuditEventListResponse]:
    data = await svc.list_audit_events(
        page=page, page_size=page_size,
        event_type=event_type, level=level,
        user_id=user_id, discussion_id=discussion_id,
        after=after,
    )
    return Result.ok(AuditEventListResponse(**data))


@router.get("/audit/events/{event_id}")
async def get_audit_event(
    event_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[AuditEventItem]:
    data = await svc.get_audit_event(event_id)
    if data is None:
        return Result.fail(5001, "Audit event not found")
    return Result.ok(AuditEventItem(**data))


@router.get("/audit/operations")
async def list_operations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    event_type: str | None = Query(default=None),
    admin_id: str | None = Query(default=None),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[OperationAuditListResponse]:
    data = await svc.list_operations(
        page=page, page_size=page_size,
        event_type=event_type, admin_id=admin_id,
    )
    return Result.ok(OperationAuditListResponse(**data))


@router.get("/audit/operations/{operation_id}")
async def get_operation(
    operation_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[OperationAuditItem]:
    data = await svc.get_operation(operation_id)
    if data is None:
        return Result.fail(5001, "Operation audit not found")
    return Result.ok(OperationAuditItem(**data))


# ═══════════════════════════════════════════
# System Health (5)
# ═══════════════════════════════════════════

@router.get("/health/overview")
async def get_health_overview(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[HealthOverview]:
    data = await svc.get_health_overview()
    return Result.ok(HealthOverview(**data))


@router.get("/health/errors")
async def get_health_errors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[HealthErrorListResponse]:
    data = await svc.get_health_errors(page=page, page_size=page_size)
    return Result.ok(HealthErrorListResponse(**data))


@router.get("/health/errors/{error_id}")
async def get_health_error(
    error_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[HealthErrorItem]:
    data = await svc.get_health_error(error_id)
    if data is None:
        return Result.fail(5001, "Error event not found")
    return Result.ok(HealthErrorItem(
        id=data["id"],
        event_type=data["event_type"],
        level=data["level"],
        message=data["payload"].get("exception_message", data["event_type"]),
        created_at=data["created_at"],
    ))


@router.get("/health/load")
async def get_health_load(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[HealthLoadInfo]:
    data = await svc.get_health_load()
    return Result.ok(HealthLoadInfo(**data))


@router.get("/health/orphan-discussions")
async def get_orphan_discussions(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[list[OrphanDiscussion]]:
    data = await svc.get_orphan_discussions()
    return Result.ok([OrphanDiscussion(**d) for d in data])


# ═══════════════════════════════════════════
# Stats (3)
# ═══════════════════════════════════════════

@router.get("/stats/overview")
async def get_stats_overview(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[StatsOverview]:
    data = await svc.get_stats_overview()
    return Result.ok(StatsOverview(**data))


@router.get("/stats/tokens")
async def get_token_stats(
    time_range: str = Query(default="7d", pattern="^(1d|7d|30d|90d)$"),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[TokenUsageSummary]:
    data = await svc.get_token_stats(time_range)
    return Result.ok(TokenUsageSummary(**data))


@router.get("/stats/tokens/trend")
async def get_token_trend(
    days: int = Query(default=7, ge=1, le=90),
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[list[TokenTrendPoint]]:
    data = await svc.get_token_trend(days)
    return Result.ok([TokenTrendPoint(**d) for d in data])


# ═══════════════════════════════════════════
# Admin Management (4)
# ═══════════════════════════════════════════

@router.get("/admins")
async def list_admins(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[list[AdminUserItem]]:
    data = await svc.list_admins()
    return Result.ok([AdminUserItem(**d) for d in data])


@router.post("/admins")
async def create_admin(
    req: CreateAdminRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[AdminUserItem]:
    data = await svc.create_admin(req.username, req.password, req.role, admin)
    return Result.ok(AdminUserItem(**data))


@router.put("/admins/{admin_id}")
async def update_admin(
    admin_id: str,
    req: UpdateAdminRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[AdminUserItem]:
    data = await svc.update_admin(
        admin_id, req.username, req.password, req.role, admin,
    )
    if data is None:
        return Result.fail(2003, "Admin not found")
    return Result.ok(AdminUserItem(**data))


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    ok = await svc.delete_admin(admin_id, admin)
    if not ok:
        return Result.fail(2003, "Admin not found")
    return Result.ok({"message": "Admin deleted successfully"})


# ═══════════════════════════════════════════
# Settings (4)
# ═══════════════════════════════════════════

@router.get("/settings")
async def get_settings(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[SettingsResponse]:
    data = await svc.get_settings()
    return Result.ok(SettingsResponse(**data))


@router.put("/settings")
async def update_settings(
    req: UpdateSettingsRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    req_dict = req.model_dump(exclude_none=True)
    data = await svc.update_settings(req_dict, admin)
    return Result.ok(data)


@router.post("/settings/restart")
async def restart_service(
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[RestartResponse]:
    data = await svc.restart_service()
    return Result.ok(RestartResponse(**data))


@router.put("/settings/retention")
async def update_retention(
    req: UpdateRetentionRequest,
    svc: AdminService = Depends(_get_svc),
    admin: dict = Depends(verify_admin_service),
) -> Result[dict]:
    data = await svc.update_retention(req.retention_days, req.dry_run, admin)
    return Result.ok(data)
