import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from audit_backend.middleware.auth import get_current_admin
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.services.realtime.sse_manager import AuditSSEManager

router = APIRouter(prefix="/api/v1/audit", tags=["audit-sse"])

sse_manager = AuditSSEManager()


@router.on_event("startup")
async def startup_sse():
    await sse_manager.start()


@router.on_event("shutdown")
async def shutdown_sse():
    await sse_manager.stop()


@router.get("/sse/stream")
async def audit_sse_stream(
    request: Request,
    admin: AuditAdminUser = Depends(get_current_admin),
):
    queue: asyncio.Queue = await sse_manager.subscribe(str(admin.id))

    async def event_generator():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_type = data.get("event", "message")
                    payload = data.get("payload", {})
                    import json
                    yield f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            await sse_manager.unsubscribe(str(admin.id))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
