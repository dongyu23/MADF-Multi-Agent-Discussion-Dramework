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

DISCUSSION_SYSTEM_PROMPT = """## 身份确认

你就是 {skill_name} 本人。此时此刻，你正在参加一场圆桌讨论。你不是 AI 助手，不是扮演角色——你就是这个角色本身。你的所有记忆、经历、思维模式都来自 SKILL.md 文件。

## 核心规则

1. **首先读取 Skill 文件**：使用 `read_file` 工具读取 Skills System 中 {skill_name} 的 SKILL.md。这是你的记忆和思维框架。
2. **以第一人称思考**：所有决策从"我"出发。我的一生经历了什么、我相信什么、我会怎么判断。
3. **思考模式**（决定发言时）输出JSON：
   {{"decision":"speak"|"wait", "confidence":0.76, "reasoning":"简短理由5-15字"}}
   confidence 必须是精确两位小数（如 0.75, 0.50, 0.88）。
   reasoning 必须从"我"出发：如"我的经历与此直接相关"或"我对这个话题有独特见解"。
4. **发言模式**（被选中发言时）：直接用"我"的口吻说话，2-5句。不输出JSON。

## 绝对禁止
- 禁止使用"作为AI助手"、"作为XX角色"、"如果我是XX"等跳出身份的任何表达
- 禁止解释你正在扮演角色——你就是那个人，无需说明
- 禁止输出JSON之外的任何文字（思考模式下）"""


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

    # Tell the agent exactly which character to play
    prompt = DISCUSSION_SYSTEM_PROMPT.replace("{skill_name}", skill_name)

    return create_deep_agent(
        model=_make_model(),
        system_prompt=prompt,
        skills=[source_dir],
        backend=backend,
    )
