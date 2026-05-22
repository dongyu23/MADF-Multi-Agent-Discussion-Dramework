import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.admin.repository import AdminRepository
from backend.services.audit.repository import AuditRepository

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Admin users stored in a JSON file alongside skills data
ADMINS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "admins.json"

_start_time = time.time()


def _load_admins() -> list[dict]:
    if ADMINS_FILE.exists():
        try:
            return json.loads(ADMINS_FILE.read_text())
        except Exception:
            return _default_admins()
    return _default_admins()


def _save_admins(admins: list[dict]) -> None:
    ADMINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADMINS_FILE.write_text(json.dumps(admins, ensure_ascii=False, indent=2))


def _default_admins() -> list[dict]:
    pw = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
    return [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "username": "admin",
            "password_hash": _pwd_context.hash(pw),
            "role": "super_admin",
            "created_at": "2025-01-01T00:00:00+00:00",
        },
    ]


def _sanitize_payload(payload: dict | None) -> dict | None:
    if payload is None:
        return None
    clean = {}
    for k, v in payload.items():
        if isinstance(v, str):
            # Remove control characters that break JSON serialization
            clean[k] = ''.join(c if ord(c) >= 32 or c in '\n\r\t' else ' ' for c in v)
        elif isinstance(v, dict):
            clean[k] = _sanitize_payload(v)
        elif isinstance(v, list):
            clean[k] = [
                _sanitize_payload(i) if isinstance(i, dict) else i
                for i in v
            ]
        else:
            clean[k] = v
    return clean


class AdminService:
    def __init__(self, session: AsyncSession):
        self.repo = AdminRepository(session)
        self.audit = AuditRepository(session)

    # ══════════════════════════════════════════
    # User Management
    # ══════════════════════════════════════════

    async def list_users(
        self, page: int, page_size: int, search: str | None, sort_by: str | None,
    ) -> dict:
        users, total = await self.repo.list_users(
            page=page, page_size=page_size, search=search, sort_by=sort_by or "created_at"
        )
        items = []
        for u in users:
            char_count = await self.repo.get_user_character_count(u.id)
            disc_count = await self.repo.get_user_discussion_count(u.id)
            items.append({
                "id": str(u.id),
                "username": u.username,
                "phone": u.phone,
                "status": "disabled" if u.deleted_at else "active",
                "character_count": char_count,
                "discussion_count": disc_count,
                "registered_at": u.created_at.isoformat(),
            })
        return {
            "items": items, "total": total,
            "page": page, "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    async def get_user_detail(self, user_id: str, admin_info: dict) -> dict:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return None
        char_count = await self.repo.get_user_character_count(uid)
        disc_count = await self.repo.get_user_discussion_count(uid)
        token_usage = await self.repo.get_user_token_usage(uid)

        return {
            "id": str(user.id),
            "username": user.username,
            "phone": user.phone,
            "status": "disabled" if user.deleted_at else "active",
            "character_count": char_count,
            "discussion_count": disc_count,
            "registered_at": user.created_at.isoformat(),
            "token_usage_summary": token_usage,
            "last_active": user.updated_at.isoformat(),
        }

    async def update_user_status(
        self, user_id: str, status_val: str, admin_info: dict,
    ) -> dict:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return None

        if status_val == "disabled":
            user.deleted_at = datetime.now(timezone.utc)
        else:
            user.deleted_at = None

        await self.repo.update_user(user)

        await self.audit.record(None, uid, "admin.user_status_changed", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "target_username": user.username,
            "new_status": status_val,
        }, level="P1")

        return {"id": str(user.id), "status": status_val}

    async def change_username(
        self, user_id: str, new_username: str, admin_info: dict,
    ) -> dict:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return None

        old_username = user.username
        user = await self.repo.update_user(user, username=new_username)

        await self.audit.record(None, uid, "admin.username_changed", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "target_username": old_username,
            "old_username": old_username,
            "new_username": new_username,
        }, level="P0")

        return {"id": str(user.id), "username": user.username}

    async def reset_password(
        self, user_id: str, new_password: str, admin_info: dict,
    ) -> dict:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return None

        new_hash = _pwd_context.hash(new_password)
        user = await self.repo.update_user(user, password_hash=new_hash)

        await self.audit.record(None, uid, "admin.password_reset", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "target_username": user.username,
        }, level="P0")

        return {"id": str(user.id), "message": "Password reset successfully"}

    async def create_user(
        self, username: str, password: str, phone: str | None, admin_info: dict,
    ) -> dict:
        existing = await self.repo.find_user_by_username(username)
        if existing:
            raise ValueError("用户名已存在")

        password_hash = _pwd_context.hash(password)
        user = await self.repo.create_user(username, password_hash, phone)

        await self.audit.record(None, user.id, "admin.user_created", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "new_username": username,
            "phone": phone,
        }, level="P0")

        return {"id": str(user.id), "username": user.username, "phone": user.phone, "status": "active"}

    async def delete_user(self, user_id: str, admin_info: dict) -> bool:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return False

        # Record audit BEFORE hard delete (FK constraint needs user to exist)
        await self.audit.record(None, uid, "admin.user_deleted", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "target_username": user.username,
            "hard_delete": True,
        }, level="P0")

        deleted = await self.repo.hard_delete_user(uid)
        return bool(deleted)

    async def update_user_phone(
        self, user_id: str, phone: str, admin_info: dict,
    ) -> dict:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return None

        user = await self.repo.update_user(user, phone=phone)

        await self.audit.record(None, uid, "admin.phone_updated", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "target_username": user.username,
        }, level="P1")

        return {"id": str(user.id), "phone": user.phone}

    async def get_user_token_usage(self, user_id: str) -> dict:
        uid = uuid.UUID(user_id)
        user = await self.repo.find_user_by_id(uid)
        if not user:
            return None
        usage = await self.repo.get_user_token_usage(uid)
        return {"user_id": str(uid), "username": user.username, **usage}

    # ══════════════════════════════════════════
    # Discussion Monitoring
    # ══════════════════════════════════════════

    async def list_discussions(
        self, page: int, page_size: int,
        status: str | None, search: str | None, owner_id: str | None,
        username: str | None = None,
    ) -> dict:
        uid = uuid.UUID(owner_id) if owner_id else None
        discs, total = await self.repo.list_all_discussions(
            page=page, page_size=page_size, status=status, search=search, owner_id=uid,
            username=username,
        )
        items = []
        for d in discs:
            agent_count = await self.repo.get_discussion_agent_count(d.id)
            msg_count = await self.repo.get_discussion_message_count(d.id)
            round_count = await self.repo.get_discussion_round_count(d.id)
            token_usage = await self.repo.get_discussion_token_usage(d.id)
            owner_username = await self.repo.get_owner_username(d.owner_id)
            items.append({
                "id": str(d.id),
                "owner_id": str(d.owner_id),
                "owner_username": owner_username,
                "topic": d.topic,
                "status": d.status,
                "agent_count": agent_count,
                "message_count": msg_count,
                "round_count": round_count,
                "token_usage": (token_usage.get("total_tokens") or token_usage.get("total_events") or 0) if token_usage else 0,
                "duration": d.duration,
                "created_at": d.created_at.isoformat(),
                "started_at": d.started_at.isoformat() if d.started_at else None,
                "ended_at": d.ended_at.isoformat() if d.ended_at else None,
            })
        return {
            "items": items, "total": total,
            "page": page, "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    async def get_discussion_detail(self, discussion_id: str) -> dict | None:
        did = uuid.UUID(discussion_id)
        disc = await self.repo.get_discussion_by_id(did)
        if not disc:
            return None

        agent_count = await self.repo.get_discussion_agent_count(did)
        msg_count = await self.repo.get_discussion_message_count(did)
        round_count = await self.repo.get_discussion_round_count(did)
        token_usage = await self.repo.get_discussion_token_usage(did)
        owner_username = await self.repo.get_owner_username(disc.owner_id)
        agents = await self.repo.get_discussion_agents(did)
        messages = await self.repo.get_discussion_messages(did)

        agent_infos = [
            {"id": str(da.id), "skill_id": str(skill.id), "skill_name": skill.name}
            for da, skill in agents
        ]
        msg_infos = [
            {
                "id": str(m.id), "round_number": m.round_number,
                "agent_name": m.agent_name, "message_type": m.message_type,
                "content": m.content[:500], "confidence": m.confidence,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

        return {
            "id": str(disc.id),
            "owner_id": str(disc.owner_id),
            "owner_username": owner_username,
            "topic": disc.topic,
            "status": disc.status,
            "agent_count": agent_count,
            "message_count": msg_count,
            "round_count": round_count,
            "token_usage": (token_usage.get("total_tokens") or token_usage.get("total_events") or 0) if token_usage else 0,
            "duration": disc.duration,
            "created_at": disc.created_at.isoformat(),
            "started_at": disc.started_at.isoformat() if disc.started_at else None,
            "ended_at": disc.ended_at.isoformat() if disc.ended_at else None,
            "agents": agent_infos,
            "messages": msg_infos,
        }

    async def delete_discussion(self, discussion_id: str, admin_info: dict) -> bool:
        did = uuid.UUID(discussion_id)
        disc = await self.repo.get_discussion_by_id(did)
        if not disc:
            return False

        await self.repo.soft_delete_discussion(did)
        await self.audit.record(did, None, "admin.discussion_deleted", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "topic": disc.topic,
        }, level="P1")
        return True

    async def get_discussion_token_usage(self, discussion_id: str) -> dict | None:
        did = uuid.UUID(discussion_id)
        disc = await self.repo.get_discussion_by_id(did)
        if not disc:
            return None
        usage = await self.repo.get_discussion_token_usage(did)
        return {"discussion_id": str(did), "topic": disc.topic, **usage}

    # ══════════════════════════════════════════
    # Character Management
    # ══════════════════════════════════════════

    async def list_characters(
        self, page: int, page_size: int,
        search: str | None, status: str | None,
        owner_id: str | None, is_public: bool | None,
    ) -> dict:
        uid = uuid.UUID(owner_id) if owner_id else None
        skills, total = await self.repo.list_all_characters(
            page=page, page_size=page_size,
            search=search, status=status, owner_id=uid, is_public=is_public,
        )
        items = [
            {
                "id": str(s.id), "owner_id": str(s.owner_id),
                "name": s.name, "description": s.description[:200],
                "tags": s.tags, "is_public": s.is_public,
                "status": s.status,
                "source_count": s.source_count,
                "model_count": s.model_count,
                "created_at": s.created_at.isoformat(),
            }
            for s in skills
        ]
        return {
            "items": items, "total": total,
            "page": page, "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    async def get_character_detail(self, character_id: str) -> dict | None:
        cid = uuid.UUID(character_id)
        skill = await self.repo.get_character_by_id(cid)
        if not skill:
            return None

        owner_username = await self.repo.get_owner_username(skill.owner_id)
        disc_count = await self.repo.get_character_discussion_count(cid)

        return {
            "id": str(skill.id),
            "owner_id": str(skill.owner_id),
            "owner_username": owner_username,
            "name": skill.name,
            "description": skill.description[:200],
            "tags": skill.tags,
            "is_public": skill.is_public,
            "status": skill.status,
            "source_count": skill.source_count,
            "model_count": skill.model_count,
            "discussion_count": disc_count,
            "file_path": skill.file_path,
            "created_at": skill.created_at.isoformat(),
        }

    async def update_character_visibility(
        self, character_id: str, is_public: bool, admin_info: dict,
    ) -> dict | None:
        cid = uuid.UUID(character_id)
        skill = await self.repo.get_character_by_id(cid)
        if not skill:
            return None

        skill = await self.repo.update_character(skill, is_public=is_public)
        await self.audit.record(None, skill.owner_id, "admin.character_visibility_changed", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "character_name": skill.name,
            "new_visibility": is_public,
        }, level="P1")

        return {"id": str(skill.id), "name": skill.name, "is_public": skill.is_public}

    async def delete_character(self, character_id: str, admin_info: dict) -> bool:
        cid = uuid.UUID(character_id)
        skill = await self.repo.get_character_by_id(cid)
        if not skill:
            return False

        await self.repo.soft_delete_character(cid)
        await self.audit.record(None, skill.owner_id, "admin.character_deleted", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "character_name": skill.name,
        }, level="P1")
        return True

    # ══════════════════════════════════════════
    # Gallery Management
    # ══════════════════════════════════════════

    async def list_gallery(
        self, page: int, page_size: int, search: str | None,
    ) -> dict:
        skills, total = await self.repo.list_gallery_characters(
            page=page, page_size=page_size, search=search,
        )
        items = []
        for s in skills:
            owner = await self.repo.get_owner_username(s.owner_id)
            items.append({
                "id": str(s.id),
                "owner_id": str(s.owner_id),
                "owner_username": owner,
                "name": s.name,
                "description": s.description[:200],
                "tags": s.tags,
                "created_at": s.created_at.isoformat(),
            })
        return {
            "items": items, "total": total,
            "page": page, "page_size": page_size,
            "has_more": (page * page_size) < total,
        }

    async def unlist_gallery(self, gallery_id: str, admin_info: dict) -> bool:
        cid = uuid.UUID(gallery_id)
        skill = await self.repo.get_character_by_id(cid)
        if not skill:
            return False

        skill = await self.repo.update_character(skill, is_public=False)
        await self.audit.record(None, skill.owner_id, "admin.gallery_unlisted", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "character_name": skill.name,
        }, level="P1")
        return True

    # ══════════════════════════════════════════
    # Audit & Trace
    # ══════════════════════════════════════════

    async def list_audit_events(
        self, page: int, page_size: int,
        event_type: str | None, level: str | None,
        user_id: str | None, discussion_id: str | None,
        after: str | None = None,
    ) -> dict:
        uid = uuid.UUID(user_id) if user_id else None
        did = uuid.UUID(discussion_id) if discussion_id else None
        events, total, has_more = await self.repo.list_audit_events(
            page=page, page_size=page_size,
            event_type=event_type, level=level,
            user_id=uid, discussion_id=did,
            after=after,
        )
        items = [
            {
                "id": str(e.id), "discussion_id": str(e.discussion_id) if e.discussion_id else None,
                "user_id": str(e.user_id) if e.user_id else None,
                "event_type": e.event_type, "level": e.level,
                "payload": _sanitize_payload(e.payload),
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size, "has_more": has_more}

    async def get_audit_event(self, event_id: str) -> dict | None:
        eid = uuid.UUID(event_id)
        event = await self.repo.get_audit_event_by_id(eid)
        if not event:
            return None
        return {
            "id": str(event.id),
            "discussion_id": str(event.discussion_id) if event.discussion_id else None,
            "user_id": str(event.user_id) if event.user_id else None,
            "event_type": event.event_type,
            "level": event.level,
            "payload": _sanitize_payload(event.payload),
            "created_at": event.created_at.isoformat(),
        }

    async def list_operations(
        self, page: int, page_size: int,
        event_type: str | None, admin_id: str | None,
    ) -> dict:
        events, total, has_more = await self.repo.list_operation_audit_events(
            page=page, page_size=page_size,
            event_type=event_type, admin_id=admin_id,
        )
        items = []
        for e in events:
            payload = _sanitize_payload(e.payload) or {}
            items.append({
                "id": str(e.id),
                "event_type": e.event_type,
                "level": e.level,
                "admin_id": payload.get("admin_id"),
                "admin_username": payload.get("admin_username"),
                "payload": payload,
                "created_at": e.created_at.isoformat(),
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size, "has_more": has_more}

    async def get_operation(self, operation_id: str) -> dict | None:
        return await self.get_audit_event(operation_id)

    # ══════════════════════════════════════════
    # System Health
    # ══════════════════════════════════════════

    async def get_health_overview(self) -> dict:
        import asyncio

        import httpx
        from sqlalchemy import text

        from backend.config import settings

        result = {
            "app": settings.app_name,
            "version": "0.1.0",
            "uptime_seconds": round(time.time() - _start_time, 1),
            "components": {},
        }

        # DB
        db_t0 = time.monotonic()
        try:
            async with self.repo.session.bind.connect() as conn:
                await conn.execute(text("SELECT 1"))
            result["components"]["database"] = {
                "status": "healthy",
                "latency_ms": round((time.monotonic() - db_t0) * 1000, 1),
            }
        except Exception as e:
            result["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)[:200],
            }

        # Redis
        redis_t0 = time.monotonic()
        try:
            import redis.asyncio as aioredis
            r = aioredis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
            )
            await asyncio.wait_for(r.ping(), timeout=3)
            await r.close()
            result["components"]["redis"] = {
                "status": "healthy",
                "latency_ms": round((time.monotonic() - redis_t0) * 1000, 1),
            }
        except Exception as e:
            result["components"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)[:200],
            }

        # LLM API
        llm_t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{settings.llm_api_base}/models",
                    headers={"Authorization": f"Bearer {settings.llm_api_key or ''}"},
                )
            result["components"]["llm_api"] = {
                "status": "healthy" if resp.status_code < 500 else "degraded",
                "latency_ms": round((time.monotonic() - llm_t0) * 1000, 1),
            }
        except Exception as e:
            result["components"]["llm_api"] = {
                "status": "unhealthy",
                "error": str(e)[:200],
            }

        return result

    async def get_health_errors(
        self, page: int, page_size: int,
    ) -> dict:
        events, has_more = await self.repo.get_health_errors(page=page, page_size=page_size)
        items = [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "level": e.level,
                "message": e.payload.get("exception_message", e.event_type),
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
        return {"items": items, "page": page, "page_size": page_size, "has_more": has_more}

    async def get_health_error(self, error_id: str) -> dict | None:
        eid = uuid.UUID(error_id)
        event = await self.repo.get_health_error_by_id(eid)
        if not event:
            return None
        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "level": event.level,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }

    async def get_health_load(self) -> dict:
        cpu_percent = 0.0
        mem_percent = 0.0
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem_percent = psutil.virtual_memory().percent
            thread_count = psutil.Process().num_threads()
        except ImportError:
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                cpu_percent = 0.0
                mem_percent = usage.ru_maxrss / (1024 * 1024)
                thread_count = 1
            except Exception:
                cpu_percent = 0.0
                mem_percent = 0.0
                thread_count = 1

        from backend.deps import async_engine
        pool = async_engine.pool
        db_pool_size = pool.size() if pool else 0
        db_checked_out = pool.checkedout() if hasattr(pool, 'checkedout') and pool else 0

        active_discussions = await self.repo.count_active_discussions()

        sse_connections = 0
        try:
            from backend.services.realtime.sse_manager import SSEManager
            sse_connections = len(SSEManager._connections) if hasattr(SSEManager, '_connections') else 0
        except Exception:
            pass

        return {
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(mem_percent, 1),
            "db_pool_size": db_pool_size,
            "db_pool_checked_out": db_checked_out,
            "active_discussions": active_discussions,
            "sse_connections": sse_connections,
            "thread_count": thread_count,
        }

    async def get_orphan_discussions(self) -> list[dict]:
        discs = await self.repo.get_orphan_discussions()
        return [
            {
                "discussion_id": str(d.id),
                "topic": d.topic,
                "owner_id": str(d.owner_id),
                "status": d.status,
                "created_at": d.created_at.isoformat(),
            }
            for d in discs
        ]

    # ══════════════════════════════════════════
    # Stats
    # ══════════════════════════════════════════

    async def get_stats_overview(self) -> dict:
        total_users = await self.repo.count_total_users()
        total_characters = await self.repo.count_total_characters()
        total_discussions = await self.repo.count_total_discussions()
        active_discussions = await self.repo.count_active_discussions()
        total_messages = await self.repo.count_total_messages()
        total_audit = await self.repo.count_total_audit_events()

        # P0 errors today
        p0_today = await self.repo.count_p0_errors_today()

        # API calls today (all audit events today)
        api_today = await self.repo.count_api_calls_today()

        # Online users: active in last 5 minutes (approximated via updated_at on User)
        from sqlalchemy import func, select

        from backend.models.user import User
        since = datetime.now(timezone.utc) - timedelta(minutes=5)
        stmt = select(func.count()).where(
            User.deleted_at.is_(None),
            User.updated_at >= since,
        )
        result = await self.repo.session.execute(stmt)
        online = result.scalar_one()

        return {
            "total_users": total_users,
            "total_characters": total_characters,
            "total_discussions": total_discussions,
            "active_discussions": active_discussions,
            "online_users": online,
            "total_messages": total_messages,
            "total_audit_events": total_audit,
            "p0_errors_today": p0_today,
            "api_calls_today": api_today,
        }

    async def get_token_stats(self, time_range: str) -> dict:
        data = await self.repo.get_token_stats(time_range)
        return {"period": time_range, **data}

    async def get_token_trend(self, days: int) -> list[dict]:
        return await self.repo.get_token_trend(days)

    # ══════════════════════════════════════════
    # Admin Management
    # ══════════════════════════════════════════

    async def list_admins(self) -> list[dict]:
        return await self.repo.list_admin_users()

    async def create_admin(self, username: str, password: str, display_name: str | None, role: str, admin_info: dict) -> dict:
        password_hash = _pwd_context.hash(password)
        admin = await self.repo.create_admin_user(username, password_hash, role, display_name or "")

        await self.audit.record(None, None, "admin.admin_created", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "new_admin_username": username,
            "new_admin_role": role,
        }, level="P0")

        return admin

    async def update_admin(self, admin_id: str, username: str | None, password: str | None, display_name: str | None, role: str | None, is_active: bool | None, admin_info: dict) -> dict | None:
        uid = uuid.UUID(admin_id)
        existing = await self.repo.find_admin_by_id(uid)
        if not existing:
            return None

        password_hash = _pwd_context.hash(password) if password else None
        ok = await self.repo.update_admin_user(
            uid, username=username, password_hash=password_hash,
            display_name=display_name, role=role, is_active=is_active,
        )
        if not ok:
            return None

        changed = [k for k, v in {"username": username, "password": password is not None, "display_name": display_name, "role": role, "is_active": is_active}.items() if v is not None]
        await self.audit.record(None, None, "admin.admin_updated", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "target_admin": existing["username"],
            "changed_fields": changed,
        }, level="P0")

        updated = await self.repo.find_admin_by_id(uid)
        return updated

    async def delete_admin(self, admin_id: str, admin_info: dict) -> bool:
        uid = uuid.UUID(admin_id)
        existing = await self.repo.find_admin_by_id(uid)
        if not existing:
            return False
        ok = await self.repo.soft_delete_admin_user(uid)
        if not ok:
            return False

        await self.audit.record(None, None, "admin.admin_deleted", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "deleted_admin": existing["username"],
        }, level="P0")
        return True

    # ══════════════════════════════════════════
    # Settings
    # ══════════════════════════════════════════

    async def get_settings(self) -> dict:
        from backend.config import settings
        retention_policies = await self.repo.get_retention_policies()
        return {
            "app_name": settings.app_name,
            "debug": settings.debug,
            "cors_origins": settings.cors_origins,
            "jwt_expire_minutes": settings.jwt_expire_minutes,
            "llm_api_base": settings.llm_api_base,
            "llm_model": settings.llm_model,
            "db_host": settings.db_host,
            "db_port": settings.db_port,
            "db_name": settings.db_name,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "max_discussion_duration": int(os.getenv("MAX_DISCUSSION_DURATION", "3600")),
            "max_agents_per_discussion": int(os.getenv("MAX_AGENTS_PER_DISCUSSION", "8")),
            "retention_days": int(os.getenv("RETENTION_DAYS", "90")),
            "registration_open": os.getenv("REGISTRATION_OPEN", "true").lower() == "true",
            "retention_policies": retention_policies,
        }

    async def update_settings(self, req: dict, admin_info: dict) -> dict:
        await self.audit.record(None, None, "admin.settings_updated", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "changed_fields": list(req.keys()),
        }, level="P0")
        return {"message": "Settings update acknowledged. Restart may be required for some changes.", "changed": list(req.keys())}

    async def restart_service(self) -> dict:
        docker_available = os.path.exists("/var/run/docker.sock")
        if docker_available:
            return {"message": "Docker socket detected. Send SIGTERM to restart via Docker policy.", "docker_available": True}
        return {"message": "Docker socket not available. Manual restart required.", "docker_available": False}

    async def update_retention(self, retention_days: int, dry_run: bool, admin_info: dict) -> dict:
        # Update per-level retention policies in DB
        updated = []
        levels = [("P0", retention_days, retention_days * 4),
                   ("P1", max(retention_days // 2, 30), retention_days * 2),
                   ("P2", max(retention_days // 3, 14), retention_days)]
        for level, hot_days, warm_days in levels:
            ok = await self.repo.update_retention_policy(level, hot_days, warm_days)
            if ok:
                updated.append({"level": level, "hot_days": hot_days, "warm_days": warm_days})

        # Also clean up old soft-deleted records
        deleted = await self.repo.cleanup_old_soft_deleted(retention_days, dry_run)

        await self.audit.record(None, None, "admin.retention_applied", {
            "admin_id": admin_info["admin_id"],
            "admin_username": admin_info["admin_username"],
            "retention_days": retention_days,
            "dry_run": dry_run,
            "updated_policies": updated,
            "deleted_count": deleted if not dry_run else 0,
            "would_delete": deleted if dry_run else 0,
        }, level="P1")

        if dry_run:
            return {"dry_run": True, "retention_days": retention_days, "would_delete": deleted, "updated_policies": updated}
        return {"retention_days": retention_days, "deleted_count": deleted, "updated_policies": updated}
