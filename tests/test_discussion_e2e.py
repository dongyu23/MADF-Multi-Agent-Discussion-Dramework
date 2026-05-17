"""TDD Step 2: End-to-end roundtable discussion with multiple agents."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

SKILLS_ROOT = Path(__file__).parent.parent / "skills" / "a0dd4bf1-d713-42ef-b093-2da0e1421b05"


async def test_full_discussion():
    """Full roundtable: 2 agents discuss for 3 rounds."""
    from agent_engine.discussion.factory import create_roundtable_agent

    agents = {
        "Steve Jobs": create_roundtable_agent(str(SKILLS_ROOT / "steve-jobs-perspective"))[0](str(SKILLS_ROOT / "steve-jobs-perspective")),
        "Albert Einstein": create_roundtable_agent(str(SKILLS_ROOT / "albert-einstein-perspective"))[0](str(SKILLS_ROOT / "albert-einstein-perspective")),
    }

    topic = "Is technological progress making humanity wiser or just more efficient?"
    messages: list[dict] = []
    agent_configs = {name: {"configurable": {"thread_id": f"disc-e2e-{name.replace(' ','-')}"}}
                     for name in agents}

    for round_num in range(1, 4):
        print(f"\n=== Round {round_num} ===")
        context = _build_context(topic, round_num, messages)

        # Step 1: All agents "think" (output decision JSON)
        decisions = {}
        for name, ag in agents.items():
            result = await ag.ainvoke(
                {"messages": [{"role": "user", "content": context}]},
                agent_configs[name],
            )
            raw = result["messages"][-1].content
            parsed = _extract_json(raw)
            decisions[name] = parsed
            print(f"  {name}: {parsed['decision']} ({parsed['confidence']})")

        # Step 2: Orchestrator selects speaker (highest confidence)
        speakers = {n: d for n, d in decisions.items() if d["decision"] == "speak"}
        if speakers:
            speaker = max(speakers, key=lambda n: float(speakers[n]["confidence"]))
        else:
            import random
            speaker = random.choice(list(agents.keys()))
            print(f"  All silent → forced: {speaker}")

        # Step 3: Speaker "speaks" (stream tokens)
        speak_prompt = (
            f"Discussion topic: {topic}\nRound {round_num}. You have been selected to speak.\n"
            f"Previous discussion:\n{_format_history(messages)}\n\n"
            f"Speak as your character. Share your perspective in 2-4 sentences. Be authentic."
        )
        result = await agents[speaker].ainvoke(
            {"messages": [{"role": "user", "content": speak_prompt}]},
            agent_configs[speaker],
        )
        speech = result["messages"][-1].content
        # Extract the actual speech (strip JSON if present)
        json_part = _extract_json(speech)
        if json_part and json_part.get("decision") == "speak":
            pass  # This is a decision JSON, not a speech — use ainvoke without the decision prompt
        messages.append({"round": round_num, "speaker": speaker, "content": speech[:200]})
        print(f"  💬 {speaker}: {speech[:150]}...")

    assert len(messages) == 3, f"Expected 3 rounds of messages, got {len(messages)}"
    print(f"\n✅ Full discussion complete: {len(messages)} rounds")


def _build_context(topic: str, round_num: int, history: list[dict]) -> str:
    ctx = f"Discussion topic: {topic}\nRound {round_num}.\n"
    if history:
        ctx += "Previous messages:\n"
        for m in history:
            ctx += f"  [{m['speaker']}]: {m['content'][:100]}\n"
    ctx += "\nDecide whether to speak or wait. Output JSON: {\"decision\":\"speak\"|\"wait\",\"confidence\":0.0-1.0}"
    return ctx


def _format_history(history: list[dict]) -> str:
    return "\n".join(f"[{m['speaker']}]: {m['content'][:200]}" for m in history[-5:])


def _extract_json(text: str) -> dict | None:
    import re
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    for m in re.finditer(r"\{[^{}]*\"decision\"[^{}]*\}", text):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    return None


if __name__ == "__main__":
    asyncio.run(test_full_discussion())
