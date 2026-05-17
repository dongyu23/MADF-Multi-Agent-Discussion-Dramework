import asyncio
import json
import os
import uuid
from pathlib import Path

from fastapi import Depends
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
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
    RecommendationItem,
    RecommendationResponse,
)


SKILLS_ROOT = Path(__file__).parent.parent.parent.parent / "skills"

# ── Curated recommendation pool ─────────────────────────
_RECOMMENDATION_POOL: list[dict] = [
    {"name": "史蒂夫·乔布斯", "description": "Apple 联合创始人，产品设计与演讲大师", "query": "史蒂夫·乔布斯 Apple 联合创始人"},
    {"name": "埃隆·马斯克", "description": "Tesla/SpaceX CEO，第一性原理思考者", "query": "埃隆·马斯克 Tesla SpaceX 创始人"},
    {"name": "艾伦·图灵", "description": "计算机科学之父，密码破译天才", "query": "艾伦·图灵 计算机科学之父"},
    {"name": "阿尔伯特·爱因斯坦", "description": "理论物理学家，相对论创立者", "query": "阿尔伯特·爱因斯坦 物理学家 相对论"},
    {"name": "理查德·费曼", "description": "物理学家，费曼学习法倡导者", "query": "理查德·费曼 物理学家 费曼学习法"},
    {"name": "玛丽·居里", "description": "放射性研究先驱，两次诺奖得主", "query": "玛丽·居里 物理学家 放射性研究"},
    {"name": "查尔斯·达尔文", "description": "进化论奠基人，博物学家", "query": "查尔斯·达尔文 进化论 物种起源"},
    {"name": "史蒂芬·霍金", "description": "理论物理学家，时间简史作者", "query": "史蒂芬·霍金 物理学家 时间简史"},
    {"name": "弗里德里希·尼采", "description": "德国哲学家，超人哲学", "query": "弗里德里希·尼采 德国哲学家"},
    {"name": "苏格拉底", "description": "古希腊哲学家，诘问法开创者", "query": "苏格拉底 古希腊哲学家"},
    {"name": "孔子", "description": "中国思想家，儒家学派创始人", "query": "孔子 儒家 中国思想家"},
    {"name": "老子", "description": "道家创始人，道德经作者", "query": "老子 道家 道德经"},
    {"name": "孙子", "description": "兵法大师，孙子兵法作者", "query": "孙子 兵法 孙子兵法"},
    {"name": "柏拉图", "description": "古希腊哲学家，理想国作者", "query": "柏拉图 古希腊哲学家 理想国"},
    {"name": "卡尔·马克思", "description": "马克思主义创始人，资本论作者", "query": "卡尔·马克思 资本论 马克思主义"},
    {"name": "亚当·斯密", "description": "经济学之父，国富论作者", "query": "亚当·斯密 经济学 国富论"},
    {"name": "文森特·梵高", "description": "后印象派画家，表现主义先驱", "query": "文森特·梵高 后印象派画家"},
    {"name": "列奥纳多·达·芬奇", "description": "文艺复兴全才，画家与发明家", "query": "列奥纳多·达·芬奇 文艺复兴 蒙娜丽莎"},
    {"name": "威廉·莎士比亚", "description": "英国剧作家，哈姆雷特作者", "query": "威廉·莎士比亚 英国剧作家"},
    {"name": "弗兰兹·卡夫卡", "description": "现代主义文学先驱，变形记作者", "query": "弗兰兹·卡夫卡 变形记 现代主义文学"},
    {"name": "鲁迅", "description": "中国文学家，思想启蒙者", "query": "鲁迅 中国文学家 狂人日记"},
    {"name": "欧内斯特·海明威", "description": "美国作家，冰山理论倡导者", "query": "欧内斯特·海明威 美国作家 老人与海"},
    {"name": "拿破仑·波拿巴", "description": "法国军事家，法兰西第一帝国皇帝", "query": "拿破仑·波拿巴 法国军事家"},
    {"name": "温斯顿·丘吉尔", "description": "英国首相，二战领袖", "query": "温斯顿·丘吉尔 英国首相 二战"},
    {"name": "马丁·路德·金", "description": "民权运动领袖，我有一个梦想", "query": "马丁·路德·金 民权运动 我有一个梦想"},
    {"name": "圣雄甘地", "description": "印度独立运动领袖，非暴力哲学", "query": "圣雄甘地 印度 非暴力不合作"},
    {"name": "黄仁勋", "description": "NVIDIA CEO，AI 计算革命推动者", "query": "黄仁勋 NVIDIA CEO GPU"},
    {"name": "沃伦·巴菲特", "description": "价值投资大师，伯克希尔 CEO", "query": "沃伦·巴菲特 价值投资 伯克希尔"},
    {"name": "彼得·德鲁克", "description": "现代管理学之父", "query": "彼得·德鲁克 现代管理学"},
    {"name": "西格蒙德·弗洛伊德", "description": "精神分析学创始人", "query": "西格蒙德·弗洛伊德 精神分析学"},
    {"name": "卡尔·荣格", "description": "分析心理学创始人，集体无意识理论", "query": "卡尔·荣格 分析心理学 集体无意识"},
    {"name": "路德维希·维特根斯坦", "description": "语言哲学大师，逻辑哲学论作者", "query": "路德维希·维特根斯坦 语言哲学"},
    {"name": "李小龙", "description": "武术家，截拳道创始人", "query": "李小龙 武术 截拳道 哲学家"},
    {"name": "宫崎骏", "description": "日本动画大师，吉卜力创始人", "query": "宫崎骏 吉卜力 动画导演"},
    {"name": "贝多芬", "description": "德国作曲家，古典音乐巨匠", "query": "贝多芬 德国作曲家 命运交响曲"},
    {"name": "莫扎特", "description": "奥地利作曲家，音乐神童", "query": "莫扎特 奥地利作曲家 古典音乐"},
    {"name": "艾萨克·牛顿", "description": "物理学家，万有引力发现者", "query": "艾萨克·牛顿 物理学家 万有引力"},
    {"name": "尼古拉·特斯拉", "description": "发明家，交流电系统设计者", "query": "尼古拉·特斯拉 发明家 交流电"},
    {"name": "本杰明·富兰克林", "description": "美国开国元勋，科学家与外交家", "query": "本杰明·富兰克林 美国 科学家 外交家"},
    {"name": "比尔·盖茨", "description": "微软联合创始人，慈善家", "query": "比尔·盖茨 微软 创始人"},
    {"name": "张一鸣", "description": "字节跳动创始人，算法推荐先驱", "query": "张一鸣 字节跳动 抖音 创始人"},
    {"name": "任正非", "description": "华为创始人，中国科技企业家", "query": "任正非 华为 创始人"},
    {"name": "雷军", "description": "小米创始人，中国互联网先行者", "query": "雷军 小米 创始人"},
    {"name": "马化腾", "description": "腾讯创始人，社交网络先驱", "query": "马化腾 腾讯 创始人"},
    {"name": "查理·芒格", "description": "投资家，多元思维模型倡导者", "query": "查理·芒格 投资 多元思维模型"},
    {"name": "奥普拉·温弗瑞", "description": "脱口秀女王，媒体企业家", "query": "奥普拉·温弗瑞 脱口秀 媒体"},
    {"name": "JK·罗琳", "description": "哈利波特作者，畅销书作家", "query": "JK·罗琳 哈利波特 作家"},
    {"name": "可可·香奈儿", "description": "时尚设计师，香奈儿品牌创始人", "query": "可可·香奈儿 时尚设计师"},
]


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

    # ── Recommendations ──────────────────────────────────

    async def get_recommendations(self, owner_id: str, exclude: list[str] | None = None) -> RecommendationResponse:
        uid = uuid.UUID(owner_id)
        existing_names: set[str] = set()
        if exclude:
            existing_names.update(_sanitize_name(n) for n in exclude)
        my_skills, _ = await self.repo.list_by_owner(uid, 1, 100)
        for s in my_skills:
            existing_names.add(s.name.replace("-perspective", ""))
        gallery_skills, _ = await self.repo.list_public_gallery(None, 100)
        for s in gallery_skills:
            existing_names.add(s.name.replace("-perspective", ""))

        try:
            items = await self._llm_recommend(existing_names)
        except Exception:
            raise BusinessException(ErrorCode.INTERNAL_ERROR, "大模型生成推荐失败，请稍后重试")
        return RecommendationResponse(items=items)

    async def _llm_recommend(self, existing_names: set[str]) -> list[RecommendationItem]:
        excluded = ", ".join(sorted(existing_names)[:30]) if existing_names else "无"
        prompt = f"""你是一个人物推荐助手。请推荐 30 位值得生成 AI 人格的知名人物。

要求：
1. 涵盖不同领域（科技、哲学、科学、艺术、商业、文学、政治等），尽量多样化
2. 避免太冷门的人物——用户应该听说过他们
3. 每人提供 name（中文名）、description（一句话简介，15字以内）、query（用于搜索的详细描述）

已存在的人物（必须排除，不要推荐）：
{excluded}

直接返回 JSON 数组，不要解释：
[{{"name": "...", "description": "...", "query": "..."}}]"""

        api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
        model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
        llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                          temperature=0.9, timeout=120)

        for attempt in range(2):
            result = await llm.ainvoke(prompt)
            text = result.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                if attempt == 0:
                    continue
                # 最后一次尝试：截断到最后一个完整对象
                last_comma = text.rfind("},")
                if last_comma > 0:
                    data = json.loads(text[:last_comma + 1] + "]")
                else:
                    raise RuntimeError("无法解析 LLM 返回的 JSON")

            items = []
            seen = set(existing_names)
            for d in data:
                name = d.get("name", "")
                key = _sanitize_name(name)
                if key and key not in seen:
                    seen.add(key)
                    items.append(RecommendationItem(
                        name=name,
                        description=d.get("description", ""),
                        query=d.get("query", f"{name}"),
                    ))
            return items

        raise RuntimeError("LLM returned malformed JSON twice")

    @staticmethod
    def _static_recommend(existing_names: set[str], random) -> list[RecommendationItem]:
        available = [item for item in _RECOMMENDATION_POOL if _sanitize_name(item["name"]) not in existing_names]
        if len(available) < 6:
            available = _RECOMMENDATION_POOL.copy()
        random.shuffle(available)
        return [RecommendationItem(name=item["name"], description=item["description"], query=item["query"])
                for item in available]

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

        asyncio.create_task(run_skill_generation(skill.id, owner_id, query, skill_name))
        return CharacterService._to_response(skill)

    def generation_sse(self, skill_id: str):
        return generation_sse_stream(skill_id)

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _to_response(skill, quotes: list[str] | None = None) -> CharacterResponse:
        if quotes is None:
            quotes = CharacterService._extract_quotes(skill)
        desc = skill.description or ""
        if quotes:
            desc = f'"{quotes[0]}"'
        return CharacterResponse(
            id=str(skill.id), owner_id=str(skill.owner_id),
            name=skill.name.replace("-perspective", ""), description=desc,
            tags=skill.tags or [], is_public=skill.is_public, status=skill.status,
            source_count=skill.source_count, model_count=skill.model_count,
            created_at=skill.created_at.isoformat(), updated_at=skill.updated_at.isoformat(),
            quotes=quotes,
        )

    _quotes_cache: dict[tuple[str, str], tuple[float, list[str]]] = {}

    @classmethod
    def _extract_quotes(cls, skill) -> list[str]:
        try:
            skill_path = SKILLS_ROOT / str(skill.owner_id) / skill.name / "SKILL.md"
            if not skill_path.exists():
                return []
            mtime = skill_path.stat().st_mtime
            cache_key = (str(skill.owner_id), skill.name)
            if cache_key in cls._quotes_cache:
                cached_mtime, cached_quotes = cls._quotes_cache[cache_key]
                if cached_mtime == mtime:
                    return cached_quotes
            text = skill_path.read_text(encoding="utf-8")
            quotes = []
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("> "):
                    quote = stripped[2:].strip().strip('"').strip('"').strip('"')
                    if len(quote) > 10:
                        quotes.append(quote)
            result = quotes[:5]
            cls._quotes_cache[cache_key] = (mtime, result)
            return result
        except Exception:
            return []


def _sanitize_name(query: str) -> str:
    name = query.strip().lower().replace(" ", "-")
    name = "".join(c for c in name if c.isalnum() or c == "-")
    return name[:40]


async def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(db)
