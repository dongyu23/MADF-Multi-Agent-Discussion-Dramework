"""代理路由 — 审计前端 → 审计后端 → 签发服务 JWT → 转发主系统。"""
import httpx
from fastapi import APIRouter, Depends, Request, Response

from audit_backend.middleware.auth import get_current_admin
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.admin_gateway import issue_service_token

router = APIRouter(prefix="/api/v1/admin", tags=["admin-proxy"])
BACKEND_URL = "http://127.0.0.1:8000"


async def _proxy(request: Request, admin: AuditAdminUser, path: str) -> Response:
    token = issue_service_token(str(admin.id), admin.username, admin.role)
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    headers["authorization"] = f"Bearer {token}"
    body = await request.body()
    url = f"{BACKEND_URL}/api/v1/admin/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method=request.method, url=url, headers=headers,
                                     content=body, params=dict(request.query_params))
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))


@router.api_route("/users", methods=["GET", "POST"])
async def proxy_users(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, "users")

@router.api_route("/users/{rest:path}", methods=["GET", "PUT", "DELETE"])
async def proxy_user_actions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"users/{request.path_params['rest']}")

@router.api_route("/discussions", methods=["GET"])
async def proxy_discussions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, "discussions")

@router.api_route("/discussions/{rest:path}", methods=["GET", "DELETE"])
async def proxy_discussion_actions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"discussions/{request.path_params['rest']}")

@router.api_route("/characters", methods=["GET"])
async def proxy_characters(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, "characters")

@router.api_route("/characters/{rest:path}", methods=["GET", "PUT", "DELETE"])
async def proxy_character_actions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"characters/{request.path_params['rest']}")

@router.api_route("/gallery", methods=["GET"])
async def proxy_gallery(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, "gallery")

@router.api_route("/gallery/{rest:path}", methods=["DELETE"])
async def proxy_gallery_actions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"gallery/{request.path_params['rest']}")

@router.api_route("/audit/{rest:path}", methods=["GET"])
async def proxy_audit(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"audit/{request.path_params['rest']}")

@router.api_route("/health/{rest:path}", methods=["GET"])
async def proxy_health(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"health/{request.path_params['rest']}")

@router.api_route("/stats/{rest:path}", methods=["GET"])
async def proxy_stats(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"stats/{request.path_params['rest']}")

@router.api_route("/admins", methods=["GET", "POST"])
async def proxy_admins(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, "admins")

@router.api_route("/admins/{rest:path}", methods=["PUT", "DELETE"])
async def proxy_admin_actions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"admins/{request.path_params['rest']}")

@router.api_route("/settings", methods=["GET", "PUT"])
async def proxy_settings(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, "settings")

@router.api_route("/settings/{rest:path}", methods=["POST", "PUT"])
async def proxy_settings_actions(request: Request, admin=Depends(get_current_admin)):
    return await _proxy(request, admin, f"settings/{request.path_params['rest']}")
