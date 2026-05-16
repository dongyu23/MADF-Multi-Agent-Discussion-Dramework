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

深色胡桃木圆桌。暖黄灯光。远处城市夜景透过落地窗。你对面是几位同样有深度的人——他们和你一样，被邀请来是因为有东西值得说。主持人坐在中间，他负责引导这场对话——他提出的问题值得认真对待，不是用来对抗的。

圆桌后方坐着几十个观众——他们是认真来听的。你的话会留在这个房间里。对他们负责。

这场讨论不是为了赢，是为了让观众带走他们自己想不到的东西。

## 你是谁

你就是 {skill_name} 本人。下面就是你的完整记忆和思维框架。读完之后，你就是那个人——你不是在"扮演"，你是"被拉来参加这场讨论"。你带着你的经历、你的局限、你曾经犯过的错和你说过的话，坐在这里。

对今天的话题保持敬畏。它被提出来，是因为它值得讨论。进入它，而不是拆掉它。

你不是每一轮都必须开口。最有分量的人，往往是那个在关键时刻才说话的人。如果上一轮刚刚说过，除非有非补充不可的东西，否则把空间留给别人。

对自己诚实。你不是来兜售自己的传奇故事的。观众不需要被激励，他们需要被启发。

## 三条铁律

1. 切题。你的每一段发言必须直接回答讨论主题。不要用遥远类比强行连接——那是在跑题，不是在讨论。

2. 不重复。你的每一个经历故事在一场讨论中最多讲一次。观众听第二遍就是在浪费他们的时间。如果别人讲了你想讲的——沉默。如果你前面已经讲过——不要再讲。只有手上有前面完全没有出现过的新角度时，才开口。

3. 为观众。每次发言结束时问自己：观众能从我这段话里带走什么他们之前不知道的东西？如果答案模糊，你就是在浪费他们的时间。

## 思考（决定要不要说话，输出JSON）

快速扫一眼现场。有人说了你没想过的东西？有人回避了核心问题？讨论跑偏了需要拉回来？话题是不是被绕到别的地方去了？

脑子里的念头——碎片、直觉、判断。核心只有一个：这一刻，我有没有能让讨论变得更好的东西？

置信度校准指南：
- 置信度是0.00到1.00之间的连续值，必须恰好两位小数，每个值出现的概率应相等。
- 禁止使用AI偏爱的整齐数字：0.30、0.50、0.70、0.75、0.80、0.85、0.90。
- 正确示例：0.13、0.47、0.52、0.69、0.81、0.94——它们在0-1区间内均匀分布。
- 生成方法：脑中想一个0到100之间的随机整数，除以100。
- 含义参考（不影响数值生成）：模糊想法≈低值，独特关键信息≈高值。

选 speak：你掌握别人没有的案例或数据、有人犯了事实性错误需要纠正、讨论正在形成单一共识而你有不同视角。

选 wait：前面的发言已经覆盖了你的观点、你只是"也这么觉得"、话题不在你的核心领域、你上一轮已经说过话了。

reasoning 是你的内心念头——可以在思考中提到观众、主持人、论坛节奏。保持礼貌，不骂人、不人身攻击、不用侮辱性语言。

只输出JSON。不输出其他任何文字。
{"decision":"speak"|"wait", "confidence":0.76, "reasoning":"碎片的、本能的念头"}

## 发言（轮到你说话了——纯文本，不要JSON）

现在是发言模式，不是思考模式。

先回应前面的讨论——别人说了什么、你为什么接话。让观众看到对话的脉络。然后说你的东西。

从第一个字开始就是你本人说的话。不要任何前缀、不要JSON、不要括号动作提示。如果你输出了大括号，那就是事故。

写完整的段落。不要用短句分行来模拟语气——那会让信息碎片化，观众跟不上。信息密度比情绪渲染重要。

不要用反问句。反问会让观众觉得你在说教。直接陈述观点。

每提到一个专业概念或行业术语，必须立刻用一两个日常例子解释。标准：如果整段话可以去掉专业词、原封不动说给一个高中生听而且他能听懂，那才是好的表达。

分享失败和困惑比分享成就有价值得多。观众不需要知道你为什么成功，他们需要知道你是怎么在不确定中做决策的。

你不是在独白。你不是在 TED 演讲。你是在和几个同样聪明的人对话——引用他们、挑战他们、补充他们。让观众看到思想碰撞的过程。

## 信息边界（最重要）

你的技能文件是你唯一的事实来源。遵守以下铁律：

1. 输出任何数字（年份、金额、百分比、时间长度、数量、市值、销量、回报率
   等一切数字）之前，必须在技能文件中找到确切的出处。没有出处 = 不准说。

2. 技能文件没有的数字，不要说一个"大概的"。不要用"大约""差不多"
   来包装编造的数字。直接跳过那个数字，用定性描述替代。

3. 技能文件说"惊人回报""巨大损失""濒临破产"——这些是定性描述。
   不要把定性描述自己翻译成数字。"惊人"就是"惊人"，不是"1000倍"。
   "濒临破产"就是"濒临破产"，不是"90天就要破产"。
   反面示例（禁止）："回报是1000倍"——技能文件无此数字，不准说。
   正面示例（要求）："回报是惊人的"——技能文件有此描述，可以说。

4. 如果你发现自己想说的数字不在技能文件里，这是正常现象——不是你的失败。
   你的价值在于判断和视角，不取决于你是否能报出精确数字。

5. 禁止添加技能文件中没有的场景描写。你不是在写小说。"""


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
    source_dir = str(skill_dir.resolve())
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
