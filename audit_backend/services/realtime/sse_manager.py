import asyncio
import json

import redis.asyncio as redis

from audit_backend.config import settings


class AuditSSEManager:
    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()
        self._redis: redis.Redis | None = None
        self._subscriber_task: asyncio.Task | None = None

    async def start(self):
        self._redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
        self._subscriber_task = asyncio.create_task(self._redis_subscribe())

    async def stop(self):
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.close()
        async with self._lock:
            for q in self._queues.values():
                await q.put(None)
            self._queues.clear()

    async def subscribe(self, admin_id: str) -> asyncio.Queue:
        async with self._lock:
            q: asyncio.Queue = asyncio.Queue(maxsize=256)
            self._queues[admin_id] = q
            return q

    async def unsubscribe(self, admin_id: str):
        async with self._lock:
            self._queues.pop(admin_id, None)

    async def broadcast(self, event_data: dict):
        async with self._lock:
            for q in self._queues.values():
                try:
                    q.put_nowait(event_data)
                except asyncio.QueueFull:
                    pass

    async def _redis_subscribe(self):
        if self._redis is None:
            return
        pubsub = self._redis.pubsub()
        await pubsub.subscribe("audit:events")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
        except asyncio.CancelledError:
            await pubsub.unsubscribe("audit:events")
            raise
