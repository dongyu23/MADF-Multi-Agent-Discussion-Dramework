import json as _json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)

_redis = None


async def _get_redis() -> "aioredis.Redis":
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis
        import os
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        _redis = aioredis.Redis(host=host, port=port, decode_responses=True)
    return _redis


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        discussion_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        event_type: str,
        payload: dict,
        level: str = "P2",
    ) -> AuditEvent:
        payload = {**payload, "level": level}
        event = AuditEvent(
            discussion_id=discussion_id,
            user_id=user_id,
            event_type=event_type,
            payload=payload,
            level=level,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)

        # 旁路推送：写入 Redis Pub/Sub，审计后端订阅后 SSE 推前端
        try:
            r = await _get_redis()
            await r.publish("audit:events", _json.dumps({
                "id": str(event.id),
                "event_type": event.event_type,
                "level": level,
                "discussion_id": str(event.discussion_id) if event.discussion_id else None,
                "user_id": str(event.user_id) if event.user_id else None,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }, ensure_ascii=False))
        except Exception:
            logger.warning("audit pubsub failed for event %s", event_type)
            try:
                await self.record(
                    discussion_id=None, user_id=None,
                    event_type="system.redis_pubsub_error",
                    payload={"failed_event_type": event_type},
                    level="P1",
                )
            except Exception:
                pass

        return event

    async def query(
        self,
        discussion_id: uuid.UUID,
        after: str | None = None,
        page_size: int = 50,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        stmt = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.discussion_id == discussion_id,
        ).order_by(AuditEvent.created_at.asc())

        if after:
            stmt = stmt.where(AuditEvent.created_at > datetime.fromisoformat(after))
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)

        stmt = stmt.limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def query_global(
        self,
        after: str | None = None,
        page_size: int = 50,
        event_type: str | None = None,
        user_id: uuid.UUID | None = None,
        discussion_id: uuid.UUID | None = None,
        level: str | None = None,
    ) -> tuple[list[AuditEvent], bool]:
        stmt = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None),
        ).order_by(AuditEvent.created_at.desc())

        if after:
            stmt = stmt.where(AuditEvent.created_at < datetime.fromisoformat(after))
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if user_id:
            stmt = stmt.where(AuditEvent.user_id == user_id)
        if discussion_id:
            stmt = stmt.where(AuditEvent.discussion_id == discussion_id)
        if level:
            stmt = stmt.where(AuditEvent.level == level)

        stmt = stmt.limit(page_size + 1)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > page_size
        return rows[:page_size], has_more

    async def list_event_types(self) -> list[str]:
        stmt = (
            select(AuditEvent.event_type)
            .where(AuditEvent.deleted_at.is_(None))
            .distinct()
            .order_by(AuditEvent.event_type)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
