"""Roundtable orchestrator — decentralized speaking with confidence-based arbitration.

The orchestrator is the central runtime controller for a discussion.
Each round:
  1. Broadcast context to all agents → collect decision JSONs
  2. Select speaker by highest confidence (or random if all wait)
  3. Speaker streams their speech tokens
  4. Write to PG + push to Redis SSE
"""

import asyncio
import json
import logging
import os
import random
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI

from agent_engine.discussion.factory import create_roundtable_agent
from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AgentDecision:
    agent_id: str
    agent_name: str
    decision: str      # "speak" | "wait"
    confidence: float  # 0.00–1.00, two decimal places
    reasoning: str = ""  # 简短理由 5-15 字
    raw_output: str = ""


@dataclass
class RoundResult:
    round_num: int
    decisions: list[AgentDecision]
    speaker_name: str
    speaker_agent_id: str
    speech_content: str
    was_forced: bool = False


def _extract_decision(text: str) -> dict | None:
    """Extract the first decision JSON from agent output."""
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


async def _agent_think(agent, agent_id: str, agent_name: str, context: str, config: dict) -> AgentDecision:
    """Agent evaluates the discussion and decides speak/wait."""
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": context}]},
        config,
    )
    raw = result["messages"][-1].content
    parsed = _extract_decision(raw)
    if parsed is None:
        parsed = {"decision": "wait", "confidence": 0.0, "reasoning": "无法解析思考输出"}
    return AgentDecision(
        agent_id=agent_id,
        agent_name=agent_name,
        decision=parsed.get("decision", "wait"),
        confidence=round(float(parsed.get("confidence", 0.0)), 2),
        reasoning=str(parsed.get("reasoning", "")),
        raw_output=raw,
    )


async def _agent_speak_stream(agent, config: dict, speak_prompt: str):
    """True per-token streaming via deepagent astream_events(version='v2').

    astream_events(v2) emits on_chat_model_stream events containing
    individual LLM tokens, enabling genuine typewriter effect.
    Falls back to ainvoke + chunking if v2 API is unavailable.
    """
    try:
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": speak_prompt}]},
            config,
            version="v2",
        ):
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
    except Exception:
        # Fallback: non-streaming ainvoke + manual chunking
        logger.warning("astream_events v2 failed, falling back to ainvoke")
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": speak_prompt}]},
            config,
        )
        full_text = result["messages"][-1].content
        chunk_size = max(1, len(full_text) // 8)
        for i in range(0, len(full_text), chunk_size):
            yield full_text[i:i + chunk_size]
            await asyncio.sleep(0.05)


class Orchestrator:
    """Manages one discussion's lifecycle."""

    def __init__(
        self,
        discussion_id: uuid.UUID,
        topic: str,
        duration: int,
        agent_skill_paths: dict[str, str],  # {agent_name: skill_dir_path}
        on_event: Callable | None = None,    # async callback(event_type, data)
    ):
        self.discussion_id = discussion_id
        self.topic = topic
        self.duration = duration  # seconds
        self.agent_skill_paths = agent_skill_paths
        self.on_event = on_event
        self.status = "pending"
        self.current_round = 0
        self.messages: list[dict] = []

    async def run(self) -> list[RoundResult]:
        """Execute the full discussion: intro → rounds → summary."""
        self.status = "running"
        results: list[RoundResult] = []
        start_time = time.time()

        # Build agents
        agents: dict[str, Any] = {}
        agent_configs: dict[str, dict] = {}
        for name, path in self.agent_skill_paths.items():
            agents[name] = create_roundtable_agent(path)
            agent_configs[name] = {"configurable": {"thread_id": f"disc-{self.discussion_id}-{name}"}}

        # ── Host intro: LLM generates opening statement ──
        if self.on_event:
            await self.on_event("host_intro_start", {"discussion_id": str(self.discussion_id)})

        intro_prompt = (
            f"你是一位圆桌论坛主持人。请为一场讨论做开场白。\n"
            f"讨论主题：{self.topic}\n"
            f"参与嘉宾：{', '.join(agents.keys())}\n"
            f"讨论时长：{self.duration} 秒\n\n"
            f"要求：欢迎嘉宾，简要介绍话题背景，说明讨论规则。3-5句话，保持中立。"
        )
        intro_content = await _call_host_llm(intro_prompt)
        if self.on_event:
            await self.on_event("host_intro", {
                "discussion_id": str(self.discussion_id),
                "content": intro_content,
            })

        # Main round loop
        while time.time() - start_time < self.duration:
            self.current_round += 1
            round_num = self.current_round

            if self.on_event:
                await self.on_event("round_start", {"round": round_num})

            # Step 1: All agents think
            context = self._build_think_context(round_num)
            tasks = [
                _agent_think(agents[name], str(uuid.uuid4()), name, context, agent_configs[name])
                for name in agents
            ]
            decisions = await asyncio.gather(*tasks)

            if self.on_event:
                for d in decisions:
                    await self.on_event("agent_think", {
                        "agent_id": d.agent_id,
                        "agent_name": d.agent_name,
                        "round": round_num,
                        "decision": d.decision,
                        "confidence": d.confidence,
                        "reasoning": d.reasoning,
                    })

            # Step 2: Select speaker
            speakers = [d for d in decisions if d.decision == "speak"]
            if speakers:
                chosen = max(speakers, key=lambda d: d.confidence)
                was_forced = False
            else:
                chosen = random.choice(decisions)
                was_forced = True
                logger.info("Round %d: all silent, forced speaker %s", round_num, chosen.agent_name)

            # Step 3: Speaker speaks
            speak_prompt = (
                f"现在轮到你发言了。\n"
                f"讨论主题: {self.topic}\n第 {round_num} 轮。\n"
                f"{_format_history(self.messages[-5:])}\n\n"
                f"以第一人称'我'的口吻直接说话。你就是你，你的经历和信念决定了你的观点。"
                f"2-5句话。不输出JSON。"
            )
            # Stream speak tokens — typewriter effect via on_event callbacks
            full_speech = ""
            if self.on_event:
                await self.on_event("agent_speak_start", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                })
            async for chunk in _agent_speak_stream(agents[chosen.agent_name], agent_configs[chosen.agent_name], speak_prompt):
                full_speech += chunk
                if self.on_event:
                    await self.on_event("agent_speak_chunk", {
                        "agent_id": chosen.agent_id,
                        "agent_name": chosen.agent_name,
                        "round": round_num,
                        "content": chunk,
                    })
            if self.on_event:
                await self.on_event("agent_speak_end", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                })
            speech = full_speech

            self.messages.append({
                "round": round_num,
                "speaker": chosen.agent_name,
                "content": speech,
            })

            if self.on_event:
                await self.on_event("agent_speak_chunk", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                    "content": speech,
                })

            results.append(RoundResult(
                round_num=round_num,
                decisions=list(decisions),
                speaker_name=chosen.agent_name,
                speaker_agent_id=chosen.agent_id,
                speech_content=speech,
                was_forced=was_forced,
            ))

        # ── Host summary: LLM summarizes the full discussion ──
        if self.on_event:
            await self.on_event("host_summary_start", {"total_rounds": self.current_round})

        summary_prompt = (
            f"你是一位圆桌论坛主持人。请为以下讨论做总结。\n"
            f"讨论主题：{self.topic}\n"
            f"参与嘉宾：{', '.join(agents.keys())}\n"
            f"共 {self.current_round} 轮发言。\n\n"
            f"讨论内容概要：\n"
        )
        for m in self.messages[-10:]:
            summary_prompt += f"  [{m['speaker']}]: {m['content'][:200]}\n"
        summary_prompt += "\n要求：总结各方核心观点，指出共识与分歧。3-5句话，保持中立。"

        summary_content = await _call_host_llm(summary_prompt)
        if self.on_event:
            await self.on_event("host_summary", {
                "discussion_id": str(self.discussion_id),
                "total_rounds": self.current_round,
                "content": summary_content,
            })
            await self.on_event("discussion_end", {
                "discussion_id": str(self.discussion_id),
                "total_rounds": self.current_round,
            })

        self.status = "completed"
        return results

    def _build_think_context(self, round_num: int) -> str:
        ctx = (
            f"讨论主题: {self.topic}\n"
            f"第 {round_num} 轮。\n"
        )
        if self.messages:
            ctx += "之前发言:\n" + _format_history(self.messages[-10:])
            ctx += "\n"
        ctx += (
            "现在你需要决定是否发言。从你自己的视角出发——"
            "这个话题和你的经历、信念是否相关？你是否有独特的观点需要表达？"
            "输出JSON: {\"decision\":\"speak\"|\"wait\",\"confidence\":0.76,\"reasoning\":\"从'我'出发的简短理由\"}"
        )
        return ctx


def _format_history(messages: list[dict]) -> str:
    return "\n".join(f"[{m['speaker']}]: {m['content'][:300]}" for m in messages)


async def _call_host_llm(prompt: str) -> str:
    """Call LLM for host intro/summary — independent of any agent skill."""
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
    model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
    llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                     temperature=0.7, timeout=30)
    result = await llm.ainvoke(prompt)
    return result.content
