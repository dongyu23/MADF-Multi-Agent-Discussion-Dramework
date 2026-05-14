"""SSE streaming endpoint with catch-up for reconnection."""

import json

import redis.asyncio as redis
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from backend.config import settings

router = APIRouter(prefix="/api/v1/discussions", tags=["realtime"])


@router.get("/{discussion_id}/stream")
async def discussion_stream(
    discussion_id: str,
    request: Request,
    after: str | None = Query(default=None),
):
    """SSE endpoint. Frontend EventSource connects here for real-time discussion events.

    Reconnection: pass `?after=ISO_TIMESTAMP` to receive missed messages first,
    then continue with the live stream.
    """

    async def event_generator():
        # ── Catch-up phase: push missed messages from PG ──
        if after:
            from uuid import UUID
            from backend.deps import async_session_factory
            from backend.services.discussion.repository import DiscussionRepository

            async with async_session_factory() as session:
                repo = DiscussionRepository(session)
                msgs = await repo.get_messages(UUID(discussion_id), after=after, limit=200)

                count = len(msgs)
                if count > 20:
                    # Summary + recent messages for large gaps
                    yield f"event: catchup_summary\ndata: {json.dumps({'missed': count, 'showing_recent': 20})}\n\n"
                    msgs = msgs[-20:]
                elif count > 0:
                    yield f"event: catchup_start\ndata: {json.dumps({'missed': count})}\n\n"

                for m in msgs:
                    data = json.dumps({
                        "agent_name": m.agent_name,
                        "content": m.content,
                        "round": m.round_number,
                        "message_type": m.message_type,
                    }, ensure_ascii=False)
                    event_type = "agent_speak_chunk" if m.message_type == "agent_speak" else m.message_type
                    yield f"event: {event_type}\ndata: {data}\n\n"

                if count > 0:
                    yield f"event: catchup_end\ndata: {{}}\n\n"

        # ── Live phase: subscribe to Redis ──
        r = redis.from_url(settings.redis_url, decode_responses=True)
        channel = f"discussion:{discussion_id}:events"
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        try:
            yield "event: heartbeat\ndata: {}\n\n"

            async for msg in pubsub.listen():
                if await request.is_disconnected():
                    break
                if msg["type"] == "message":
                    payload = json.loads(msg["data"])
                    event_type = payload.get("event", "message")
                    event_data = json.dumps(payload.get("data", {}), ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {event_data}\n\n"

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
