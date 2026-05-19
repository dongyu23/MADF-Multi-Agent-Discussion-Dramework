import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import settings
from backend.core.exception_handlers import register_exception_handlers
from backend.core.responses import Result
from backend.deps import async_engine
from backend.middleware.cors import configure_cors
from backend.services.admin import router as admin_router
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

app.include_router(admin_router)
app.include_router(user_router)
app.include_router(character_router)
app.include_router(discussion_router)
app.include_router(realtime_router)


@app.get("/api/v1/health")
async def health() -> Result[str]:
    return Result.ok(f"{settings.app_name} is running")


@app.get("/api/v1/health/detailed")
async def health_detailed() -> Result[dict]:
    import asyncio
    import time

    import httpx
    from sqlalchemy import text

    from backend.deps import async_session_factory

    result = {"app": settings.app_name, "components": {}}

    # DB
    t0 = time.monotonic()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        result["components"]["database"] = {"status": "healthy", "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as e:
        result["components"]["database"] = {"status": "unhealthy", "error": str(e)[:200]}

    # Redis
    t0 = time.monotonic()
    try:
        import redis.asyncio as aioredis
        import os
        r = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
        )
        await asyncio.wait_for(r.ping(), timeout=3)
        await r.close()
        result["components"]["redis"] = {"status": "healthy", "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as e:
        result["components"]["redis"] = {"status": "unhealthy", "error": str(e)[:200]}

    # LLM API (lightweight: just check connectivity)
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.llm_api_base}/models",
                headers={"Authorization": f"Bearer {settings.llm_api_key or ''}"})
        result["components"]["llm_api"] = {"status": "healthy" if resp.status_code < 500 else "degraded",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1), "http_status": resp.status_code}
    except Exception as e:
        result["components"]["llm_api"] = {"status": "unhealthy", "error": str(e)[:200]}

    return Result.ok(result)
