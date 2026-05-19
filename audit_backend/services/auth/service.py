import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.config import settings
from audit_backend.core.exceptions import UnauthorizedException
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.auth.schemas import AdminUserResponse, TokenResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, username: str, password: str) -> TokenResponse:
        stmt = select(AuditAdminUser).where(
            AuditAdminUser.username == username,
            AuditAdminUser.is_active == True,
        )
        result = await self.session.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            raise UnauthorizedException("用户名或密码错误")

        if not pwd_context.verify(password, admin.password_hash):
            raise UnauthorizedException("用户名或密码错误")

        admin.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()

        token = self._create_token(admin)
        return TokenResponse(
            token=token,
            admin_user=AdminUserResponse(
                id=str(admin.id),
                username=admin.username,
                display_name=admin.display_name,
                role=admin.role,
            ),
        )

    async def get_me(self, admin_id: uuid.UUID) -> AdminUserResponse:
        stmt = select(AuditAdminUser).where(
            AuditAdminUser.id == admin_id,
            AuditAdminUser.is_active == True,
        )
        result = await self.session.execute(stmt)
        admin = result.scalar_one_or_none()
        if admin is None:
            raise UnauthorizedException("管理员不存在")
        return AdminUserResponse(
            id=str(admin.id),
            username=admin.username,
            display_name=admin.display_name,
            role=admin.role,
        )

    @staticmethod
    def _create_token(admin: AuditAdminUser) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(admin.id),
            "role": admin.role,
            "exp": expire,
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
