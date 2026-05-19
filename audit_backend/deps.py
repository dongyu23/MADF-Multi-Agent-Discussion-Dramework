from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from audit_backend.config import settings

DATABASE_URL = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_audit_db():
    async with async_session_factory() as session:
        yield session
