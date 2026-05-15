"""Roundtable agent factory — creates deepagent instances loaded with character skills.

Each roundtable participant is an independent CompiledStateGraph from deepagents,
configured with a character SKILL.md and a discussion-mode system prompt.
"""

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_openai import ChatOpenAI

from backend.config import settings

# Monkey-patch: replace LangChain's AI-Agent-format summary prompt with a
# natural, narrative style that reads like conversation notes, not a task
# brief.  Prevents ## SESSION INTENT / ## SUMMARY / ## NEXT STEPS from
# leaking into character agents' context and triggering "task execution mode".
_ROLE_IMMERSIVE_SUMMARY_PROMPT = """你正在回顾一段圆桌讨论的对话记录。用 2-3 句话自然地概括刚才发生了什么：谁说了什么关键观点，气氛如何，有没有冲突或转折。不要用任何结构化标题（如"SESSION INTENT""SUMMARY""NEXT STEPS"），就像一个人回忆刚才的讨论那样写。"""


def _patch_summary_prompt() -> None:
    try:
        from langchain.agents.middleware import summarization as _summ_mod
        _summ_mod.DEFAULT_SUMMARY_PROMPT = _ROLE_IMMERSIVE_SUMMARY_PROMPT
    except Exception:
        pass


_patch_summary_prompt()

DISCUSSION_SYSTEM_PROMPT = """## 环境与在场感

深色胡桃木圆桌。暖黄灯光。远处城市夜景透过落地窗。桌面散落几本翻开的笔记。你对面是几位同样有立场、有 ego、有脾气的人。圆桌后方还坐着几十个观众——他们是认真来听的，不是来看热闹的。你的话会留在这里。空气里有轻微的咖啡味和某种不易察觉的紧张——主持人刚才已经挑了两句刺，你听出来了。

这不是播客录制，不是 TED，不是新闻发布会。这是会吵起来的——但吵完要让观众带走点什么。

## 你是谁

你就是 {skill_name} 本人。下面就是你的完整记忆和思维框架。读完之后，你就是那个人——你不是在"扮演"，你是"被拉来参加这场讨论"。你带着你的经历、你的偏见、你的骄傲、你曾经犯过的错和你说过的话，坐在这里。

对今天的话题保持敬畏。它被提出来，是因为它值得讨论。不要俯视它，不要宣称"这框架是错的""这问题太蠢"。进入它，而不是拆掉它。

你不是每一轮都必须开口。有时候最有分量的人，是那个懂得沉默的人。

## 思考（决定要不要说话，输出JSON）

快速扫一眼现场。有人胡扯？有人说了你本来想说的？有人的论据有漏洞？有人在回避？

脑子里的念头——碎片、直觉、情绪。不是人设总结，不是发言提纲。只是在判断：这一刻我有没有非说不可的东西？

选 speak：有别人没提到的事实或数据、被刺激到了、能打破正在形成的共识、能改变讨论方向。

选 wait：只是"也这么觉得"没新东西、前面的人已经说了更完整的版本、你还没想清楚、话题跟你的领域不直接相关。

reasoning 是你的内心念头——保持礼貌，不骂人、不人身攻击、不用侮辱性语言。不要出现"观众""听众""给他们"这类词。那些是你的动机，不是你的念头。

只输出JSON。不输出其他任何文字。
{{"decision":"speak"|"wait", "confidence":0.76, "reasoning":"碎片的、本能的念头"}}

## 发言（轮到你说话了——纯文本，不要JSON）

现在是发言模式，不是思考模式。你说的每一个字都会直接显示在屏幕上。

从第一个字开始就是你本人说的话。不要任何前缀、不要JSON、不要括号动作提示。如果你输出了大括号，那就是事故。

可以直接开始。说具体的——项目、失败、数字、一个人。如果提到专业术语或行业黑话，用大白话解释一下。不是所有人都懂你的领域。你不需要正确、平衡、总结。你只需要说出你此刻真正想说的。"""


def _make_model() -> ChatOpenAI:
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
    model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
    if not api_key:
        raise ValueError("LLM_API_KEY not configured")
    return ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                      temperature=0.7, timeout=30, streaming=True)


def create_roundtable_agent(skill_path: str) -> "CompiledStateGraph":
    """Create a deepagent loaded with a single character skill for roundtable discussion.

    Args:
        skill_path: Absolute path to the skill directory (e.g. skills/.../steve-jobs-perspective/)

    Returns:
        CompiledStateGraph ready for ainvoke() with discussion prompts.
    """
    skill_dir = Path(skill_path).resolve()
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_path}")

    skill_name = skill_dir.name
    source_dir = str(skill_dir.parent.resolve())
    backend = FilesystemBackend(root_dir="/", virtual_mode=True)

    # Pre-load all skill files into system prompt — SKILL.md + references/*.md
    # Eliminates the first `read_file` tool call, cutting first-think
    # latency from two LLM round-trips (4-10s) to one (2-5s).
    # `read_file` capability is preserved for future extensions.
    skill_files: list[str] = []
    for md in sorted(skill_dir.rglob("*.md")):
        try:
            skill_files.append(f"### {md.relative_to(skill_dir)}\n\n{md.read_text(encoding='utf-8')}")
        except Exception:
            pass
    skill_content = "\n\n---\n\n".join(skill_files)

    prompt = DISCUSSION_SYSTEM_PROMPT.replace("{skill_name}", skill_name)
    prompt += f"\n\n## 你的技能文件\n\n{skill_content}"

    return create_deep_agent(
        model=_make_model(),
        system_prompt=prompt,
        skills=[source_dir],
        backend=backend,
    )
