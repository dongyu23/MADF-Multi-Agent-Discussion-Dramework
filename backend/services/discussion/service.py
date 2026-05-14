"""Discussion service — orchestrates the full lifecycle of a roundtable discussion."""

import asyncio
import json
import logging
import uuid
from pathlib import Path

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_engine.discussion.orchestrator import Orchestrator

from backend.config import settings
from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.audit.repository import AuditRepository
from backend.services.character.repository import CharacterRepository
from backend.services.discussion.repository import DiscussionRepository
from backend.services.discussion.schemas import (
    DiscussionCreateRequest,
    DiscussionMessageResponse,
    DiscussionResponse,
)

logger = logging.getLogger(__name__)

SKILLS_ROOT = Path(__file__).parent.parent.parent.parent / "skills"

_redis: redis.Redis | None = None
_active_orchestrators: dict[str, Orchestrator] = {}  # discussion_id → orch ref


async def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


class DiscussionService:
    def __init__(self, session: AsyncSession):
        self.repo = DiscussionRepository(session)
        self.char_repo = CharacterRepository(session)
        self._owner_id: uuid.UUID | None = None  # Set during create_discussion for audit

    async def create_discussion(
        self, owner_id: str, req: DiscussionCreateRequest
    ) -> DiscussionResponse:
        uid = uuid.UUID(owner_id)
        skill_ids = [uuid.UUID(sid) for sid in req.character_ids]

        # Validate all skills exist
        skill_paths: dict[str, str] = {}  # {agent_name: skill_dir_path}
        for sid in skill_ids:
            skill = await self.char_repo.find_by_id(sid)
            if not skill or skill.status != "ready":
                raise BusinessException(ErrorCode.SKILL_NOT_FOUND,
                                        f"Skill {sid} not found or not ready")
            skill_dir = SKILLS_ROOT / str(skill.owner_id) / skill.name
            skill_paths[skill.name] = str(skill_dir.resolve())

        # Create discussion
        disc = await self.repo.create_discussion(uid, req.topic, req.duration)
        await self.repo.add_agents(disc.id, skill_ids)
        await self.repo.start_discussion(disc.id)

        # P1: Audit discussion creation
        self._owner_id = uid
        audit = AuditRepository(self.repo.session)
        await audit.record(disc.id, uid, "discussion.create", {
            "topic": req.topic, "duration": req.duration,
            "character_ids": req.character_ids[:5],
        })

        # Launch orchestrator in background
        orchestrator = Orchestrator(
            discussion_id=disc.id,
            topic=req.topic,
            duration=req.duration,
            agent_skill_paths=skill_paths,
            on_event=self._make_event_handler(disc.id),
        )
        _active_orchestrators[str(disc.id)] = orchestrator
        asyncio.create_task(self._run_orchestrator(disc.id, orchestrator))

        return DiscussionService._to_response(disc)

    async def _run_orchestrator(self, disc_id: uuid.UUID, orch: Orchestrator) -> None:
        try:
            results = await orch.run()
            # Agent speak messages already written by _make_event_handler in real-time.
            # Write agent_think decisions to discussion_messages for replay/analysis.
            for msg in orch.messages:
                if msg.get("decision_data"):
                    for d in msg["decision_data"]:
                        await self.repo.add_message(
                            discussion_id=disc_id, round_number=msg["round"],
                            agent_id=None, agent_name=d.agent_name,
                            message_type="agent_think", content=d.raw_output,
                            confidence=d.confidence,
                        )
            await self.repo.end_discussion(disc_id)
            logger.info("Discussion %s completed: %d rounds", disc_id, len(results))
        except Exception as e:
            logger.exception("Discussion %s failed", disc_id)
            await self.repo.set_error(disc_id)
            # P1: Audit orchestrator crash
            audit = AuditRepository(self.repo.session)
            await audit.record(disc_id, self._owner_id, "discussion.error", {
                "error": str(e)[:500],
            })

    def _make_event_handler(self, disc_id: uuid.UUID):
        """Create async callback: orchestrator events → Redis + PG messages + Audit."""
        channel = f"discussion:{disc_id}:events"

        async def handler(event_type: str, data: dict) -> None:
            # 1. Push to Redis for SSE streaming
            r = await _get_redis()
            payload = json.dumps({"event": event_type, "data": data}, ensure_ascii=False)
            await r.publish(channel, payload)

            # 2. Persist agent_speak messages to PG
            if event_type == "agent_speak_chunk":
                await self.repo.add_message(
                    discussion_id=disc_id,
                    round_number=data.get("round", 0),
                    agent_id=None,
                    agent_name=data.get("agent_name", ""),
                    message_type="agent_speak",
                    content=data.get("content", ""),
                )

            # 3. Write audit event (with user_id when available)
            from backend.services.audit.service import AuditService  # noqa: PLC0415
            audit_svc = AuditService(self.repo.session)
            await audit_svc.record(
                event_type=event_type,
                payload=data,
                discussion_id=disc_id,
                user_id=self._owner_id,
            )

        return handler

    async def get_discussion(self, disc_id: str) -> DiscussionResponse:
        d = await self.repo.find_by_id(uuid.UUID(disc_id))
        if not d:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        return DiscussionService._to_response(d)

    async def list_discussions(
        self, owner_id: str, page: int, page_size: int
    ) -> tuple[list[DiscussionResponse], int, bool]:
        discs, total = await self.repo.list_by_owner(uuid.UUID(owner_id), page, page_size)
        items = [DiscussionService._to_response(d) for d in discs]
        return items, total, (page * page_size) < total

    async def intervene(self, disc_id: str, user_id: str, content: str) -> None:
        """Inject user intervention into the active orchestrator."""
        orch = _active_orchestrators.get(disc_id)
        if not orch:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not active")
        orch.messages.append({
            "round": orch.current_round,
            "speaker": f"user:{user_id}",
            "content": content,
        })
        # Push user_intervened SSE event
        r = await _get_redis()
        payload = json.dumps({"event": "user_intervened", "data": {
            "user_id": user_id, "content": content,
        }}, ensure_ascii=False)
        await r.publish(f"discussion:{disc_id}:events", payload)

    async def get_messages(
        self, disc_id: str, after: str | None
    ) -> list[DiscussionMessageResponse]:
        msgs = await self.repo.get_messages(uuid.UUID(disc_id), after)
        return [DiscussionService._msg_to_response(m) for m in msgs]

    @staticmethod
    def _to_response(d) -> DiscussionResponse:
        return DiscussionResponse(
            id=str(d.id),
            owner_id=str(d.owner_id),
            topic=d.topic,
            duration=d.duration,
            status=d.status,
            started_at=d.started_at.isoformat() if d.started_at else None,
            ended_at=d.ended_at.isoformat() if d.ended_at else None,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )

    @staticmethod
    def _msg_to_response(m) -> DiscussionMessageResponse:
        return DiscussionMessageResponse(
            id=str(m.id),
            discussion_id=str(m.discussion_id),
            round_number=m.round_number,
            agent_id=str(m.agent_id) if m.agent_id else None,
            agent_name=m.agent_name,
            message_type=m.message_type,
            content=m.content,
            confidence=m.confidence,
            created_at=m.created_at.isoformat(),
        )


async def get_discussion_service(db: AsyncSession = Depends(get_db)) -> DiscussionService:
    return DiscussionService(db)
