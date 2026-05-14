import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import settings
from backend.core.exception_handlers import register_exception_handlers
from backend.core.responses import Result
from backend.deps import async_engine
from backend.middleware.cors import configure_cors
from backend.services.audit import router as audit_router
from backend.services.character import router as character_router
from backend.services.discussion import router as discussion_router
from backend.services.realtime import router as realtime_router
from backend.services.user import router as user_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("%s starting on port 8000", settings.app_name)
    yield
    await async_engine.dispose()
    logger.info("%s shut down", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

configure_cors(app)
register_exception_handlers(app)

app.include_router(user_router)
app.include_router(character_router)
app.include_router(discussion_router)
app.include_router(realtime_router)
app.include_router(audit_router)


@app.get("/api/v1/health")
async def health() -> Result[str]:
    return Result.ok(f"{settings.app_name} is running")
