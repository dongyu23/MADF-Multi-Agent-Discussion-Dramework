from pydantic import BaseModel, Field


class EventQueryParams(BaseModel):
    after: str | None = None
    before: str | None = None
    page_size: int = 50
    level: str | None = None
    event_type: str | None = None
    user_id: str | None = None
    discussion_id: str | None = None
    keyword: str | None = None
    sort: str = "desc"


class EventDetailResponse(BaseModel):
    id: str
    discussion_id: str | None = None
    user_id: str | None = None
    event_type: str
    level: str | None = None
    payload: dict = Field(default_factory=dict)
    created_at: str | None = None


class EventQueryResponse(BaseModel):
    items: list[EventDetailResponse]
    has_more: bool = False


class EventContextResponse(BaseModel):
    discussion_id: str
    events: list[EventDetailResponse]
    total: int
