from pydantic import BaseModel


class AuditQueryParams(BaseModel):
    after: str | None = None
    page_size: int = 50
    event_type: str | None = None


class AuditEventResponse(BaseModel):
    id: str
    discussion_id: str | None = None
    user_id: str | None = None
    event_type: str
    payload: dict
    created_at: str
