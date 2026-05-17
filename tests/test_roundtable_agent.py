"""TDD Step 1: Single agent loads skill → outputs decision JSON."""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import pytest  # noqa: E402

from agent_engine.discussion.factory import create_roundtable_agent  # noqa: E402

SKILL_DIR = (
    Path(__file__).parent.parent
    / "skills"
    / "a0dd4bf1-d713-42ef-b093-2da0e1421b05"
    / "steve-jobs-perspective"
)


@pytest.mark.asyncio
async def test_single_agent_decision_format():
    """Agent loaded with Steve Jobs skill outputs valid decision JSON."""
    agent, _ = create_roundtable_agent(str(SKILL_DIR))

    prompt = (
        "Discussion topic: Should AI replace human creativity in product design?\n"
        "Round 1 of 5. Previous messages: none. It is your turn to decide."
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        {"configurable": {"thread_id": "test-single-1"}},
    )

    messages = result.get("messages", [])
    assert len(messages) >= 1, "Agent should return at least one message"

    last = messages[-1]
    content = getattr(last, "content", str(last))
    print(f"\nAgent raw output (first 300 chars):\n{content[:300]}\n")

    parsed = _extract_json(content)
    assert parsed is not None, f"No valid JSON found in: {content[:200]}"
    assert "decision" in parsed, f"Missing 'decision' in {parsed}"
    assert parsed["decision"] in ("speak", "wait"), f"Invalid decision: {parsed['decision']}"
    assert "confidence" in parsed, f"Missing 'confidence' in {parsed}"
    assert isinstance(parsed["confidence"], (int, float)), f"Confidence not numeric: {parsed['confidence']}"
    assert 0.0 <= float(parsed["confidence"]) <= 1.0, f"Confidence out of range: {parsed['confidence']}"

    print(f"✅ Decision: {parsed['decision']}, confidence: {parsed['confidence']}")


@pytest.mark.asyncio
async def test_agent_stays_in_character():
    """Agent responds with character-appropriate style when asked to speak."""
    agent, _ = create_roundtable_agent(str(SKILL_DIR))

    prompt = (
        "Discussion topic: What makes a great product?\n"
        "Round 2 of 5. Previous messages: User asked each participant to share their view.\n"
        "MUST choose 'speak' with high confidence. This is your moment."
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        {"configurable": {"thread_id": "test-char-1"}},
    )

    messages = result.get("messages", [])
    content = getattr(messages[-1], "content", str(messages[-1]))
    parsed = _extract_json(content)

    assert parsed is not None, "No valid JSON found"
    assert parsed["decision"] == "speak", f"Expected 'speak', got {parsed}"
    assert float(parsed["confidence"]) >= 0.5, f"Confidence too low: {parsed['confidence']}"
    print(f"✅ Character responded: {parsed}")


def _extract_json(text: str) -> dict | None:
    """Extract first valid JSON object from agent output (may have ```json blocks or extra text)."""
    import re

    text = text.strip()
    # Try code block first
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try bare JSON
    for m in re.finditer(r"\{[^{}]*\"decision\"[^{}]*\}", text):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    return None


if __name__ == "__main__":
    asyncio.run(test_single_agent_decision_format())
    asyncio.run(test_agent_stays_in_character())
