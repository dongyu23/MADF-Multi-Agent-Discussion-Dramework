"""MADF Audit Backend — 独立审计服务（旁路半独立架构）

- 独立端口 8001，独立 JWT 认证
- 只读 PostgreSQL 用户连接
- Redis Pub/Sub 订阅实时事件 → SSE 推前端
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from audit_backend.middleware import access_log as access_log_mw
from audit_backend.middleware import cors as cors_mw


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="MADF Audit", version="1.0.0", lifespan=lifespan)
cors_mw.setup(app)
access_log_mw.setup(app)

from audit_backend.core.exception_handlers import register_handlers
from audit_backend.services.admin_proxy.router import router as admin_proxy_router
from audit_backend.services.auth import router as auth_router
from audit_backend.services.events import router as events_router
from audit_backend.services.realtime import router as sse_router
from audit_backend.services.settings import router as settings_router
from audit_backend.services.stats import router as stats_router

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(stats_router)
app.include_router(sse_router)
app.include_router(settings_router)
app.include_router(admin_proxy_router)
register_handlers(app)
