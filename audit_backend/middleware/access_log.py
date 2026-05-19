import asyncio
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from audit_backend.deps import async_session_factory
from audit_backend.models.audit_access_log import AuditAccessLog


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        admin_id = None
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            from jose import jwt

            from audit_backend.config import settings

            try:
                payload = jwt.decode(
                    token[7:],
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                )
                admin_id = payload.get("sub", "")
            except Exception:
                pass

        if admin_id:
            asyncio.create_task(
                _write_access_log(
                    admin_id=uuid.UUID(admin_id),
                    action=_derive_action(request),
                    query_params=str(request.query_params) if request.query_params else None,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", ""),
                )
            )

        return response


def _derive_action(request: Request) -> str:
    method = request.method
    path = request.url.path
    if path.startswith("/api/v1/audit/auth"):
        return f"auth:{method}:{path.split('/')[-1]}"
    return f"{method}:{path}"


async def _write_access_log(
    admin_id: uuid.UUID,
    action: str,
    query_params: str | None,
    ip_address: str | None,
    user_agent: str | None,
):
    try:
        async with async_session_factory() as session:
            log_entry = AuditAccessLog(
                admin_user_id=admin_id,
                action=action,
                query_params=query_params,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(log_entry)
            await session.commit()
    except Exception:
        pass


def setup(app: FastAPI):
    app.add_middleware(AccessLogMiddleware)
