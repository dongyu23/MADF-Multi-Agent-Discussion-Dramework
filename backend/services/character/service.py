import asyncio
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import BusinessException, ErrorCode
from backend.deps import get_db
from backend.services.audit.repository import AuditRepository
from backend.services.character.file_manager import SkillFileManager
from backend.services.character.generation_service import generation_sse_stream, run_skill_generation
from backend.services.character.repository import CharacterRepository
from backend.services.character.schemas import (
    CharacterListResponse,
    CharacterResponse,
    FileListResponse,
    GalleryQuery,
)


class CharacterService:
    def __init__(self, session: AsyncSession):
        self.repo = CharacterRepository(session)
        self.fm = SkillFileManager()
        self.audit = AuditRepository(session)

    # ── CRUD ──────────────────────────────────────────────

    async def create_character(self, owner_id: str, name: str, description: str, tags: list[str], is_public: bool) -> CharacterResponse:
        uid = uuid.UUID(owner_id)
        skill_name = f"{name}-perspective" if not name.endswith("-perspective") else name
        existing = await self.repo.find_by_owner_and_name(uid, skill_name)
        if existing:
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS)
        await self.fm.create_skill_dir(owner_id, skill_name)
        await self.fm.write_file(owner_id, skill_name, "SKILL.md", f"# {name}\n\n> {description}\n")
        skill = await self.repo.create(
            owner_id=uid, name=skill_name, description=description,
            file_path=f"{owner_id}/{skill_name}", tags=tags, is_public=is_public, status="ready",
        )
        # P2: Audit manual skill creation
        await self.audit.record(None, uid, "skill.create", {
            "skill_id": str(skill.id), "skill_name": skill_name, "is_public": is_public,
        })
        return CharacterService._to_response(skill)

    async def list_my_characters(self, owner_id: str, page: int, page_size: int, search: str | None) -> CharacterListResponse:
        uid = uuid.UUID(owner_id)
        skills, total = await self.repo.list_by_owner(uid, page, page_size, search)
        return CharacterListResponse(
            items=[CharacterService._to_response(s) for s in skills],
            total=total, page=page, page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def get_character(self, skill_id: str) -> CharacterResponse:
        sid = uuid.UUID(skill_id)
        skill = await self.repo.find_by_id(sid)
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        return CharacterService._to_response(skill)

    async def update_character(self, skill_id: str, **kwargs) -> CharacterResponse:
        sid = uuid.UUID(skill_id)
        skill = await self.repo.find_by_id(sid)
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        changed = {k: v for k, v in kwargs.items() if v is not None and getattr(skill, k) != v}
        skill = await self.repo.update(skill, **kwargs)
        if changed:
            # P2: Audit skill metadata changes (especially is_public toggle)
            await self.audit.record(None, skill.owner_id, "skill.update", {
                "skill_id": str(skill.id), "skill_name": skill.name,
                "changed_fields": list(changed.keys()),
            })
        return CharacterService._to_response(skill)

    async def delete_character(self, skill_id: str, owner_id: str) -> None:
        sid = uuid.UUID(skill_id)
        skill = await self.repo.find_by_id(sid)
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        if str(skill.owner_id) != owner_id:
            raise BusinessException(ErrorCode.FORBIDDEN)
        # P1: Audit destructive deletion
        await self.audit.record(None, skill.owner_id, "skill.delete", {
            "skill_id": str(skill.id), "skill_name": skill.name,
        })
        await self.fm.delete_skill_dir(str(skill.owner_id), skill.name)
        await self.repo.soft_delete(skill)

    # ── Gallery ───────────────────────────────────────────

    async def list_gallery(self, q: GalleryQuery) -> CharacterListResponse:
        skills, has_more = await self.repo.list_public_gallery(q.after, q.page_size, q.search, q.tag)
        return CharacterListResponse(
            items=[CharacterService._to_response(s) for s in skills],
            total=-1, page=1, page_size=q.page_size, has_more=has_more,
        )

    async def copy_from_gallery(self, skill_id: str, dst_owner_id: str) -> CharacterResponse:
        sid = uuid.UUID(skill_id)
        src_skill = await self.repo.find_by_id(sid)
        if not src_skill or not src_skill.is_public:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        if str(src_skill.owner_id) == dst_owner_id:
            raise BusinessException(ErrorCode.INVALID_PARAMS, "Cannot copy your own skill")

        await self.fm.copy_skill(str(src_skill.owner_id), src_skill.name, dst_owner_id)
        new_skill = await self.repo.create(
            owner_id=uuid.UUID(dst_owner_id), name=src_skill.name,
            description=src_skill.description,
            file_path=f"{dst_owner_id}/{src_skill.name}",
            tags=src_skill.tags or [], is_public=False, status="ready",
            source_count=src_skill.source_count, model_count=src_skill.model_count,
        )
        # P1: Audit cross-user copy for data lineage
        await self.audit.record(None, new_skill.owner_id, "skill.copy", {
            "src_skill_id": str(src_skill.id), "src_owner_id": str(src_skill.owner_id),
            "dst_skill_id": str(new_skill.id),
        })
        return CharacterService._to_response(new_skill)

    # ── Files ─────────────────────────────────────────────

    async def list_files(self, skill_id: str) -> FileListResponse:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        files = await self.fm.list_files(str(skill.owner_id), skill.name)
        return FileListResponse(files=files, skill_dir=f"{skill.owner_id}/{skill.name}")

    async def read_file(self, skill_id: str, rel_path: str) -> str:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        return await self.fm.read_file(str(skill.owner_id), skill.name, rel_path)

    async def write_file(self, skill_id: str, rel_path: str, content: str) -> None:
        skill = await self.repo.find_by_id(uuid.UUID(skill_id))
        if not skill:
            raise BusinessException(ErrorCode.SKILL_NOT_FOUND)
        await self.fm.write_file(str(skill.owner_id), skill.name, rel_path, content)
        # P2: Audit file content modification
        await self.audit.record(None, skill.owner_id, "skill.file_write", {
            "skill_id": str(skill.id), "file_path": rel_path,
        })

    # ── Generation ────────────────────────────────────────

    async def generate_skill(self, owner_id: str, query: str, name: str | None) -> CharacterResponse:
        uid = uuid.UUID(owner_id)
        skill_name = name or _sanitize_name(query)
        skill_name = f"{skill_name}-perspective"

        existing = await self.repo.find_by_owner_and_name(uid, skill_name)
        if existing:
            raise BusinessException(ErrorCode.SKILL_NAME_EXISTS, f"Skill '{skill_name}' already exists")

        await self.fm.create_skill_dir(owner_id, skill_name)
        skill = await self.repo.create(
            owner_id=uid, name=skill_name,
            description=f"Generating: {query}",
            file_path=f"{owner_id}/{skill_name}", status="generating",
        )

        # P0: Audit resource-intensive generation start
        await self.audit.record(None, uid, "skill.generate", {
            "skill_id": str(skill.id), "query": query, "skill_name": skill_name,
        })

        asyncio.create_task(run_skill_generation(skill.id, owner_id, query, skill_name, self.repo, self.fm))
        return CharacterService._to_response(skill)

    def generation_sse(self, skill_id: str):
        return generation_sse_stream(skill_id)

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _to_response(skill) -> CharacterResponse:
        return CharacterResponse(
            id=str(skill.id), owner_id=str(skill.owner_id),
            name=skill.name, description=skill.description or "",
            tags=skill.tags or [], is_public=skill.is_public, status=skill.status,
            source_count=skill.source_count, model_count=skill.model_count,
            created_at=skill.created_at.isoformat(), updated_at=skill.updated_at.isoformat(),
        )


def _sanitize_name(query: str) -> str:
    name = query.strip().lower().replace(" ", "-")
    name = "".join(c for c in name if c.isalnum() or c == "-")
    return name[:40]


async def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(db)
