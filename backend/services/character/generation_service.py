"""Skill generation with deepagent integration + SSE progress streaming.

All frontend-visible messages are in Chinese.
Events pushed: main-agent phases, sub-agent spawn/completion, tool calls, output summary.
"""

import asyncio
import contextvars
import logging
import shutil
import time

# ── 全局 Token 累加器（ContextVar，支持 asyncio 并发） ──
_acc_context: contextvars.ContextVar["TokenAccumulator | None"] = contextvars.ContextVar(
    "token_accumulator", default=None
)


class TokenAccumulator:
    """ContextVar 隔离的 token 累加器。通过 monkey-patch ChatOpenAI._agenerate/_astream 全局拦截。"""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.llm_call_count = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def activate(self) -> None:
        _acc_context.set(self)

    def deactivate(self) -> None:
        _acc_context.set(None)

    @staticmethod
    def current() -> "TokenAccumulator | None":
        return _acc_context.get()


def _patch_chatopenai() -> None:
    """Monkey-patch ChatOpenAI._generate / _agenerate 来捕获所有 LLM token 消耗。
    只执行一次。覆盖主 Agent 和所有子 Agent 的 ChatOpenAI 实例。
    """
    from langchain_openai import ChatOpenAI
    if getattr(ChatOpenAI, "_token_patched", False):
        return

    _orig_ainvoke = ChatOpenAI.ainvoke
    _orig_astream = ChatOpenAI.astream

    async def _patched_ainvoke(self, input, config=None, *, stop=None, **kwargs):
        result = await _orig_ainvoke(self, input, config=config, stop=stop, **kwargs)
        acc = TokenAccumulator.current()
        if acc is not None:
            usage = getattr(result, "usage_metadata", None) or {}
            inp = usage.get("input_tokens", 0) or 0
            out = usage.get("output_tokens", 0) or 0
            if inp or out:
                acc.input_tokens += inp
                acc.output_tokens += out
                acc.llm_call_count += 1
        return result

    async def _patched_astream(self, input, config=None, *, stop=None, **kwargs):
        last_chunk = None
        async for chunk in _orig_astream(self, input, config=config, stop=stop, **kwargs):
            last_chunk = chunk
            yield chunk
        acc = TokenAccumulator.current()
        if acc is not None and last_chunk is not None:
            usage = getattr(last_chunk, "usage_metadata", None) or {}
            inp = usage.get("input_tokens", 0) or 0
            out = usage.get("output_tokens", 0) or 0
            if inp or out:
                acc.input_tokens += inp
                acc.output_tokens += out
                acc.llm_call_count += 1

    ChatOpenAI.ainvoke = _patched_ainvoke
    ChatOpenAI.astream = _patched_astream
    ChatOpenAI._token_patched = True
import uuid
from pathlib import Path

from agent_engine.skill_gen.agent import create_nvwa_agent
from backend.config import settings
from backend.deps import async_session_factory
from backend.models.skill_generation_event import SkillGenerationEvent
from backend.services.audit.repository import AuditRepository
from backend.services.character.file_manager import SKILLS_ROOT
from backend.services.character.repository import CharacterRepository
from sqlalchemy import func, select

logger = logging.getLogger(__name__)

# Sub-agent name → 中文阶段描述
SUBAGENT_CN: dict[str, str] = {
    "researcher-writings":     "📚 调研子智能体：搜集著作与系统性长文",
    "researcher-conversations": "🎙️ 调研子智能体：搜集对话与深度访谈",
    "researcher-expressions":   "✍️ 调研子智能体：搜集表达风格与碎片化内容",
    "researcher-external":      "👁️ 调研子智能体：搜集外部视角与批评",
    "researcher-decisions":     "🔀 调研子智能体：搜集重大决策与行动记录",
    "researcher-timeline":      "📅 调研子智能体：构建完整人物时间线",
    "synthesizer":              "🧠 提炼子智能体：提取心智模型与思维框架",
    "validator-known":          "✅ 验证子智能体：对比已知立场进行测试",
    "validator-edge":           "🔍 验证子智能体：边缘场景不确定性测试",
    "validator-voice":          "🎭 验证子智能体：检查表达风格真实性",
    "optimizer-structure":      "🏗️ 优化子智能体：优化 Skill 结构与可操作性",
    "optimizer-usability":      "🔧 优化子智能体：优化激活触发与角色扮演规则",
    # General-purpose fallback
    "general-purpose":          "🤖 通用子智能体：执行复杂多步任务",
}

# Tool name → 中文描述
TOOL_CN: dict[str, str] = {
    "task":             "派发子Agent",
    "internet_search":  "联网搜索",
    "read_file":        "读取文件",
    "write_file":       "写入文件",
    "edit_file":        "编辑文件",
    "ls":               "浏览目录",
    "glob":             "搜索文件",
    "grep":             "搜索内容",
    "execute":          "执行脚本",
    "write_todos":      "更新待办",
}


def _truncate(s: str, max_len: int = 120) -> str:
    return s[:max_len] + "…" if len(s) > max_len else s


SENTINEL = object()

class GenerationProgress:
    """SSE 进度追踪器，支持多订阅者。"""

    def __init__(self, skill_id: str, owner_id: str):
        self.skill_id = uuid.UUID(skill_id)
        self.owner_id = uuid.UUID(owner_id)
        self._queues: list[asyncio.Queue] = []
        self._current_status = {"level": "idle", "message": "等待中"}
        self._lock = asyncio.Lock()
        self._closed = False
        self._seq = 0

    async def initialize(self) -> None:
        async with async_session_factory() as session:
            stmt = select(func.coalesce(func.max(SkillGenerationEvent.seq), 0)).where(
                SkillGenerationEvent.deleted_at.is_(None),
                SkillGenerationEvent.skill_id == self.skill_id,
            )
            result = await session.execute(stmt)
            self._seq = int(result.scalar_one() or 0)

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._queues.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    async def push(self, level: str, message: str, extra: dict | None = None) -> None:
        event = await self._persist(level, message, extra)
        msg: dict = {
            "seq": event.seq,
            "level": level,
            "message": message,
            "created_at": event.created_at.isoformat(),
        }
        if extra:
            msg["extra"] = extra
        self._current_status = msg
        async with self._lock:
            for q in self._queues:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass

    async def _persist(self, level: str, message: str, extra: dict | None) -> SkillGenerationEvent:
        self._seq += 1
        async with async_session_factory() as session:
            event = SkillGenerationEvent(
                skill_id=self.skill_id,
                owner_id=self.owner_id,
                seq=self._seq,
                level=level,
                message=message,
                extra=extra,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def close(self) -> None:
        async with self._lock:
            self._closed = True
            for q in self._queues:
                try:
                    q.put_nowait(SENTINEL)
                except asyncio.QueueFull:
                    pass
            self._queues.clear()


_progress: dict[str, GenerationProgress] = {}
_progress_lock = asyncio.Lock()


async def _get_progress(skill_id: str, owner_id: str) -> GenerationProgress:
    async with _progress_lock:
        if skill_id not in _progress:
            progress = GenerationProgress(skill_id, owner_id)
            await progress.initialize()
            _progress[skill_id] = progress
        return _progress[skill_id]


async def _get_existing_progress(skill_id: str) -> GenerationProgress | None:
    async with _progress_lock:
        return _progress.get(skill_id)


async def _cleanup_progress(skill_id: str) -> None:
    async with _progress_lock:
        _progress.pop(skill_id, None)


async def run_skill_generation(
    skill_id: uuid.UUID,
    owner_id: str,
    query: str,
    skill_name: str,
) -> None:
    """后台任务：通过 deepagent astream() 实时推送生成进度。

    推送的事件层级:
      level="main"  — 主流程阶段（创建Agent、启动调研、复制文件等）
      level="sub"   — 子智能体被派发时触发
      level="tool"  — 工具调用被捕获时（搜索、读写文件等）
      level="done"  — 生成完成
      level="error" — 生成失败
    """
    try:
        progress = await _get_progress(str(skill_id), owner_id)
        await progress.push("main", "阶段 0/5：正在创建 Deep Agent 实例…")

        # 创建工作目录
        nuwa_source = Path(__file__).parent.parent.parent.parent / "agent_engine" / "skill_gen" / "nuwa_source"
        work_root = SKILLS_ROOT / owner_id / skill_name / ".gen_work"
        dest_dir = SKILLS_ROOT / owner_id / skill_name
        if work_root.exists():
            shutil.rmtree(str(work_root))
        shutil.copytree(str(nuwa_source), str(work_root), dirs_exist_ok=True)

        skill_distill = work_root / "skill-distill" / skill_name
        skill_distill.mkdir(parents=True, exist_ok=True)
        (skill_distill / "references" / "research").mkdir(parents=True, exist_ok=True)

        # 创建 deep agent（内部调用 deepagents.create_deep_agent()）
        # 启用全局 Token 拦截：patch ChatOpenAI 的 _agenerate，捕获所有 LLM 调用
        _patch_chatopenai()
        token_acc = TokenAccumulator()
        token_acc.activate()

        async def _on_search_failover(msg: str) -> None:
            await progress.push("tool", msg, {"tool": "internet_search", "failover": True})

        agent = create_nvwa_agent(
            model=settings.llm_model,
            api_key=settings.llm_api_key or None,
            base_url=settings.llm_api_base or None,
            enable_langsmith=False,
            root_dir=str(work_root),
            on_search_failover=_on_search_failover,
        )

        prompt = (
            f"蒸馏 {query}，创建完整的 perspective skill。\n\n"
            f"你必须严格按照 nuwa-skill 的 5 阶段流水线执行，不可跳过任何阶段：\n\n"
            f"Phase 1（必须）：使用 task 工具并行派发 6 个调研子 Agent（researcher-writings, researcher-conversations, "
            f"researcher-expressions, researcher-external, researcher-decisions, researcher-timeline），"
            f"各自将结果写入 /skill-distill/{skill_name}/references/research/01-06.md\n"
            f"Phase 2（必须）：使用 task 工具派发 synthesizer 子 Agent，读取 6 个调研文件，提取心智模型和思维框架\n"
            f"Phase 3（必须）：你自己基于 synthesizer 结果，按 skill-template.md 模板构建 /skill-distill/{skill_name}/SKILL.md\n"
            f"Phase 4（必须）：使用 task 工具并行派发 3 个验证子 Agent（validator-known, validator-edge, validator-voice）测试 SKILL.md\n"
            f"Phase 5（必须）：使用 task 工具并行派发 2 个优化子 Agent（optimizer-structure, optimizer-usability）优化 SKILL.md\n\n"
            f"核心要求：\n"
            f"- 生成的 SKILL.md 必须包含 YAML frontmatter, 角色扮演规则, 回答工作流, 身份卡, "
            f"核心心智模型, 决策启发式, 表达DNA, 时间线, 价值观与反模式, 智识谱系, 诚实边界, 调研来源(每条须含原始URL)\n"
            f"- 每个阶段完成后才进入下一阶段，禁止跳阶段\n"
            f"- 禁止不派发子 Agent 就自己写文件"
        )

        config = {"configurable": {"thread_id": f"skill-gen-{skill_id}"}}
        await progress.push("main", "阶段 1/5：调度 6 个并行调研子智能体，通过 Tavily 联网搜索…")

        spawned: set[str] = set()
        seen_nodes: set[str] = set()
        seen_tc_ids: set[str] = set()
        synced_files: set[tuple[str, int]] = set()
        _last_sync: float = 0.0
        _announced_strategy = False
        _announced_phase: dict[int, bool] = {}
        _last_main_msg = ""
        tool_seq = 0

        def _phase_researchers(s: set[str]) -> bool:
            return bool({"researcher-writings", "researcher-conversations", "researcher-expressions",
                         "researcher-external", "researcher-decisions", "researcher-timeline"} & s)

        async def _announce_phase(phase: int, msg: str) -> None:
            if phase not in _announced_phase:
                _announced_phase[phase] = True
                await _push_main(msg)

        async def _push_main(msg: str) -> None:
            nonlocal _last_main_msg
            if msg != _last_main_msg:
                _last_main_msg = msg
                await progress.push("main", msg)

        # Helper: sync new files from work dir → final dir, push file_created events
        async def _sync_new_files(force: bool = False) -> None:
            nonlocal _last_sync
            now = time.monotonic()
            if not force and now - _last_sync < 3.0:
                return
            _last_sync = now
            generated_src = work_root / "skill-distill" / skill_name
            if not generated_src.exists():
                return
            for p in sorted(generated_src.rglob("*")):
                if not p.is_file():
                    continue
                rel = str(p.relative_to(generated_src))
                key = (rel, p.stat().st_size)
                if key in synced_files:
                    continue
                synced_files.add(key)
                dest = dest_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(p), str(dest))
                except OSError:
                    logger.warning("Failed to copy %s to %s", rel, dest_dir)
                await progress.push("file", f"文件产出：{rel}", {
                    "path": rel,
                    "size": p.stat().st_size,
                })

        async for event in agent.astream(
            {"messages": [{"role": "user", "content": prompt}]},
            config,
        ):
            # ── 主 Agent 图节点事件 ──
            for node_name in event:
                if node_name.startswith("__") or node_name in seen_nodes:
                    continue
                seen_nodes.add(node_name)

            # ── 从消息中提取工具调用和返回 ──
            for node_name, node_data in event.items():
                if node_name.startswith("__") or node_data is None:
                    continue
                messages = node_data.get("messages", []) if hasattr(node_data, "get") else []
                tc_name_map: dict[str, str] = {}  # tool_call_id → name
                for msg in messages:
                    mtype = msg.__class__.__name__ if hasattr(msg, "__class__") else ""

                    # 工具调用（AIMessage 带 tool_calls）
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                            if tc_id in seen_tc_ids:
                                continue
                            seen_tc_ids.add(tc_id)
                            tool_seq += 1
                            tc_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                            tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                            tc_name_map[tc_id] = tc_name
                            tool_label = TOOL_CN.get(tc_name, tc_name)

                            # 子智能体派发
                            if tc_name == "task":
                                sub_type = (
                                    tc_args.get("subagent_type", "")
                                    or tc_args.get("subagent_name", "")
                                    or tc_args.get("type", "")
                                    or tc_args.get("name", "")
                                )
                                if sub_type and sub_type not in spawned:
                                    spawned.add(sub_type)
                                    sub_label = SUBAGENT_CN.get(sub_type, f"子智能体: {sub_type}")
                                    desc = tc_args.get("description", "") if isinstance(tc_args, dict) else ""
                                    await progress.push("sub", sub_label, {
                                        "agent": sub_type,
                                        "description": _truncate(str(desc)),
                                        "seq": tool_seq,
                                    })
                                    logger.info("Generation [%s] subagent #%d: %s", str(skill_id)[:8], tool_seq, sub_type)

                            # 搜索调用
                            elif tc_name == "internet_search":
                                search_q = tc_args.get("query", "") if isinstance(tc_args, dict) else str(tc_args)[:120]
                                await progress.push("tool", f"{tool_label}：{_truncate(str(search_q), 80)}", {
                                    "tool": tc_name,
                                    "query": str(search_q)[:200],
                                    "seq": tool_seq,
                                })

                            # 其他工具
                            elif tc_name != "task":
                                await progress.push("tool", f"调用工具：{tool_label}", {
                                    "tool": tc_name,
                                    "seq": tool_seq,
                                })

                        # 工具返回（ToolMessage）— 对搜索类静默，只推送文件类返回值
                        if mtype == "ToolMessage":
                            tc_msg_id = str(getattr(msg, "tool_call_id", ""))
                            if tc_msg_id in seen_tc_ids:
                                continue
                            seen_tc_ids.add(tc_msg_id)
                            content = str(getattr(msg, "content", ""))
                            resp_tool = tc_name_map.get(tc_msg_id, "")
                            if len(content) > 15 and resp_tool not in ("internet_search",):
                                preview = _truncate(content, 80)
                                await progress.push("tool", f"{TOOL_CN.get(resp_tool, resp_tool)}返回：{preview}", {
                                    "type": "result",
                                })

            # 同步新文件到最终目录 + 推送 file_created 事件
            await _sync_new_files()

            # 阶段检测与公告
            researchers_done = _phase_researchers(spawned)
            synth_spawned = "synthesizer" in spawned
            validators_spawned = bool({"validator-known", "validator-edge", "validator-voice"} & spawned)
            optimizers_spawned = bool({"optimizer-structure", "optimizer-usability"} & spawned)

            if researchers_done and not synth_spawned:
                await _announce_phase(1, "Phase 1/5 完成：6 个调研子 Agent 已派发，正在并行搜索…")
            if synth_spawned and not validators_spawned:
                await _announce_phase(2, "Phase 2/5：synthesizer 子 Agent 正在提炼心智模型与思维框架…")
            if validators_spawned and not optimizers_spawned:
                await _announce_phase(4, "Phase 4/5：3 个验证子 Agent 正在并行测试…")
            if optimizers_spawned:
                await _announce_phase(5, "Phase 5/5：2 个优化子 Agent 正在精炼 Skill…")

            # 进度汇总（每种状态只推一次）
            if len(spawned) == 0 and len(seen_nodes) >= 2 and not _announced_strategy:
                _announced_strategy = True
                await _push_main("主智能体正在分析任务并制定子智能体调度策略…")

        token_acc.deactivate()

        # ── 最终同步所有剩余文件 ──
        await _sync_new_files(force=True)
        shutil.rmtree(str(work_root), ignore_errors=True)

        # 清理 LLM 可能创建的 .gitkeep 占位文件及随之产生的空目录
        for gp in dest_dir.rglob(".gitkeep"):
            gp.unlink(missing_ok=True)
        for dp in sorted(dest_dir.rglob("*"), reverse=True):
            if dp.is_dir() and not any(dp.iterdir()):
                try:
                    dp.rmdir()
                except OSError:
                    pass

        file_count = 0
        for _p in dest_dir.rglob("*"):
            if _p.is_file():
                file_count += 1

        async with async_session_factory() as bg_session:
            bg_repo = CharacterRepository(bg_session)
            bg_audit = AuditRepository(bg_session)
            await bg_repo.set_status(skill_id, "ready", {
                "source_count": file_count,
                "description": f"基于公开资料的 {query} 思维框架。包含心智模型、决策启发式和表达DNA。",
            })
            await bg_audit.record(None, uuid.UUID(owner_id) if owner_id else None, "skill.generate_complete", {
                "skill_id": str(skill_id), "file_count": file_count,
                "subagents_spawned": len(spawned),
                "input_tokens": token_acc.input_tokens,
                "output_tokens": token_acc.output_tokens,
                "total_tokens": token_acc.total_tokens,
                "llm_call_count": token_acc.llm_call_count,
            }, level="P1")

        # 列出生成的文件
        file_list: list[str] = []
        for _p in sorted(dest_dir.rglob("*")):
            if _p.is_file():
                rel = str(_p.relative_to(dest_dir))
                file_list.append(f"{rel} ({_p.stat().st_size:,} 字节)")

        await progress.push("done", f"生成完成，共 {file_count} 个文件", {
            "file_count": file_count,
            "subagents_spawned": len(spawned),
            "files": file_list[:10],
        })
        await progress.close()
        logger.info("Skill generation complete: %s (%d files, %d subagents)",
                     str(skill_id)[:8], file_count, len(spawned))

    except Exception as e:
        token_acc.deactivate()
        logger.exception("Skill generation failed: %s", str(skill_id)[:8])
        await progress.push("error", f"生成失败：{e}")
        await progress.close()

        async with async_session_factory() as bg_session:
            bg_repo = CharacterRepository(bg_session)
            bg_audit = AuditRepository(bg_session)
            await bg_repo.set_status(skill_id, "error")
            await bg_audit.record(None, uuid.UUID(owner_id) if owner_id else None, "skill.generate_error", {
                "skill_id": str(skill_id), "error": str(e)[:500],
                "input_tokens": token_acc.input_tokens,
                "output_tokens": token_acc.output_tokens,
                "total_tokens": token_acc.total_tokens,
                "llm_call_count": token_acc.llm_call_count,
            }, level="P1")
    finally:
        await _cleanup_progress(str(skill_id))


def _event_to_payload(event: SkillGenerationEvent) -> dict:
    payload = {
        "seq": event.seq,
        "level": event.level,
        "message": event.message,
        "created_at": event.created_at.isoformat(),
    }
    if event.extra:
        payload["extra"] = event.extra
    return payload


async def _load_generation_events(skill_id: str, after_seq: int = 0) -> list[dict]:
    async with async_session_factory() as session:
        stmt = (
            select(SkillGenerationEvent)
            .where(
                SkillGenerationEvent.deleted_at.is_(None),
                SkillGenerationEvent.skill_id == uuid.UUID(skill_id),
                SkillGenerationEvent.seq > after_seq,
            )
            .order_by(SkillGenerationEvent.seq.asc())
        )
        result = await session.execute(stmt)
        return [_event_to_payload(event) for event in result.scalars().all()]


async def generation_sse_stream(skill_id: str, after_seq: int = 0) -> str:
    """SSE endpoint generator: replay persisted history, then live events."""
    import json

    progress = await _get_existing_progress(skill_id)
    queue = await progress.subscribe() if progress and not progress._closed else None
    last_seq = after_seq

    for payload in await _load_generation_events(skill_id, after_seq):
        last_seq = max(last_seq, int(payload.get("seq") or 0))
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    if queue is None:
        return

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15)
                if msg is SENTINEL:
                    return
                seq = int(msg.get("seq") or 0)
                if seq > last_seq:
                    last_seq = seq
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except TimeoutError:
                if progress._closed:
                    return
                if int(progress._current_status.get("seq") or 0) > last_seq:
                    last_seq = int(progress._current_status.get("seq") or 0)
                    yield f"data: {json.dumps(progress._current_status, ensure_ascii=False)}\n\n"
    finally:
        if queue is not None:
            await progress.unsubscribe(queue)
