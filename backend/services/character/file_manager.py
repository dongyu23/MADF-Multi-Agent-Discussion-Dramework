import asyncio
import os
import shutil
from pathlib import Path

from backend.config import settings


SKILLS_ROOT = Path(os.getenv("SKILLS_ROOT", str(Path(__file__).parent.parent.parent.parent / "skills")))


class SkillFileManager:
    """管理 skill 目录的文件系统操作。

    路径映射: skills/{owner_id}/{skill-name}/SKILL.md
    """

    def _skill_dir(self, owner_id: str, skill_name: str) -> Path:
        return SKILLS_ROOT / owner_id / skill_name

    def _ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    async def create_skill_dir(self, owner_id: str, skill_name: str) -> Path:
        skill_dir = self._skill_dir(owner_id, skill_name)
        refs_dir = skill_dir / "references" / "research"
        await asyncio.to_thread(self._ensure_dir, refs_dir)
        return skill_dir

    async def write_file(self, owner_id: str, skill_name: str, rel_path: str, content: str) -> Path:
        """写入文件。rel_path 相对于 skill 根目录，如 'SKILL.md' 或 'references/research/01-writings.md'。"""
        skill_dir = self._skill_dir(owner_id, skill_name)
        full_path = skill_dir / rel_path
        full_path = full_path.resolve()
        if not str(full_path).startswith(str(skill_dir.resolve())):
            raise ValueError(f"Path traversal denied: {rel_path}")
        await asyncio.to_thread(self._ensure_dir, full_path.parent)
        await asyncio.to_thread(full_path.write_text, content, encoding="utf-8")
        return full_path

    async def read_file(self, owner_id: str, skill_name: str, rel_path: str) -> str:
        skill_dir = self._skill_dir(owner_id, skill_name)
        full_path = (skill_dir / rel_path).resolve()
        if not str(full_path).startswith(str(skill_dir.resolve())):
            raise ValueError(f"Path traversal denied: {rel_path}")
        return await asyncio.to_thread(full_path.read_text, encoding="utf-8")

    async def list_files(self, owner_id: str, skill_name: str) -> list[str]:
        skill_dir = self._skill_dir(owner_id, skill_name)
        if not skill_dir.exists():
            return []

        def _list() -> list[str]:
            files: list[str] = []
            for root, _dirs, filenames in os.walk(skill_dir):
                for f in filenames:
                    abs_path = os.path.join(root, f)
                    rel = os.path.relpath(abs_path, skill_dir)
                    files.append(rel)
            return sorted(files)

        return await asyncio.to_thread(_list)

    async def delete_skill_dir(self, owner_id: str, skill_name: str) -> None:
        skill_dir = self._skill_dir(owner_id, skill_name)
        if skill_dir.exists():
            await asyncio.to_thread(shutil.rmtree, str(skill_dir))

    async def copy_skill(self, src_owner_id: str, src_name: str, dst_owner_id: str) -> Path:
        src_dir = self._skill_dir(src_owner_id, src_name)
        dst_dir = self._skill_dir(dst_owner_id, src_name)
        if not src_dir.exists():
            raise FileNotFoundError(f"Source skill not found: {src_name}")

        def _copy() -> Path:
            shutil.copytree(str(src_dir), str(dst_dir), dirs_exist_ok=True)
            return dst_dir

        return await asyncio.to_thread(_copy)
