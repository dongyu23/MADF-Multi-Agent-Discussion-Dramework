import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.audit.repository import AuditRepository
from backend.services.user.repository import UserRepository
from backend.services.user.schemas import TokenResponse, UserResponse


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.audit = AuditRepository(session)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def register(self, username: str, password: str, phone: str | None) -> tuple[TokenResponse, UserResponse]:
        existing = await self.repo.find_by_username(username)
        if existing:
            raise BusinessException(ErrorCode.USERNAME_EXISTS, f"Username '{username}' already taken")

        if phone:
            existing_phone = await self.repo.find_by_phone(phone)
            if existing_phone:
                raise BusinessException(ErrorCode.PHONE_EXISTS, f"Phone '{phone}' already registered")

        password_hash = self.pwd_context.hash(password)
        user = await self.repo.create(username, password_hash, phone)
        token = self._issue_token(user.id)

        # P1: Audit account creation
        await self.audit.record(None, user.id, "user.register", {
            "username": username, "phone": phone,
        })

        return token, UserService._to_response(user)

    async def login(self, username: str, password: str) -> tuple[TokenResponse, UserResponse]:
        user = await self.repo.find_by_username(username)
        if not user:
            # P0: Audit failed login — user not found
            await self.audit.record(None, None, "user.login_failed", {
                "username": username, "reason": "user_not_found",
            })
            raise BusinessException(ErrorCode.USER_NOT_FOUND, "Invalid username or password")

        if not self.pwd_context.verify(password, user.password_hash):
            # P0: Audit failed login — wrong password
            await self.audit.record(None, user.id, "user.login_failed", {
                "username": username, "reason": "wrong_password",
            })
            raise BusinessException(ErrorCode.WRONG_PASSWORD, "Invalid username or password")

        token = self._issue_token(user.id)

        # P0: Audit successful login
        await self.audit.record(None, user.id, "user.login", {"username": username})

        return token, UserService._to_response(user)

    async def get_me(self, user_id: str) -> UserResponse:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_by_id(uid)
        if not user:
            raise BusinessException(ErrorCode.USER_NOT_FOUND)
        return UserService._to_response(user)

    def _issue_token(self, user_id: uuid.UUID) -> TokenResponse:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {"sub": str(user_id), "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return TokenResponse(token=token)

    @staticmethod
    def _to_response(user) -> UserResponse:
        return UserResponse(
            id=str(user.id), username=user.username, phone=user.phone,
            created_at=user.created_at.isoformat(),
        )


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)
