from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt

from backend.config import settings
from backend.core.responses import Result
from backend.deps import get_current_user, require_user
from backend.services.character.schemas import (
    CharacterCreateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
    FileContentRequest,
    GalleryQuery,
    GenerateRequest,
    RecommendationResponse,
)
from backend.services.character.service import CharacterService, get_character_service

router = APIRouter(prefix="/api/v1/characters", tags=["character"])


def _decode_query_token(token: str | None) -> str:
    if not token:
        return ""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub", "")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


@router.post("/generate")
async def generate_skill(
    req: GenerateRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.generate_skill(user_id, req.query, req.name)
    return Result.ok(character)


@router.get("/{skill_id}/generation-progress")
async def generation_progress(
    skill_id: str,
    after_seq: int = Query(default=0, ge=0),
    token: str | None = Query(default=None),
    user_id: str = Depends(get_current_user),
    svc: CharacterService = Depends(get_character_service),
):
    stream_user_id = user_id or _decode_query_token(token)
    stream = await svc.generation_sse(skill_id, stream_user_id, after_seq=after_seq)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("")
async def create_character(
    req: CharacterCreateRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.create_character(user_id, req.name, req.description, req.tags, req.is_public)
    return Result.ok(character)


@router.get("")
async def list_my_characters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result:
    result = await svc.list_my_characters(user_id, page, page_size, search)
    return Result.ok(result)


@router.get("/gallery")
async def gallery(
    after: str | None = None,
    page_size: int = Query(default=20, ge=1, le=50),
    search: str | None = None,
    tag: str | None = None,
    svc: CharacterService = Depends(get_character_service),
) -> Result:
    q = GalleryQuery(after=after, page_size=page_size, search=search, tag=tag)
    result = await svc.list_gallery(q)
    return Result.ok(result)


@router.get("/recommendations")
async def get_recommendations(
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
    exclude: str | None = None,
) -> Result[RecommendationResponse]:
    exclude_list = [n.strip() for n in exclude.split(",") if n.strip()] if exclude else None
    result = await svc.get_recommendations(user_id, exclude=exclude_list)
    return Result.ok(result)


@router.get("/{skill_id}")
async def get_character(
    skill_id: str,
    user_id: str = Depends(get_current_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.get_character(skill_id, user_id)
    return Result.ok(character)


@router.put("/{skill_id}")
async def update_character(
    skill_id: str,
    req: CharacterUpdateRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    character = await svc.update_character(skill_id, user_id, **updates)
    return Result.ok(character)


@router.delete("/{skill_id}")
async def delete_character(
    skill_id: str,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[None]:
    await svc.delete_character(skill_id, user_id)
    return Result.ok(None)


@router.post("/{skill_id}/copy")
async def copy_character(
    skill_id: str,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.copy_from_gallery(skill_id, user_id)
    return Result.ok(character)


@router.get("/{skill_id}/files")
async def list_or_read_files(
    skill_id: str,
    path: str | None = Query(default=None),
    user_id: str = Depends(get_current_user),
    svc: CharacterService = Depends(get_character_service),
):
    if path:
        content = await svc.read_file(skill_id, path, user_id)
        return Result.ok(content)
    files = await svc.list_files(skill_id, user_id)
    return Result.ok(files)


@router.put("/{skill_id}/files")
async def write_file(
    skill_id: str,
    req: FileContentRequest,
    user_id: str = Depends(require_user),
    svc: CharacterService = Depends(get_character_service),
) -> Result[None]:
    await svc.write_file(skill_id, req.path, req.content or "", user_id)
    return Result.ok(None)
