import uuid
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.config import settings
from audit_backend.core.exceptions import ForbiddenException, UnauthorizedException
from audit_backend.deps import get_audit_db
from audit_backend.models.audit_admin_user import AuditAdminUser

security_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    session: AsyncSession = Depends(get_audit_db),
) -> AuditAdminUser:
    if credentials is None:
        raise UnauthorizedException("缺少认证令牌")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        admin_id: str = payload.get("sub", "")
        if not admin_id:
            raise UnauthorizedException("无效的令牌")
    except JWTError:
        raise UnauthorizedException("令牌无效或已过期")

    stmt = select(AuditAdminUser).where(AuditAdminUser.id == uuid.UUID(admin_id))
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if admin is None:
        raise UnauthorizedException("管理员不存在")
    if not admin.is_active:
        raise UnauthorizedException("管理员已禁用")

    return admin


def require_role(*roles: str):
    async def role_checker(
        admin: AuditAdminUser = Depends(get_current_admin),
    ) -> AuditAdminUser:
        if admin.role not in roles:
            raise ForbiddenException("权限不足")
        return admin

    return role_checker
