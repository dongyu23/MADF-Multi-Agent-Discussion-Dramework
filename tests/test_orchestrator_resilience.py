import asyncio
import uuid

import pytest

from agent_engine.discussion import orchestrator as orch_mod
from agent_engine.discussion.orchestrator import AgentDecision, Orchestrator


class FakeAgent:
    pass


@pytest.mark.asyncio
async def test_think_deadline_is_shared_not_sequential(monkeypatch):
    monkeypatch.setattr(orch_mod, "THINK_TIMEOUT_SECONDS", 0.03)

    def fake_create_roundtable_agent(path: str):
        return FakeAgent(), f"prompt for {path}"

    async def fake_host_stream(prompt: str):
        yield "开场"

    async def slow_think(system_prompt: str, agent_id: str, agent_name: str, context: str):
        await asyncio.sleep(0.2)
        return AgentDecision(agent_id, agent_name, "speak", 0.9, "should timeout")

    async def empty_speak_stream(agent, config, speak_prompt: str):
        if False:
            yield ""

    async def fallback_speak(agent, config, speak_prompt: str):
        return "兜底发言"

    monkeypatch.setattr(orch_mod, "create_roundtable_agent", fake_create_roundtable_agent)
    monkeypatch.setattr(orch_mod, "_call_host_llm_stream", fake_host_stream)
    monkeypatch.setattr(orch_mod, "_agent_think_fast", slow_think)
    monkeypatch.setattr(orch_mod, "_agent_speak_stream", empty_speak_stream)
    monkeypatch.setattr(orch_mod, "_agent_speak_once", fallback_speak)

    events: list[tuple[str, dict]] = []
    runner: Orchestrator | None = None

    async def on_event(event_type: str, data: dict):
        events.append((event_type, data))
        if event_type == "agent_speak_end" and runner:
            runner.duration = 0

    runner = Orchestrator(
        discussion_id=uuid.uuid4(),
        topic="测试统一超时",
        duration=1,
        agent_skill_paths={"A": "/skills/a", "B": "/skills/b", "C": "/skills/c"},
        on_event=on_event,
    )

    started = asyncio.get_running_loop().time()
    await runner.run()
    elapsed = asyncio.get_running_loop().time() - started

    timeout_events = [data for event, data in events if event == "agent_think_timeout"]
    assert len(timeout_events) == 3
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_empty_streaming_speech_gets_fallback_content(monkeypatch):
    monkeypatch.setattr(orch_mod, "THINK_TIMEOUT_SECONDS", 0.1)

    def fake_create_roundtable_agent(path: str):
        return FakeAgent(), f"prompt for {path}"

    async def fake_host_stream(prompt: str):
        yield "开场"

    async def fast_think(system_prompt: str, agent_id: str, agent_name: str, context: str):
        return AgentDecision(agent_id, agent_name, "speak", 0.9, "应该发言")

    async def empty_speak_stream(agent, config, speak_prompt: str):
        if False:
            yield ""

    async def empty_fallback(agent, config, speak_prompt: str):
        return ""

    monkeypatch.setattr(orch_mod, "create_roundtable_agent", fake_create_roundtable_agent)
    monkeypatch.setattr(orch_mod, "_call_host_llm_stream", fake_host_stream)
    monkeypatch.setattr(orch_mod, "_agent_think_fast", fast_think)
    monkeypatch.setattr(orch_mod, "_agent_speak_stream", empty_speak_stream)
    monkeypatch.setattr(orch_mod, "_agent_speak_once", empty_fallback)

    events: list[tuple[str, dict]] = []
    runner: Orchestrator | None = None

    async def on_event(event_type: str, data: dict):
        events.append((event_type, data))
        if event_type == "agent_speak_end" and runner:
            runner.duration = 0

    runner = Orchestrator(
        discussion_id=uuid.uuid4(),
        topic="测试空发言",
        duration=1,
        agent_skill_paths={"A": "/skills/a"},
        on_event=on_event,
    )

    await runner.run()

    speak_end = [data for event, data in events if event == "agent_speak_end"][-1]
    timeout = [data for event, data in events if event == "agent_speak_timeout"][-1]
    assert speak_end["content"] == orch_mod.EMPTY_SPEECH_FALLBACK_TEXT
    assert speak_end["empty_speech"] is True
    assert timeout["content"] == orch_mod.EMPTY_SPEECH_FALLBACK_TEXT
