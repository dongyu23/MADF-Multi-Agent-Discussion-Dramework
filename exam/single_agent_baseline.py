"""Single-agent baseline — ONE LLM plays ALL characters in sequence.

This is fundamentally different from a monologue. The same LLM instance receives
all character skill prompts and simulates a multi-person conversation by
role-playing each character in turn. No orchestrator, no deepagent, no confidence
arbitration — just raw LLM prompted to "be these three people talking".

This tests: can one smart LLM do what MADF does, just by being told to simulate it?
"""

import asyncio, json, os, time, uuid
from pathlib import Path
from langchain_openai import ChatOpenAI

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def _load_skill_content(skill_path: str, max_chars: int = 3000) -> str:
    """Load SKILL.md content from a skill directory, capped at max_chars."""
    skill_dir = Path(skill_path)
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n...(truncated)"
        return text
    return ""


def _build_simulation_prompt(skill_paths: dict[str, str], topic: str) -> str:
    """Build the prompt for a single LLM to simulate all three characters."""
    char_descriptions: list[str] = []
    for name, path in skill_paths.items():
        content = _load_skill_content(path)
        char_descriptions.append(f"### {name}\n{content}")

    all_chars = "\n\n".join(char_descriptions)
    names = list(skill_paths.keys())

    return f"""你现在要模拟一场圆桌讨论。你一个人扮演三个角色：{', '.join(names)}。

每个角色有各自的背景知识、语言风格和思维方式（见下方）。你要在三个角色之间来回切换，每换一个角色就用"【角色名】"标记。

讨论主题：{topic}

规则：
- 每次发言前标注【角色名】，然后直接写该角色的发言内容
- 角色的发言必须符合其背景知识、语言风格和思维方式
- 角色之间要有真正的互动——引用对方、反驳对方、补充对方
- 不要轮流念稿。如果有角色在当前话题上更有发言权，他可以多说。如果有角色没什么可补充的，可以沉默
- 讨论时长约3分钟，大约发言8-12次
- 现在开始。

{all_chars}

主持人：今天我们讨论"{topic}"。参与嘉宾：{', '.join(names)}。

现在开始讨论。请先以【{names[0]}】的身份发言。"""


async def run_single_agent_baseline(
    skill_paths: dict[str, str],
    topic: str,
    duration: int = 180,
    rep: int = 1,
) -> dict:
    """One LLM plays all characters. Returns transcript + stats like a real discussion."""
    from backend.config import settings

    prompt = _build_simulation_prompt(skill_paths, topic)

    llm = ChatOpenAI(
        model=settings.llm_model or os.getenv("LLM_MODEL", "step-3.6"),
        openai_api_key=settings.llm_api_key or os.getenv("LLM_API_KEY"),
        openai_api_base=settings.llm_api_base or os.getenv("LLM_API_BASE"),
        temperature=0.8,
        timeout=30,
    )

    transcript: list[dict] = []
    messages: list[dict] = [{"role": "user", "content": prompt}]
    total_chars = 0
    round_num = 0
    t0 = time.time()

    while time.time() - t0 < duration:
        try:
            result = await asyncio.wait_for(
                llm.ainvoke(messages),
                timeout=45,
            )
        except asyncio.TimeoutError:
            print(f"    LLM timeout at {time.time()-t0:.0f}s")
            break

        response = result.content
        if not response or len(response) < 20:
            print(f"    Short/empty response ({len(response)} chars)")
            break

        # Parse character-tagged segments from the response
        import re
        segments = re.split(r'【([^】]+)】', response)
        # segments alternates: prefix, name, content, name, content...
        for i in range(1, len(segments) - 1, 2):
            name = segments[i].strip()
            content = segments[i + 1].strip()
            if name and content and len(content) > 10:
                round_num += 1
                transcript.append({
                    "speaker": name,
                    "content": content,
                    "round": round_num,
                })
                total_chars += len(content)

        # Continue the conversation
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": "继续。"})

    elapsed = time.time() - t0
    return {
        "condition": "BL",
        "condition_label": "单智能体基线（一人饰三角）",
        "topic": topic,
        "rep": rep,
        "elapsed": round(elapsed, 1),
        "stats": {
            "total_rounds": round_num,
            "forced_speaks": 0,
            "forced_speak_rate": 0.0,
            "avg_confidence": 0.0,
            "avg_speech_length": round(total_chars / max(round_num, 1), 1),
        },
        "transcript": transcript,
    }
