from fastapi import APIRouter, Depends, Query

from backend.core.responses import Result
from backend.deps import require_user
from backend.services.discussion.schemas import (
    DiscussionCreateRequest,
    DiscussionMessageResponse,
    DiscussionResponse,
    InterveneRequest,
)
from backend.services.discussion.service import DiscussionService, get_discussion_service

router = APIRouter(prefix="/api/v1/discussions", tags=["discussion"])


@router.get("/generate-topic")
async def generate_topic(
    user_id: str = Depends(require_user),
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result[str]:
    topic = await svc.generate_topic()
    return Result.ok(topic)


@router.post("")
async def create_discussion(
    req: DiscussionCreateRequest,
    user_id: str = Depends(require_user),
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result[DiscussionResponse]:
    result = await svc.create_discussion(user_id, req)
    return Result.ok(result)


@router.get("")
async def list_discussions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(require_user),
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result:
    items, total, has_more = await svc.list_discussions(user_id, page, page_size)
    return Result.ok({"items": items, "total": total, "page": page, "page_size": page_size, "has_more": has_more})


@router.get("/{discussion_id}")
async def get_discussion(
    discussion_id: str,
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result[DiscussionResponse]:
    result = await svc.get_discussion(discussion_id)
    return Result.ok(result)


@router.get("/{discussion_id}/messages")
async def get_messages(
    discussion_id: str,
    after: str | None = None,
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result[list[DiscussionMessageResponse]]:
    msgs = await svc.get_messages(discussion_id, after)
    return Result.ok(msgs)


@router.post("/{discussion_id}/intervene")
async def intervene(
    discussion_id: str,
    req: InterveneRequest,
    user_id: str = Depends(require_user),
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result[None]:
    await svc.intervene(discussion_id, user_id, req.content)
    return Result.ok(None)


@router.delete("/{discussion_id}")
async def delete_discussion(
    discussion_id: str,
    user_id: str = Depends(require_user),
    svc: DiscussionService = Depends(get_discussion_service),
) -> Result[None]:
    await svc.delete_discussion(discussion_id, user_id)
    return Result.ok(None)
