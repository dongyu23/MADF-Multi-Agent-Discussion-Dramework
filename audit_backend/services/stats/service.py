from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.models.audit_event import AuditEvent


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_overview(self) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total = await self.session.scalar(
            select(func.count(AuditEvent.id)).where(AuditEvent.deleted_at.is_(None))
        )

        today = await self.session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.created_at >= today_start,
            )
        )

        p0_count = await self.session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.level == "P0",
            )
        )

        type_count = await self.session.scalar(
            select(func.count(func.distinct(AuditEvent.event_type))).where(
                AuditEvent.deleted_at.is_(None)
            )
        )

        return {
            "total_events": total or 0,
            "today_events": today or 0,
            "p0_events": p0_count or 0,
            "event_type_count": type_count or 0,
        }

    async def get_trend(self, days: int = 7) -> list[dict]:
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.date_trunc("hour", AuditEvent.created_at).label("hour"),
                func.count(AuditEvent.id).label("count"),
            )
            .where(
                AuditEvent.deleted_at.is_(None),
                AuditEvent.created_at >= since,
            )
            .group_by(text("hour"))
            .order_by(text("hour"))
        )
        rows = result.all()
        return [{"hour": str(row.hour), "count": row.count} for row in rows]

    async def get_distribution(self) -> dict:
        module_query = await self.session.execute(
            select(
                func.split_part(AuditEvent.event_type, ".", 1).label("module"),
                func.count(AuditEvent.id).label("count"),
            )
            .where(AuditEvent.deleted_at.is_(None))
            .group_by(text("module"))
            .order_by(text("count DESC"))
        )
        by_module = {row.module or "other": row.count for row in module_query.all()}

        level_query = await self.session.execute(
            select(
                AuditEvent.level.label("level"),
                func.count(AuditEvent.id).label("count"),
            )
            .where(AuditEvent.deleted_at.is_(None))
            .group_by(AuditEvent.level)
            .order_by(AuditEvent.level)
        )
        by_level = {row.level or "unknown": row.count for row in level_query.all()}

        return {"by_module": by_module, "by_level": by_level}
