import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import settings

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    settings.db_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(async_engine.sync_engine, "handle_error")
def _handle_db_error(context):
    """DB 连接池异常监听——连接失败/池溢出时记录审计事件。"""
    try:
        from backend.services.audit.repository import AuditRepository
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(_record_db_error(context))
    except Exception:
        logger.warning("Failed to dispatch db pool error audit")


async def _record_db_error(context):
    try:
        async with async_session_factory() as session:
            repo = AuditRepository(session)
            original = context.original_exception
            await repo.record(
                discussion_id=None, user_id=None,
                event_type="system.db_pool_error",
                payload={
                    "exception_type": type(original).__name__,
                    "exception_message": str(original)[:500],
                },
                level="P0",
            )
    except Exception:
        logger.warning("Failed to record system.db_pool_error audit event")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> str:
    if credentials is None:
        return ""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub", "")
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def require_user(
    user_id: str = Depends(get_current_user),
) -> str:
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user_id
