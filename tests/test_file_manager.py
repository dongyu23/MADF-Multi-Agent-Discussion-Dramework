"""SkillFileManager unit tests — uses temp dir, no DB needed."""
import pytest
import tempfile, os
from pathlib import Path

from backend.services.character.file_manager import SkillFileManager


@pytest.fixture
def fm(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr("backend.services.character.file_manager.SKILLS_ROOT", Path(tmp))
    yield SkillFileManager()
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestSkillFileManager:
    @pytest.mark.asyncio
    async def test_create_skill_dir(self, fm):
        d = await fm.create_skill_dir("owner1", "test-skill")
        assert d.exists()
        refs = d / "references" / "research"
        assert refs.exists()

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        await fm.write_file("owner1", "test-skill", "SKILL.md", "# Hello\n\nWorld")
        content = await fm.read_file("owner1", "test-skill", "SKILL.md")
        assert content == "# Hello\n\nWorld"

    @pytest.mark.asyncio
    async def test_write_nested_file(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        await fm.write_file("owner1", "test-skill", "references/research/01.md", "content")
        content = await fm.read_file("owner1", "test-skill", "references/research/01.md")
        assert content == "content"

    @pytest.mark.asyncio
    async def test_list_files(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        await fm.write_file("owner1", "test-skill", "SKILL.md", "a")
        await fm.write_file("owner1", "test-skill", "references/research/01.md", "b")
        await fm.write_file("owner1", "test-skill", "references/research/02.md", "c")
        files = await fm.list_files("owner1", "test-skill")
        assert "SKILL.md" in files
        assert "references/research/01.md" in files
        assert "references/research/02.md" in files

    @pytest.mark.asyncio
    async def test_list_empty_dir(self, fm):
        await fm.create_skill_dir("owner1", "empty-skill")
        files = await fm.list_files("owner1", "empty-skill")
        assert files == []

    @pytest.mark.asyncio
    async def test_list_nonexistent_dir(self, fm):
        files = await fm.list_files("owner1", "nonexistent")
        assert files == []

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        with pytest.raises(ValueError, match="Path traversal"):
            await fm.write_file("owner1", "test-skill", "../../../etc/passwd", "evil")

    @pytest.mark.asyncio
    async def test_read_path_traversal_blocked(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        with pytest.raises(ValueError, match="Path traversal"):
            await fm.read_file("owner1", "test-skill", "../../../etc/passwd")

    @pytest.mark.asyncio
    async def test_delete_skill_dir(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        await fm.write_file("owner1", "test-skill", "SKILL.md", "content")
        await fm.delete_skill_dir("owner1", "test-skill")
        import os
        assert not (fm._skill_dir("owner1", "test-skill")).exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self, fm):
        await fm.delete_skill_dir("owner1", "nonexistent")

    @pytest.mark.asyncio
    async def test_copy_skill(self, fm):
        await fm.create_skill_dir("owner1", "test-skill")
        await fm.write_file("owner1", "test-skill", "SKILL.md", "original")
        dst = await fm.copy_skill("owner1", "test-skill", "owner2")
        assert dst.exists()
        content = await fm.read_file("owner2", "test-skill", "SKILL.md")
        assert content == "original"

    @pytest.mark.asyncio
    async def test_copy_nonexistent_source(self, fm):
        with pytest.raises(FileNotFoundError):
            await fm.copy_skill("owner1", "nonexistent", "owner2")
