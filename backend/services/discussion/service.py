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
        self.audit = AuditRepository(session)
        self._owner_id: uuid.UUID | None = None  # Set during create_discussion for audit

    async def generate_topic(self) -> str:
        import os
        from langchain_openai import ChatOpenAI
        from backend.config import settings

        api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
        model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
        llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                          temperature=1.0, timeout=8)

        prompt = ("生成一个适合多智能体圆桌讨论的辩论主题。主题应具有争议性、时代感，适合不同背景的AI角色参与讨论。"
                   "只返回主题本身（30字以内），不要加引号或解释。")

        result = await llm.ainvoke(prompt)
        usage = getattr(result, 'usage_metadata', None) or {}
        topic_input = usage.get('input_tokens', 0) or 0
        topic_output = usage.get('output_tokens', 0) or 0
        topic_text = result.content.strip().strip('"').strip("'").strip("。").strip()
        await self.audit.record(None, None, "llm.topic_generation", {
            "input_tokens": topic_input,
            "output_tokens": topic_output,
            "topic": topic_text,
        }, level="P2")
        return topic_text

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
            if str(skill.owner_id) != owner_id:
                raise BusinessException(ErrorCode.FORBIDDEN,
                                        f"Skill '{skill.name}' does not belong to you")
            skill_dir = SKILLS_ROOT / str(skill.owner_id) / skill.name
            if not (skill_dir / "SKILL.md").exists():
                raise BusinessException(ErrorCode.SKILL_NOT_FOUND,
                                        f"SKILL.md missing for skill '{skill.name}'")
            skill_paths[skill.name.replace("-perspective", "")] = str(skill_dir.resolve())

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
        }, level="P1")

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

        agents = await self._get_agent_names(disc.id)
        return DiscussionService._to_response(disc, agents)

    async def _run_orchestrator(self, disc_id: uuid.UUID, orch: Orchestrator) -> None:
        """Background task: runs orchestrator with its own independent DB session."""
        from backend.services.character.generation_service import _patch_chatopenai, TokenAccumulator
        _patch_chatopenai()
        token_acc = TokenAccumulator()
        token_acc.activate()
        try:
            results = await orch.run()
            token_acc.deactivate()
            # Write accumulated token data to discussion_end audit event
            from backend.deps import async_session_factory
            async with async_session_factory() as bg_session:
                audit = AuditRepository(bg_session)
                await audit.record(disc_id, None, "discussion_end", {
                    "total_rounds": len(results),
                    "input_tokens": token_acc.input_tokens,
                    "output_tokens": token_acc.output_tokens,
                    "total_tokens": token_acc.total_tokens,
                    "llm_call_count": token_acc.llm_call_count,
                }, level="P1")
            # Persist complete messages (agent_think + agent_speak were written by event handler)
            await self._finalize_discussion(disc_id)
            logger.info("Discussion %s completed: %d rounds, %s tokens",
                         disc_id, len(results), token_acc.total_tokens)
        except Exception as e:
            token_acc.deactivate()
            logger.exception("Discussion %s failed", disc_id)
            await self._fail_discussion(disc_id, str(e))

    async def _finalize_discussion(self, disc_id: uuid.UUID) -> None:
        from backend.deps import async_session_factory
        async with async_session_factory() as bg_session:
            repo = DiscussionRepository(bg_session)
            await repo.end_discussion(disc_id)

    async def _fail_discussion(self, disc_id: uuid.UUID, error: str) -> None:
        from backend.deps import async_session_factory
        async with async_session_factory() as bg_session:
            repo = DiscussionRepository(bg_session)
            await repo.set_error(disc_id)
            audit = AuditRepository(bg_session)
            await audit.record(disc_id, self._owner_id, "discussion.error", {
                "error": error[:500],
            }, level="P1")

    def _make_event_handler(self, disc_id: uuid.UUID):
        """Create async callback: orchestrator events → Redis + PG messages."""
        channel = f"discussion:{disc_id}:events"
        owner_id = self._owner_id

        async def handler(event_type: str, data: dict) -> None:
            # 1. Push to Redis for SSE streaming (always)
            r = await _get_redis()
            payload = json.dumps({"event": event_type, "data": data}, ensure_ascii=False)
            await r.publish(channel, payload)

            # 2. Persist to PG with independent background session
            from backend.deps import async_session_factory  # noqa: PLC0415
            async with async_session_factory() as bg_session:
                repo = DiscussionRepository(bg_session)

                if event_type == "agent_speak_end":
                    await repo.add_message(
                        discussion_id=disc_id,
                        round_number=data.get("round", 0),
                        agent_id=None,
                        agent_name=data.get("agent_name", "").replace("-perspective", ""),
                        message_type="agent_speak",
                        content=data.get("content", ""),
                    )

                elif event_type == "agent_think":
                    await repo.add_message(
                        discussion_id=disc_id,
                        round_number=data.get("round", 0),
                        agent_id=None,
                        agent_name=data.get("agent_name", "").replace("-perspective", ""),
                        message_type="agent_think",
                        content=data.get("reasoning", ""),
                        confidence=data.get("confidence"),
                    )

                elif event_type == "host_intro":
                    await repo.add_message(
                        discussion_id=disc_id, round_number=0,
                        agent_id=None, agent_name="主持人",
                        message_type="host_intro",
                        content=data.get("content", ""),
                    )

                elif event_type == "host_summary":
                    await repo.add_message(
                        discussion_id=disc_id,
                        round_number=data.get("total_rounds", 0),
                        agent_id=None, agent_name="主持人总结",
                        message_type="host_summary",
                        content=data.get("content", ""),
                    )

                # 3. Business audit for LLM events (with token tracking)
                if event_type in ("discussion_end", "discussion_error",
                                  "agent_think", "agent_speak_end",
                                  "host_intro", "host_summary"):
                    audit = AuditRepository(bg_session)
                    audit_payload = {
                        k: v for k, v in data.items()
                        if k not in ("content", "reasoning")
                    }
                    audit_payload["llm_call"] = True
                    await audit.record(disc_id, owner_id, event_type, audit_payload, level="P2")

        return handler

    async def get_discussion(self, disc_id: str) -> DiscussionResponse:
        d = await self.repo.find_by_id(uuid.UUID(disc_id))
        if not d:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        agents = await self._get_agent_names(d.id)
        return DiscussionService._to_response(d, agents)

    async def list_discussions(
        self, owner_id: str, page: int, page_size: int
    ) -> tuple[list[DiscussionResponse], int, bool]:
        discs, total = await self.repo.list_by_owner(uuid.UUID(owner_id), page, page_size)
        items = []
        for d in discs:
            agents = await self._get_agent_names(d.id)
            items.append(DiscussionService._to_response(d, agents))
        return items, total, (page * page_size) < total

    async def _get_agent_names(self, disc_id: uuid.UUID) -> list[dict]:
        agents = await self.repo.get_agents(disc_id)
        result = []
        for a in agents:
            skill = await self.char_repo.find_by_id(a.skill_id)
            name = skill.name if skill else "unknown"
            result.append({"skill_id": str(a.skill_id), "name": name.replace("-perspective", "")})
        return result

    async def delete_discussion(self, disc_id: str, user_id: str) -> None:
        uid = uuid.UUID(user_id)
        d = await self.repo.find_by_id(uuid.UUID(disc_id))
        if not d:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND)
        if str(d.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN, "Cannot delete another user's discussion")

        # Stop active orchestrator if running
        orch = _active_orchestrators.pop(disc_id, None)
        if orch and orch.status == "running":
            orch.status = "error"

        await self.repo.soft_delete(uuid.UUID(disc_id))

        # P1: Audit deletion
        audit = AuditRepository(self.repo.session)
        await audit.record(uuid.UUID(disc_id), uid, "discussion.delete", {
            "topic": d.topic,
        }, level="P1")

    async def intervene(self, disc_id: str, user_id: str, content: str) -> None:
        """Inject user intervention into the active orchestrator."""
        orch = _active_orchestrators.get(disc_id)
        if not orch:
            raise BusinessException(ErrorCode.DISCUSSION_NOT_FOUND, "Discussion not active")

        # Ownership check
        disc = await self.repo.find_by_id(uuid.UUID(disc_id))
        if not disc or str(disc.owner_id) != user_id:
            raise BusinessException(ErrorCode.FORBIDDEN, "Cannot intervene in another user's discussion")

        if orch.status != "running":
            raise BusinessException(ErrorCode.DISCUSSION_ENDED, "Discussion has ended")

        # Resolve username for display
        from backend.services.user.repository import UserRepository
        user_repo = UserRepository(self.repo.session)
        user = await user_repo.find_by_id(uuid.UUID(user_id))
        username = user.username if user else user_id

        # Append to orchestrator context — human-readable speaker label
        orch.messages.append({
            "round": orch.current_round,
            "speaker": f"观众（{username}）",
            "content": content,
        })

        # Persist to PG (same session — committed atomically with audit)
        await self.repo.add_message(
            discussion_id=orch.discussion_id,
            round_number=orch.current_round,
            agent_id=None,
            agent_name=username,
            message_type="user_intervene",
            content=content,
        )
        await self.audit.record(orch.discussion_id, uuid.UUID(user_id),
                                "user_intervened", {"content": content[:200]}, level="P2")

        # Signal orchestrator to restart the current round with updated context
        orch.signal_interrupt()

        # Push SSE event via Redis
        r = await _get_redis()
        payload = json.dumps({"event": "user_intervened", "data": {
            "user_id": user_id, "username": username, "content": content,
        }}, ensure_ascii=False)
        await r.publish(f"discussion:{disc_id}:events", payload)

    async def get_messages(
        self, disc_id: str, after: str | None
    ) -> list[DiscussionMessageResponse]:
        msgs = await self.repo.get_messages(uuid.UUID(disc_id), after)
        return [DiscussionService._msg_to_response(m) for m in msgs]

    @staticmethod
    def _to_response(d, agents: list[dict] | None = None) -> DiscussionResponse:
        from backend.services.discussion.schemas import AgentInfo
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
            agents=[AgentInfo(**a) for a in (agents or [])],
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
