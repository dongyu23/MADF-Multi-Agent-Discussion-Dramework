"""Skill generation with deepagent integration + SSE progress streaming.

All frontend-visible messages are in Chinese.
Events pushed: main-agent phases, sub-agent spawn/completion, tool calls, output summary.
"""

import asyncio
import logging
import shutil
import uuid
from pathlib import Path

from agent_engine.skill_gen.agent import create_nvwa_agent

from backend.config import settings
from backend.services.character.file_manager import SKILLS_ROOT, SkillFileManager
from backend.services.character.repository import CharacterRepository

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
    "task":             "派发子智能体任务",
    "internet_search":  "联网搜索 (Tavily)",
    "read_file":        "读取文件",
    "write_file":       "写入文件",
    "edit_file":        "编辑文件",
    "ls":               "浏览目录",
    "grep":             "搜索文件内容",
    "execute":          "执行脚本",
}


def _truncate(s: str, max_len: int = 120) -> str:
    return s[:max_len] + "…" if len(s) > max_len else s


class GenerationProgress:
    """SSE 进度追踪器，支持多订阅者。"""

    def __init__(self):
        self._queues: list[asyncio.Queue] = []
        self._current_status = {"level": "idle", "message": "等待中"}

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    def push(self, level: str, message: str, extra: dict | None = None) -> None:
        msg: dict = {"level": level, "message": message}
        if extra:
            msg["extra"] = extra
        self._current_status = msg
        for q in self._queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass


_progress: dict[str, GenerationProgress] = {}


def _get_progress(skill_id: str) -> GenerationProgress:
    if skill_id not in _progress:
        _progress[skill_id] = GenerationProgress()
    return _progress[skill_id]


def _cleanup_progress(skill_id: str) -> None:
    _progress.pop(skill_id, None)


async def run_skill_generation(
    skill_id: uuid.UUID,
    owner_id: str,
    query: str,
    skill_name: str,
    repo: CharacterRepository,
    fm: SkillFileManager,
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
        progress = _get_progress(str(skill_id))
        progress.push("main", "阶段 0/5：正在创建 Deep Agent 实例…")

        # 创建工作目录
        nuwa_source = Path(__file__).parent.parent.parent.parent / "agent_engine" / "skill_gen" / "nuwa_source"
        work_root = SKILLS_ROOT / owner_id / skill_name / ".gen_work"
        if work_root.exists():
            shutil.rmtree(str(work_root))
        shutil.copytree(str(nuwa_source), str(work_root), dirs_exist_ok=True)

        skill_distill = work_root / "skill-distill" / skill_name
        skill_distill.mkdir(parents=True, exist_ok=True)
        (skill_distill / "references" / "research").mkdir(parents=True, exist_ok=True)

        # 创建 deep agent（内部调用 deepagents.create_deep_agent()）
        agent = create_nvwa_agent(
            model=settings.llm_model,
            api_key=settings.llm_api_key or None,
            base_url=settings.llm_api_base or None,
            enable_langsmith=False,
            root_dir=str(work_root),
        )

        prompt = (
            f"蒸馏 {query}，创建完整的 perspective skill。\n\n"
            f"重要：生成的 SKILL.md 必须包含 YAML frontmatter, 角色扮演规则, 回答工作流, 身份卡, "
            f"核心心智模型(含证据+应用+局限), 决策启发式, 表达DNA, 时间线, "
            f"价值观与反模式, 智识谱系, 诚实边界, 调研来源(每条须含原始URL), 创建者归属。\n"
            f"严格按 nuwa-skill 的 references/skill-template.md 模板格式输出。\n"
            f"最终产物写入: /skill-distill/{skill_name}/SKILL.md\n"
            f"调研文件写入: /skill-distill/{skill_name}/references/research/01-writings.md ~ 06-timeline.md"
        )

        config = {"configurable": {"thread_id": f"skill-gen-{skill_id}"}}
        progress.push("main", "阶段 1/5：调度 6 个并行调研子智能体，通过 Tavily 联网搜索…")

        spawned: set[str] = set()
        completed: set[str] = set()
        seen_nodes: set[str] = set()
        tool_seq = 0

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
                for msg in messages:
                    mtype = msg.__class__.__name__ if hasattr(msg, "__class__") else ""

                    # 工具调用（AIMessage 带 tool_calls）
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_seq += 1
                            tc_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                            tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                            tool_label = TOOL_CN.get(tc_name, tc_name)

                            # 子智能体派发
                            if tc_name == "task":
                                sub_type = tc_args.get("subagent_type", "") or tc_args.get("subagent_name", "")
                                if sub_type and sub_type not in spawned:
                                    spawned.add(sub_type)
                                    sub_label = SUBAGENT_CN.get(sub_type, f"子智能体: {sub_type}")
                                    desc = tc_args.get("description", "") if isinstance(tc_args, dict) else ""
                                    progress.push("sub", sub_label, {
                                        "agent": sub_type,
                                        "description": _truncate(str(desc)),
                                        "seq": tool_seq,
                                    })
                                    logger.info("Generation [%s] subagent #%d: %s", str(skill_id)[:8], tool_seq, sub_type)

                            # 搜索调用
                            elif tc_name == "internet_search":
                                search_q = tc_args.get("query", "") if isinstance(tc_args, dict) else str(tc_args)[:120]
                                progress.push("tool", f"{tool_label}：{_truncate(str(search_q), 80)}", {
                                    "tool": tc_name,
                                    "query": str(search_q)[:200],
                                    "seq": tool_seq,
                                })

                            # 其他工具
                            elif tool_label != tc_name and tc_name != "task":
                                progress.push("tool", f"调用工具：{tool_label}", {
                                    "tool": tc_name,
                                    "seq": tool_seq,
                                })

                    # 工具返回（ToolMessage）
                    if mtype == "ToolMessage":
                        content = str(getattr(msg, "content", ""))
                        if len(content) > 15 and content not in completed:
                            completed.add(content[:60])
                            preview = _truncate(content, 100)
                            progress.push("tool", f"工具返回结果：{preview}", {
                                "type": "result",
                                "preview": _truncate(content, 300),
                            })

            # 进度汇总
            if len(spawned) == 0 and len(seen_nodes) >= 2:
                progress.push("main",
                    "主智能体正在分析任务并制定子智能体调度策略…")

        # ── 复制生成结果 ──
        progress.push("main", "阶段收尾：复制生成的 Skill 文件到最终目录…")

        dest_dir = SKILLS_ROOT / owner_id / skill_name
        generated_src = work_root / "skill-distill" / skill_name

        if generated_src.exists():
            for item in generated_src.iterdir():
                dest = dest_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(str(dest))
                    shutil.copytree(str(item), str(dest))
                else:
                    shutil.copy2(str(item), str(dest))

        shutil.rmtree(str(work_root), ignore_errors=True)

        file_count = 0
        for _p in dest_dir.rglob("*"):
            if _p.is_file():
                file_count += 1

        await repo.set_status(skill_id, "ready", {
            "source_count": file_count,
            "description": f"基于公开资料的 {query} 思维框架。包含心智模型、决策启发式和表达DNA。",
        })

        # P1: Audit generation success
        from backend.services.audit.repository import AuditRepository  # noqa: PLC0415
        audit = AuditRepository(repo.session)
        await audit.record(None, uuid.UUID(owner_id) if owner_id else None, "skill.generate_complete", {
            "skill_id": str(skill_id), "file_count": file_count,
            "subagents_spawned": len(spawned),
        })

        # 列出生成的文件
        file_list: list[str] = []
        for _p in sorted(dest_dir.rglob("*")):
            if _p.is_file():
                rel = str(_p.relative_to(dest_dir))
                file_list.append(f"{rel} ({_p.stat().st_size:,} 字节)")

        progress.push("done", f"生成完成，共 {file_count} 个文件", {
            "file_count": file_count,
            "subagents_spawned": len(spawned),
            "files": file_list[:10],
        })
        logger.info("Skill generation complete: %s (%d files, %d subagents)",
                     str(skill_id)[:8], file_count, len(spawned))

    except Exception as e:
        logger.exception("Skill generation failed: %s", str(skill_id)[:8])
        await repo.set_status(skill_id, "error")
        progress.push("error", f"生成失败：{e}")

        # P1: Audit generation failure
        from backend.services.audit.repository import AuditRepository  # noqa: PLC0415
        audit = AuditRepository(repo.session)
        await audit.record(None, uuid.UUID(owner_id) if owner_id else None, "skill.generate_error", {
            "skill_id": str(skill_id), "error": str(e)[:500],
        })


async def generation_sse_stream(skill_id: str) -> str:
    """SSE 端点生成器，前端可通过 EventSource 连接。"""
    import json

    progress = _get_progress(skill_id)
    queue = progress.subscribe()
    try:
        yield f"data: {json.dumps(progress._current_status, ensure_ascii=False)}\n\n"
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except TimeoutError:
                yield f"data: {json.dumps(progress._current_status, ensure_ascii=False)}\n\n"
    finally:
        progress.unsubscribe(queue)
