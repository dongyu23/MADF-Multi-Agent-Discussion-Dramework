from abc import ABC, abstractmethod


class SkillFileCache(ABC):
    """Skill 文件缓存抽象接口。

    一期默认实现：直接读文件系统。
    后续演进：Redis 缓存实现，不改业务代码。
    """

    @abstractmethod
    async def get_or_load(self, file_path: str) -> str:
        ...

    @abstractmethod
    async def invalidate(self, file_path: str) -> None:
        ...


class FilesystemSkillCache(SkillFileCache):
    """一期实现：直接读文件，不做缓存。"""

    async def get_or_load(self, file_path: str) -> str:
        import aiofiles

        async with aiofiles.open(file_path) as f:
            return await f.read()

    async def invalidate(self, file_path: str) -> None:
        pass  # 无缓存时不需要 invalidate
