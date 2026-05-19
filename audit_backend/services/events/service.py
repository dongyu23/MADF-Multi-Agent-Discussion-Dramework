import uuid

from audit_backend.models.audit_event import AuditEvent
from audit_backend.services.events.repository import AuditEventRepository
from audit_backend.services.events.schemas import EventQueryParams


class AuditEventService:
    def __init__(self, repository: AuditEventRepository):
        self.repo = repository

    async def query_events(
        self, params: EventQueryParams, role: str
    ) -> tuple[list[AuditEvent], bool]:
        if role == "viewer":
            if params.level and params.level == "P0":
                params.level = "P1"
            elif params.level is None:
                params.level = None

        events, has_more = await self.repo.query_events(params)

        if role == "viewer":
            events = [e for e in events if e.level != "P0"]

        return events, has_more

    async def get_event(self, event_id: uuid.UUID, role: str) -> AuditEvent | None:
        event = await self.repo.get_event(event_id)
        if event and role == "viewer" and event.level == "P0":
            return None
        return event

    async def get_context(self, discussion_id: uuid.UUID) -> list[AuditEvent]:
        return await self.repo.get_context(discussion_id)
