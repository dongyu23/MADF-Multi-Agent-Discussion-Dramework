from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from backend.core.responses import Result
from backend.deps import require_user
from backend.services.character.schemas import (
    CharacterCreateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
    FileContentRequest,
    FileListResponse,
    GalleryQuery,
    GenerateRequest
)
from backend.services.character.service import CharacterService, get_character_service

router = APIRouter(prefix="/api/v1/characters", tags=["character"])


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
    svc: CharacterService = Depends(get_character_service),
):
    return StreamingResponse(
        svc.generation_sse(skill_id),
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


@router.get("/{skill_id}")
async def get_character(
    skill_id: str,
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    character = await svc.get_character(skill_id)
    return Result.ok(character)


@router.put("/{skill_id}")
async def update_character(
    skill_id: str,
    req: CharacterUpdateRequest,
    svc: CharacterService = Depends(get_character_service),
) -> Result[CharacterResponse]:
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    character = await svc.update_character(skill_id, **updates)
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
    svc: CharacterService = Depends(get_character_service),
):
    if path:
        content = await svc.read_file(skill_id, path)
        return Result.ok(content)
    files = await svc.list_files(skill_id)
    return Result.ok(files)


@router.put("/{skill_id}/files")
async def write_file(
    skill_id: str,
    req: FileContentRequest,
    svc: CharacterService = Depends(get_character_service),
) -> Result[None]:
    await svc.write_file(skill_id, req.path, req.content or "")
    return Result.ok(None)
