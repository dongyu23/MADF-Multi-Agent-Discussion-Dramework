import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_event import AuditEvent
from backend.models.discussion import Discussion
from backend.models.discussion_agent import DiscussionAgent
from backend.models.discussion_message import DiscussionMessage
from backend.models.skill import Skill
from backend.models.user import User


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ══════════════════════════════════════════
    # Users
    # ══════════════════════════════════════════

    async def list_users(
        self, page: int, page_size: int, search: str | None = None, sort_by: str = "created_at"
    ) -> tuple[list[User], int]:
        base = select(User)
        if search:
            base = base.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.phone.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        sort_col = getattr(User, sort_by, User.created_at)
        stmt = base.order_by(sort_col.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def find_user_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_user_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, username: str, password_hash: str, phone: str | None) -> User:
        user = User(
            id=uuid.uuid4(),
            username=username,
            password_hash=password_hash,
            phone=phone,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_character_count(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Skill.deleted_at.is_(None), Skill.owner_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_user_discussion_count(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Discussion.deleted_at.is_(None), Discussion.owner_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_user_token_usage(self, user_id: uuid.UUID) -> dict:
        stmt = (
            select(AuditEvent.event_type, func.count(AuditEvent.id))
            .where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.user_id == user_id,
                AuditEvent.event_type.in_([
                    "agent_think", "agent_speak_chunk", "host_intro", "host_summary",
                    "skill.generate", "skill.generate_complete",
                ]),
            )
            .group_by(AuditEvent.event_type)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        total = sum(r[1] for r in rows)
        by_type = {r[0]: r[1] for r in rows}
        return {"total_llm_events": total, "by_type": by_type}

    async def update_user(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def soft_delete_user(self, user_id: uuid.UUID) -> None:
        user = await self.find_user_by_id(user_id)
        if user:
            user.deleted_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def hard_delete_user(self, user_id: uuid.UUID) -> int:
        # Nullify foreign key references first
        await self.session.execute(
            text("UPDATE discussions SET owner_id = NULL WHERE owner_id = :uid"),
            {"uid": user_id},
        )
        await self.session.execute(
            text("UPDATE skills SET owner_id = NULL WHERE owner_id = :uid"),
            {"uid": user_id},
        )
        # audit_events.user_id has ON DELETE SET NULL, handled automatically
        result = await self.session.execute(
            text("DELETE FROM users WHERE id = :uid"), {"uid": user_id}
        )
        await self.session.commit()
        return result.rowcount

    async def count_total_users(self) -> int:
        stmt = select(func.count()).select_from(User)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ══════════════════════════════════════════
    # Discussions
    # ══════════════════════════════════════════

    async def list_all_discussions(
        self, page: int, page_size: int,
        status: str | None = None,
        search: str | None = None,
        owner_id: uuid.UUID | None = None,
        username: str | None = None,
    ) -> tuple[list[Discussion], int]:
        base = select(Discussion).where(Discussion.deleted_at.is_(None))
        if status:
            base = base.where(Discussion.status == status)
        if search:
            base = base.where(Discussion.topic.ilike(f"%{search}%"))
        if owner_id:
            base = base.where(Discussion.owner_id == owner_id)
        if username:
            base = base.join(User, Discussion.owner_id == User.id).where(
                User.username.ilike(f"%{username}%")
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Discussion.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_discussion_by_id(self, discussion_id: uuid.UUID) -> Discussion | None:
        stmt = select(Discussion).where(
            Discussion.deleted_at.is_(None), Discussion.id == discussion_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_discussion_messages(
        self, discussion_id: uuid.UUID, limit: int = 500
    ) -> list[DiscussionMessage]:
        stmt = (
            select(DiscussionMessage)
            .where(
                DiscussionMessage.deleted_at.is_(None),
                DiscussionMessage.discussion_id == discussion_id,
            )
            .order_by(DiscussionMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_discussion_agents(
        self, discussion_id: uuid.UUID
    ) -> list[tuple[DiscussionAgent, Skill]]:
        stmt = (
            select(DiscussionAgent, Skill)
            .join(Skill, DiscussionAgent.skill_id == Skill.id)
            .where(
                DiscussionAgent.deleted_at.is_(None),
                DiscussionAgent.discussion_id == discussion_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def get_discussion_agent_count(self, discussion_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            DiscussionAgent.deleted_at.is_(None),
            DiscussionAgent.discussion_id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_discussion_message_count(self, discussion_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            DiscussionMessage.deleted_at.is_(None),
            DiscussionMessage.discussion_id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_discussion_round_count(self, discussion_id: uuid.UUID) -> int:
        stmt = select(func.max(DiscussionMessage.round_number)).where(
            DiscussionMessage.deleted_at.is_(None),
            DiscussionMessage.discussion_id == discussion_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_discussion_token_usage(self, discussion_id: uuid.UUID) -> dict:
        # Read accumulated token totals from discussion_end event
        end_stmt = select(AuditEvent.payload).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.discussion_id == discussion_id,
            AuditEvent.event_type == "discussion_end",
        ).order_by(AuditEvent.created_at.desc()).limit(1)
        end_result = await self.session.execute(end_stmt)
        end_payload = end_result.scalar_one_or_none() or {}

        # Also count total messages
        msg_stmt = (
            select(func.count(DiscussionMessage.id))
            .where(
                DiscussionMessage.deleted_at.is_(None),
                DiscussionMessage.discussion_id == discussion_id,
            )
        )
        msg_result = await self.session.execute(msg_stmt)
        total_messages = msg_result.scalar_one()

        # Per-type counts from audit events
        type_stmt = (
            select(AuditEvent.event_type, func.count(AuditEvent.id))
            .where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.discussion_id == discussion_id,
                AuditEvent.event_type.in_([
                    "agent_think", "agent_speak_end", "host_intro", "host_summary",
                ]),
            )
            .group_by(AuditEvent.event_type)
        )
        type_result = await self.session.execute(type_stmt)
        by_type = {r[0]: {"count": r[1], "input_tokens": 0, "output_tokens": 0} for r in type_result.all()}

        return {
            "total_events": total_messages,
            "total_input_tokens": end_payload.get("input_tokens", 0) or 0,
            "total_output_tokens": end_payload.get("output_tokens", 0) or 0,
            "total_tokens": end_payload.get("total_tokens", 0) or 0,
            "llm_call_count": end_payload.get("llm_call_count", 0) or 0,
            "by_type": by_type,
        }

    async def soft_delete_discussion(self, discussion_id: uuid.UUID) -> None:
        disc = await self.get_discussion_by_id(discussion_id)
        if disc:
            disc.deleted_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def count_active_discussions(self) -> int:
        stmt = select(func.count()).where(
            Discussion.deleted_at.is_(None), Discussion.status == "running"
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_total_discussions(self) -> int:
        stmt = select(func.count()).where(Discussion.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_orphan_discussions(self) -> list[Discussion]:
        stmt = select(Discussion).where(
            Discussion.deleted_at.is_(None),
            Discussion.status.in_(["pending", "starting", "running"]),
            Discussion.created_at < (datetime.now(timezone.utc) - timedelta(hours=2)),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ══════════════════════════════════════════
    # Characters
    # ══════════════════════════════════════════

    async def list_all_characters(
        self, page: int, page_size: int,
        search: str | None = None,
        status: str | None = None,
        owner_id: uuid.UUID | None = None,
        is_public: bool | None = None,
    ) -> tuple[list[Skill], int]:
        base = select(Skill).where(Skill.deleted_at.is_(None))
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )
        if status:
            base = base.where(Skill.status == status)
        if owner_id:
            base = base.where(Skill.owner_id == owner_id)
        if is_public is not None:
            base = base.where(Skill.is_public.is_(is_public))

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Skill.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_character_by_id(self, character_id: uuid.UUID) -> Skill | None:
        stmt = select(Skill).where(Skill.deleted_at.is_(None), Skill.id == character_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owner_username(self, owner_id: uuid.UUID) -> str:
        stmt = select(User.username).where(User.deleted_at.is_(None), User.id == owner_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row or "unknown"

    async def get_character_discussion_count(self, skill_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            DiscussionAgent.deleted_at.is_(None),
            DiscussionAgent.skill_id == skill_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_character(self, skill: Skill, **kwargs) -> Skill:
        for key, value in kwargs.items():
            if value is not None and hasattr(skill, key):
                setattr(skill, key, value)
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def soft_delete_character(self, character_id: uuid.UUID) -> None:
        skill = await self.get_character_by_id(character_id)
        if skill:
            skill.deleted_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def count_total_characters(self) -> int:
        stmt = select(func.count()).where(Skill.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ══════════════════════════════════════════
    # Gallery
    # ══════════════════════════════════════════

    async def list_gallery_characters(
        self, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[Skill], int]:
        base = select(Skill).where(
            Skill.deleted_at.is_(None),
            Skill.is_public.is_(True),
        )
        if search:
            base = base.where(
                or_(Skill.name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%"))
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(Skill.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # ══════════════════════════════════════════
    # Audit
    # ══════════════════════════════════════════

    async def list_audit_events(
        self, page: int, page_size: int,
        event_type: str | None = None,
        level: str | None = None,
        user_id: uuid.UUID | None = None,
        discussion_id: uuid.UUID | None = None,
        after: str | None = None,
    ) -> tuple[list[AuditEvent], int, bool]:
        base = select(AuditEvent).where(AuditEvent.deleted_at.is_(None))

        if event_type:
            base = base.where(AuditEvent.event_type == event_type)
        if level:
            base = base.where(AuditEvent.level == level)
        if user_id:
            base = base.where(AuditEvent.user_id == user_id)
        if discussion_id:
            base = base.where(AuditEvent.discussion_id == discussion_id)

        # Cursor-based pagination: filter events created before 'after' timestamp
        if after:
            try:
                after_ts = datetime.fromisoformat(after.replace("Z", "+00:00"))
                base = base.where(AuditEvent.created_at < after_ts)
            except (ValueError, TypeError):
                pass

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(AuditEvent.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size + 1)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > page_size
        return rows[:page_size], total, has_more

    async def get_audit_event_by_id(self, event_id: uuid.UUID) -> AuditEvent | None:
        stmt = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None), AuditEvent.id == event_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_operation_audit_events(
        self, page: int, page_size: int,
        event_type: str | None = None,
        admin_id: str | None = None,
    ) -> tuple[list[AuditEvent], int, bool]:
        base = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.event_type.like("admin.%"),
        )

        if event_type:
            base = base.where(AuditEvent.event_type == event_type)
        if admin_id:
            base = base.where(AuditEvent.payload["admin_id"].as_string() == admin_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(AuditEvent.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size + 1)
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > page_size
        return rows[:page_size], total, has_more

    async def count_total_audit_events(self) -> int:
        stmt = select(func.count()).where(AuditEvent.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_p0_errors_today(self) -> int:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count()).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.level == "P0",
            AuditEvent.created_at >= today_start,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_api_calls_today(self) -> int:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count()).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.created_at >= today_start,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_total_messages(self) -> int:
        stmt = select(func.count()).where(DiscussionMessage.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ══════════════════════════════════════════
    # Stats
    # ══════════════════════════════════════════

    async def get_token_stats(self, time_range: str = "7d") -> dict:
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(time_range, 7)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Discussion tokens: SUM from discussion_end payloads (accumulated by monkey-patch)
        disc_r = await self.session.execute(
            select(func.coalesce(
                func.sum(func.cast(AuditEvent.payload["total_tokens"].as_integer(), Integer)), 0
            )).where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.created_at >= since,
                AuditEvent.event_type == "discussion_end",
            )
        )
        discussion_tokens = disc_r.scalar_one() or 0

        # Character tokens: SUM from skill.generate_complete + skill.generate_error + llm.recommendation
        char_r = await self.session.execute(
            select(func.coalesce(
                func.sum(func.cast(AuditEvent.payload["total_tokens"].as_integer(), Integer)), 0
            )).where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.created_at >= since,
                AuditEvent.event_type.in_([
                    "skill.generate_complete", "skill.generate_error", "llm.recommendation",
                ]),
            )
        )
        character_tokens = char_r.scalar_one() or 0

        # Other: llm.topic_generation + anything else with input/output tokens in payload
        other_r = await self.session.execute(
            select(func.coalesce(
                func.sum(func.cast(
                    func.coalesce(AuditEvent.payload["total_tokens"].as_integer(), 0) +
                    func.coalesce(AuditEvent.payload["input_tokens"].as_integer(), 0) +
                    func.coalesce(AuditEvent.payload["output_tokens"].as_integer(), 0),
                    Integer)), 0
            )).where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.created_at >= since,
                AuditEvent.event_type.notin_([
                    "discussion_end", "skill.generate_complete", "skill.generate_error",
                    "llm.recommendation",
                ]),
            )
        )
        other_tokens = other_r.scalar_one() or 0

        return {
            "period": time_range,
            "discussion_tokens": discussion_tokens,
            "character_tokens": character_tokens,
            "other_tokens": other_tokens,
            "total_tokens": discussion_tokens + character_tokens + other_tokens,
            "by_event_type": {},
        }

    async def get_token_trend(self, days: int = 7) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        llm_types = ["agent_think", "agent_speak_end", "agent_speak_chunk",
                      "host_intro", "host_summary", "agent_speak_start",
                      "host_intro_start", "host_summary_start",
                      "llm.recommendation", "llm.topic_generation",
                      "skill.generate", "skill.generate_complete"]

        stmt = (
            select(AuditEvent.created_at, AuditEvent.event_type, AuditEvent.payload)
            .where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.created_at >= since,
            )
            .order_by(AuditEvent.created_at)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Aggregate real tokens by date
        daily: dict[str, dict[str, int]] = {}
        for created_at, event_type, payload in rows:
            date_str = str(created_at.date())
            if date_str not in daily:
                daily[date_str] = {"llm_tokens": 0, "tavily_tokens": 0, "other_tokens": 0}

            inp = (payload or {}).get("input_tokens", 0) or 0
            out = (payload or {}).get("output_tokens", 0) or 0
            tokens = inp + out

            if event_type in llm_types:
                daily[date_str]["llm_tokens"] += tokens
            elif (event_type or "").startswith("tavily"):
                daily[date_str]["tavily_tokens"] += tokens
            else:
                daily[date_str]["other_tokens"] += tokens

        trend = [
            {"date": d, **counts}
            for d, counts in sorted(daily.items())
        ]
        return trend

    # ══════════════════════════════════════════
    # Health
    # ══════════════════════════════════════════

    async def get_health_errors(
        self, page: int, page_size: int
    ) -> tuple[list[AuditEvent], bool]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.level == "P0",
                AuditEvent.event_type.like("system.%"),
            )
            .order_by(AuditEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > page_size
        return rows[:page_size], has_more

    async def get_health_error_by_id(self, event_id: uuid.UUID) -> AuditEvent | None:
        stmt = select(AuditEvent).where(
            AuditEvent.deleted_at.is_(None),
            AuditEvent.id == event_id,
            AuditEvent.level == "P0",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ══════════════════════════════════════════
    # Admin Users (audit_admin_users table)
    # ══════════════════════════════════════════

    async def list_admin_users(self) -> list[dict]:
        stmt = text(
            "SELECT id, username, display_name, role, is_active, last_login_at, created_at "
            "FROM audit_admin_users WHERE is_active = true ORDER BY created_at"
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": str(r[0]), "username": r[1], "display_name": r[2],
                "role": r[3], "is_active": r[4],
                "last_login": r[5].isoformat() if r[5] else None,
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]

    async def find_admin_by_id(self, admin_id: uuid.UUID) -> dict | None:
        stmt = text(
            "SELECT id, username, display_name, role, is_active, last_login_at, created_at "
            "FROM audit_admin_users WHERE id = :id"
        )
        result = await self.session.execute(stmt, {"id": admin_id})
        r = result.first()
        if not r:
            return None
        return {
            "id": str(r[0]), "username": r[1], "display_name": r[2],
            "role": r[3], "is_active": r[4],
            "last_login": r[5].isoformat() if r[5] else None,
            "created_at": r[6].isoformat() if r[6] else None,
        }

    async def create_admin_user(
        self, username: str, password_hash: str, role: str, display_name: str = ""
    ) -> dict:
        new_id = uuid.uuid4()
        stmt = text(
            "INSERT INTO audit_admin_users (id, username, password_hash, display_name, role, is_active) "
            "VALUES (:id, :username, :password_hash, :display_name, :role, true) "
            "RETURNING id, username, display_name, role, is_active, created_at"
        )
        result = await self.session.execute(stmt, {
            "id": new_id, "username": username,
            "password_hash": password_hash,
            "display_name": display_name or username,
            "role": role,
        })
        await self.session.commit()
        r = result.first()
        return {
            "id": str(r[0]), "username": r[1], "display_name": r[2],
            "role": r[3], "is_active": r[4],
            "created_at": r[5].isoformat() if r[5] else None,
        }

    async def update_admin_user(
        self, admin_id: uuid.UUID,
        username: str | None = None,
        password_hash: str | None = None,
        display_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> bool:
        sets = []
        params = {"id": admin_id}
        if username is not None:
            sets.append("username = :username")
            params["username"] = username
        if password_hash is not None:
            sets.append("password_hash = :password_hash")
            params["password_hash"] = password_hash
        if display_name is not None:
            sets.append("display_name = :display_name")
            params["display_name"] = display_name
        if role is not None:
            sets.append("role = :role")
            params["role"] = role
        if is_active is not None:
            sets.append("is_active = :is_active")
            params["is_active"] = is_active
        if not sets:
            return False
        sets.append("updated_at = NOW()")
        stmt = text(f"UPDATE audit_admin_users SET {', '.join(sets)} WHERE id = :id")
        result = await self.session.execute(stmt, params)
        await self.session.commit()
        return result.rowcount > 0

    async def soft_delete_admin_user(self, admin_id: uuid.UUID) -> bool:
        stmt = text(
            "UPDATE audit_admin_users SET is_active = false, updated_at = NOW() WHERE id = :id"
        )
        result = await self.session.execute(stmt, {"id": admin_id})
        await self.session.commit()
        return result.rowcount > 0

    # ══════════════════════════════════════════
    # Retention Policy
    # ══════════════════════════════════════════

    async def get_retention_policies(self) -> list[dict]:
        stmt = text(
            "SELECT id, name, level, hot_days, warm_days, archive_enabled, "
            "archive_method, is_active, created_at, updated_at "
            "FROM audit_retention_policy ORDER BY level"
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": str(r[0]), "name": r[1], "level": r[2],
                "hot_days": r[3], "warm_days": r[4],
                "archive_enabled": r[5], "archive_method": r[6],
                "is_active": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
                "updated_at": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ]

    async def update_retention_policy(self, level: str, hot_days: int, warm_days: int) -> bool:
        stmt = text(
            "UPDATE audit_retention_policy SET hot_days = :hot_days, warm_days = :warm_days, "
            "updated_at = NOW() WHERE level = :level"
        )
        result = await self.session.execute(stmt, {
            "hot_days": hot_days, "warm_days": warm_days, "level": level,
        })
        await self.session.commit()
        return result.rowcount > 0

    # ══════════════════════════════════════════
    # Cleanup
    # ══════════════════════════════════════════

    async def cleanup_old_soft_deleted(self, retention_days: int, dry_run: bool) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=retention_days)

        if dry_run:
            count_stmt = select(func.count()).where(
                DiscussionMessage.deleted_at.isnot(None),
                DiscussionMessage.deleted_at < since,
            )
            result = await self.session.execute(count_stmt)
            messages = result.scalar_one()

            count_stmt2 = select(func.count()).where(
                AuditEvent.deleted_at.isnot(None),
                AuditEvent.deleted_at < since,
            )
            result2 = await self.session.execute(count_stmt2)
            audit = result2.scalar_one()

            return messages + audit

        result = await self.session.execute(
            text("DELETE FROM discussion_messages WHERE deleted_at IS NOT NULL AND deleted_at < :since"),
            {"since": since},
        )
        msg_count = result.rowcount

        result2 = await self.session.execute(
            text("DELETE FROM audit_events WHERE deleted_at IS NOT NULL AND deleted_at < :since"),
            {"since": since},
        )
        audit_count = result2.rowcount
        await self.session.commit()
        return msg_count + audit_count
