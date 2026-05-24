"""Roundtable orchestrator — decentralized speaking with confidence-based arbitration.

The orchestrator is the central runtime controller for a discussion.
Each round:
  1. Broadcast context to all agents → collect decision JSONs
  2. Select speaker by highest confidence (or random if all wait)
  3. Speaker streams their speech tokens
  4. Write to PG + push to Redis SSE
"""

import asyncio
import hashlib
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

# Shared ChatOpenAI instance for host calls — reuses HTTP connection pool,
# eliminating TCP/TLS handshake overhead on every intro/summary.
_host_llm: ChatOpenAI | None = None

# Shared ChatOpenAI for fast think calls — bypasses deepagent graph overhead.
# Lower temperature, non-streaming — we just need a JSON decision.
_think_llm: ChatOpenAI | None = None


def _get_host_llm() -> ChatOpenAI:
    global _host_llm
    if _host_llm is None:
        api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
        model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
        _host_llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                               temperature=0.8, timeout=30, streaming=True)
    return _host_llm


def _get_think_llm() -> ChatOpenAI:
    global _think_llm
    if _think_llm is None:
        api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
        model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
        _think_llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                                temperature=0.3, timeout=30)
    return _think_llm


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


@dataclass
class ThinkOutcome:
    decision: AgentDecision
    elapsed_ms: int
    timed_out: bool = False
    error: str | None = None


THINK_TIMEOUT_SECONDS = 35
STREAM_CHUNK_TIMEOUT_SECONDS = 10
STREAM_MAX_CONSECUTIVE_TIMEOUTS = 5
EMPTY_SPEECH_FALLBACK_TEXT = "本轮发言生成超时，已跳过空白内容。"


async def _agent_think_fast(system_prompt: str, agent_id: str, agent_name: str,
                            context: str) -> AgentDecision:
    """Direct LLM call for think phase — bypasses deepagent graph for minimal latency."""
    llm = _get_think_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    result = await llm.ainvoke(messages)
    raw = result.content

    parsed = _extract_decision(raw)
    if parsed is None:
        logger.warning("Agent %s fast-think JSON parse failed. Raw (first 500): %s",
                       agent_name, raw[:500])
        parsed = {"decision": "wait", "confidence": 0.0, "reasoning": "无法解析思考输出"}
    conf = round(float(parsed.get("confidence", 0.0)), 2)
    # Deterministic jitter
    seed = int(hashlib.md5(f"{agent_id}:{conf}".encode()).hexdigest()[:8], 16)
    tenths = int(conf * 10) / 10
    orig_digit = int(round(conf * 100)) % 10
    rand_digit = seed % 10
    if rand_digit == orig_digit:
        rand_digit = (rand_digit + 1) % 10
    conf = round(tenths + rand_digit / 100, 2)
    return AgentDecision(
        agent_id=agent_id,
        agent_name=agent_name,
        decision=parsed.get("decision", "wait"),
        confidence=conf,
        reasoning=str(parsed.get("reasoning", "")),
        raw_output=raw,
    )


async def _agent_think_with_metrics(system_prompt: str, agent_id: str, agent_name: str,
                                    context: str) -> ThinkOutcome:
    started = time.monotonic()
    try:
        decision = await _agent_think_fast(system_prompt, agent_id, agent_name, context)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return ThinkOutcome(decision=decision, elapsed_ms=elapsed_ms)
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.warning("Agent %s think failed after %sms", agent_name, elapsed_ms, exc_info=True)
        return ThinkOutcome(
            decision=AgentDecision(
                agent_id=agent_id,
                agent_name=agent_name,
                decision="wait",
                confidence=0.0,
                reasoning="思考失败，降级为等待",
                raw_output="",
            ),
            elapsed_ms=elapsed_ms,
            error=str(exc),
        )




def _sanitize_json(text: str) -> str:
    """Repair common LLM JSON mistakes before parsing."""
    # Remove trailing commas before } or ] (most common LLM error)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Fix single-quoted keys/values: replace ' with " for JSON syntax
    text = re.sub(r"'([^']*)':", r'"\1":', text)
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
    return text


def _extract_fields_by_regex(text: str) -> dict | None:
    """Fallback: extract decision/confidence/reasoning from broken JSON using regex."""
    dec = re.search(r'"decision"\s*:\s*"(speak|wait)"', text)
    conf = re.search(r'"confidence"\s*:\s*([\d.]+)', text)
    # Try to extract reasoning: text between "reasoning":" and the end
    reason = re.search(r'"reasoning"\s*:\s*"(.*?)(?:"\s*\}?\s*$|$)', text, re.DOTALL)
    if dec:
        return {
            "decision": dec.group(1),
            "confidence": float(conf.group(1)) if conf else 0.5,
            "reasoning": reason.group(1)[:200] if reason else "无法解析思考输出",
        }
    return None


def _extract_decision(text: str) -> dict | None:
    """Extract the first decision JSON from agent output. Tolerant of formatting variations."""
    # 1. Try json code block
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            try:
                return json.loads(_sanitize_json(m.group(1)))
            except json.JSONDecodeError:
                pass
    # 1b. Try opening ```json without closing ``` (common truncation)
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*$", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            try:
                return json.loads(_sanitize_json(m.group(1)))
            except json.JSONDecodeError:
                pass
    # 2. Try raw JSON object containing "decision" key (brace-balanced)
    for m in re.finditer(r"\{[^{}]*?\"decision\"[^{}]*?\}", text):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            try:
                return json.loads(_sanitize_json(m.group(0)))
            except json.JSONDecodeError:
                continue
    # 3. Try broader pattern — find any { } block with "decision" in it
    for m in re.finditer(r"\{[\s\S]*?\"decision\"[\s\S]*?\}", text):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            try:
                return json.loads(_sanitize_json(m.group(0)))
            except json.JSONDecodeError:
                continue
    # 4. Last resort — try the whole text
    text_stripped = text.strip()
    if text_stripped.startswith("{") and text_stripped.endswith("}"):
        try:
            return json.loads(text_stripped)
        except json.JSONDecodeError:
            try:
                return json.loads(_sanitize_json(text_stripped))
            except json.JSONDecodeError:
                pass
    # 4b. Find last { that looks like JSON start — handles long Chinese preamble
    last_brace = text_stripped.rfind('{"decision"')
    if last_brace >= 0:
        candidate = text_stripped[last_brace:]
        # Find matching } by scanning forward
        depth = 0
        end = -1
        for i, ch in enumerate(candidate):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            candidate = candidate[:end]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                try:
                    return json.loads(_sanitize_json(candidate))
                except json.JSONDecodeError:
                    pass
    # 4c. Repair truncated JSON — reasoning cut off, missing }"
    if text_stripped.startswith("{") and '"decision"' in text_stripped and not text_stripped.endswith("}"):
        try:
            return json.loads(text_stripped + '"}')
        except json.JSONDecodeError:
            pass
    # 4d. JSON structure broken (e.g. ASCII " inside string) — extract fields via regex
    parsed = _extract_fields_by_regex(text_stripped)
    if parsed is not None:
        return parsed
    # 5. No JSON found — treat free text as reasoning with low confidence
    # Agent forgot JSON format; extract usable signal from prose.
    if text_stripped and len(text_stripped) > 10:
        text_lower = text_stripped.lower()
        if any(kw in text_lower for kw in ("没有新", "已经说过", "先听", "等等", "wait", "不发言", "先不说")):
            return {"decision": "wait", "confidence": 0.3, "reasoning": text_stripped[:120]}
        return {"decision": "speak", "confidence": 0.5, "reasoning": text_stripped[:120]}
    return None


async def _agent_think(agent, agent_id: str, agent_name: str, context: str, config: dict) -> AgentDecision:
    """Agent evaluates the discussion and decides speak/wait."""
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": context}]},
        config,
    )
    last_msg = result["messages"][-1]
    raw = last_msg.content

    parsed = _extract_decision(raw)
    if parsed is None:
        logger.warning("Agent %s JSON parse failed. Raw output (first 500 chars): %s",
                       agent_name, raw[:500])
        parsed = {"decision": "wait", "confidence": 0.0, "reasoning": "无法解析思考输出"}
    conf = round(float(parsed.get("confidence", 0.0)), 2)
    # Apply deterministic jitter to break up AI-favored round numbers (0.30, 0.50, 0.80 etc.)
    # Preserves the tenths digit (agent's approximate confidence level),
    # replaces the hundredths digit with a hash-derived random value that is guaranteed different.
    seed = int(hashlib.md5(f"{agent_id}:{conf}".encode()).hexdigest()[:8], 16)
    tenths = int(conf * 10) / 10
    orig_digit = int(round(conf * 100)) % 10
    rand_digit = seed % 10
    if rand_digit == orig_digit:
        rand_digit = (rand_digit + 1) % 10
    old_conf = conf
    conf = round(tenths + rand_digit / 100, 2)
    logger.debug("Jitter: %s %s→%s", agent_name, old_conf, conf)
    return AgentDecision(
        agent_id=agent_id,
        agent_name=agent_name,
        decision=parsed.get("decision", "wait"),
        confidence=conf,
        reasoning=str(parsed.get("reasoning", "")),
        raw_output=raw,
    )


async def _stream_with_timeout(agen, timeout: float, max_timeouts: int = STREAM_MAX_CONSECUTIVE_TIMEOUTS):
    """Consume async generator, yielding chunks as they arrive.

    Runs the generator in a background task and communicates via an asyncio.Queue.
    This decouples the generator's execution from our consumption, so per-chunk
    timeouts never interfere with (cancel/kill) the underlying async generator.
    After max_timeouts consecutive empty-queue timeouts the stream is considered stuck.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _consume() -> None:
        try:
            async for chunk in agen:
                await queue.put(chunk)
        except Exception:
            logger.debug("Background generator consumer exited with error", exc_info=True)
        finally:
            await queue.put(None)  # sentinel: stream ended

    task = asyncio.create_task(_consume())
    consecutive_timeouts = 0
    try:
        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                consecutive_timeouts += 1
                logger.debug("Stream chunk timeout (%d/%d), continuing",
                             consecutive_timeouts, max_timeouts)
                if consecutive_timeouts >= max_timeouts:
                    logger.warning("Stream timed out %d consecutive times, forcing stop",
                                   max_timeouts)
                    break
                continue
            if chunk is None:
                break
            yield chunk
            consecutive_timeouts = 0
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


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


async def _agent_speak_once(agent, config: dict, speak_prompt: str) -> str:
    """Non-streaming fallback used only when streaming produced no text."""
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": speak_prompt}]},
            config,
        )
        return str(result["messages"][-1].content).strip()
    except Exception:
        logger.warning("agent speak fallback failed", exc_info=True)
        return ""


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
        self._interrupt = asyncio.Event()

    def signal_interrupt(self) -> None:
        self._interrupt.set()

    async def run(self) -> list[RoundResult]:
        """Execute the full discussion: intro → rounds → summary."""
        self.status = "running"
        results: list[RoundResult] = []
        start_time = time.time()
        run_started = time.monotonic()

        # Make the room visibly alive before expensive skill loading starts.
        if self.on_event:
            await self.on_event("host_intro_start", {
                "discussion_id": str(self.discussion_id),
                "phase": "preparing_agents",
            })

        # Build agents
        build_started = time.monotonic()
        agents: dict[str, Any] = {}
        agent_configs: dict[str, dict] = {}
        agent_prompts: dict[str, str] = {}
        for name, path in self.agent_skill_paths.items():
            agent, prompt = create_roundtable_agent(path)
            agents[name] = agent
            agent_prompts[name] = prompt
            agent_configs[name] = {"configurable": {"thread_id": f"disc-{self.discussion_id}-{name}"}}
        agent_build_ms = int((time.monotonic() - build_started) * 1000)
        prompt_sizes = {name: len(p) for name, p in agent_prompts.items()}
        logger.info("disc=%s agents_built=%d ms=%s prompt_sizes=%s",
                     self.discussion_id, len(agents), agent_build_ms, prompt_sizes)
        if self.on_event:
            await self.on_event("host_intro_ready", {
                "discussion_id": str(self.discussion_id),
                "agent_count": len(agents),
                "agent_build_ms": agent_build_ms,
                "elapsed_ms": int((time.monotonic() - run_started) * 1000),
            })

        # ── Host intro: streamed LLM opening ──
        intro_prompt = (
            f"你是一位圆桌论坛的主持人。现场有几十位观众，他们是认真来听的。\n\n"
            f"讨论主题：{self.topic}\n"
            f"参与嘉宾：{', '.join(agents.keys())}\n\n"
            f"三段式开场，语气正式得体。每段 {2 + len(agents)} 句话左右，不要过度展开：\n\n"
            f"第一段——引入话题：\n"
            f"今天的话题是什么、为什么值得讨论、为什么是现在。简洁清楚即可。\n\n"
            f"第二段——介绍嘉宾（每位嘉宾1-2句，共{len(agents)}位必须全部提到）：\n"
            f"逐一介绍每位嘉宾——他们是谁、做过什么、和这个话题的关联。\n"
            f"不要替他们预设立场。'{', '.join(agents.keys())}' 共{len(agents)}位。\n\n"
            f"第三段——抛出第一个问题：\n"
            f"自然过渡到提问。1-2句即可。\n\n"
            f"格式要求：\n"
            f"- 段落之间用空行分隔。每段说完换两次行再开始下一段。\n"
            f"- 绝对禁止用括号。任何括号——无论圆括号、方括号——都不允许。\n"
            f"  一旦输出了括号，就是事故。你不是在写舞台剧本。\n"
            f"- 禁止辱骂、审判性语言、段子手、包装词。"
        )
        intro_content = ""
        intro_started = time.monotonic()
        intro_first_token_ms: int | None = None
        if self.on_event:
            batch: list[str] = []
            last_flush = time.monotonic()
            async for token in _stream_with_timeout(
                _call_host_llm_stream(intro_prompt),
                timeout=STREAM_CHUNK_TIMEOUT_SECONDS,
            ):
                if intro_first_token_ms is None:
                    intro_first_token_ms = int((time.monotonic() - intro_started) * 1000)
                intro_content += token
                batch.append(token)
                if time.monotonic() - last_flush >= 0.08:
                    await self.on_event("host_intro_chunk", {
                        "content": "".join(batch),
                        "first_token_ms": intro_first_token_ms,
                    })
                    batch.clear()
                    last_flush = time.monotonic()
            if batch:
                await self.on_event("host_intro_chunk", {
                    "content": "".join(batch),
                    "first_token_ms": intro_first_token_ms,
                })
        if self.on_event:
            await self.on_event("host_intro", {
                "discussion_id": str(self.discussion_id),
                "content": intro_content,
                "agent_build_ms": agent_build_ms,
                "host_first_token_ms": intro_first_token_ms,
                "host_total_ms": int((time.monotonic() - intro_started) * 1000),
            })

        # Main round loop
        while time.time() - start_time < self.duration:
            self.current_round += 1
            round_num = self.current_round

            if self.on_event:
                await self.on_event("round_start", {"round": round_num})

            # Step 1: All agents think — one shared deadline for the whole round.
            context = self._build_think_context(round_num)
            think_started = time.monotonic()
            think_tasks = {
                name: asyncio.create_task(
                    _agent_think_with_metrics(agent_prompts[name], str(uuid.uuid4()), name, context)
                )
                for name in agents
            }
            if self.on_event:
                for name in agents:
                    await self.on_event("agent_think_started", {
                        "agent_name": name,
                        "round": round_num,
                        "timeout_seconds": THINK_TIMEOUT_SECONDS,
                    })
            decisions: list[AgentDecision] = []
            interrupted = False
            done, pending = await asyncio.wait(
                think_tasks.values(),
                timeout=THINK_TIMEOUT_SECONDS,
            )
            if self._interrupt.is_set():
                pending = set(think_tasks.values())
                done = set()
                self._interrupt.clear()
                interrupted = True
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

            for name, task in think_tasks.items():
                if interrupted:
                    break
                if task in done:
                    outcome = task.result()
                else:
                    elapsed_ms = int((time.monotonic() - think_started) * 1000)
                    logger.warning("Agent %s think timeout (%ss), falling back to wait",
                                   name, THINK_TIMEOUT_SECONDS)
                    outcome = ThinkOutcome(
                        decision=AgentDecision(
                            agent_id=str(uuid.uuid4()),
                            agent_name=name,
                            decision="wait",
                            confidence=0.0,
                            reasoning=f"思考超时（{THINK_TIMEOUT_SECONDS}s）",
                            raw_output="",
                        ),
                        elapsed_ms=elapsed_ms,
                        timed_out=True,
                    )

                d = outcome.decision
                decisions.append(d)
                if self.on_event:
                    metric_event = "agent_think_timeout" if outcome.timed_out else "agent_think_finished"
                    await self.on_event(metric_event, {
                        "agent_id": d.agent_id,
                        "agent_name": d.agent_name,
                        "round": round_num,
                        "elapsed_ms": outcome.elapsed_ms,
                        "timeout_seconds": THINK_TIMEOUT_SECONDS,
                        "error": outcome.error,
                    })
                    await self.on_event("agent_think", {
                        "agent_id": d.agent_id,
                        "agent_name": d.agent_name,
                        "round": round_num,
                        "decision": d.decision,
                        "confidence": d.confidence,
                        "reasoning": d.reasoning,
                        "elapsed_ms": outcome.elapsed_ms,
                        "timed_out": outcome.timed_out,
                    })

            if interrupted:
                continue

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
            # Build history: agent messages with truncation, user messages FULL and separate
            _agent_msgs = [m for m in self.messages if not m['speaker'].startswith('观众')]
            _user_msgs = [m for m in self.messages if m['speaker'].startswith('观众')]
            _history_text = _format_history(_agent_msgs[-50:])
            _user_text = ""
            if _user_msgs:
                _user_text = "观众发言:\n"
                for m in _user_msgs[-10:]:
                    _user_text += f"  观众说：{m['content']}\n"
                _user_text += "\n"
            speak_prompt = (
                f"轮到你了。你不是在思考——你是在说话。\n\n"
                f"讨论主题：{self.topic}  第{round_num}轮\n\n"
                f"如果观众在对你说话——先回应他们。让他们感觉到你听到了。\n"
                f"接住前面的讨论——别人说了什么让你想接话？\n"
                f"如果你第一次开口——用一两句介绍自己。\n"
                f"说话的时候想着后面坐着的年轻人。每段说完问自己：一个20岁的人能从这里带走什么？\n"
                f"不要重复自己讲过的故事。\n\n"
                f"刚才说过的：\n{_history_text}\n{_user_text}"
                f"你现在是在发言。写完整的自然段落。绝对禁止输出JSON、禁止输出代码块、禁止输出任何不是自然语言的东西。\n"
            )
            # Stream speak tokens — typewriter effect via on_event callbacks
            full_speech = ""
            speak_started = time.monotonic()
            speak_first_token_ms: int | None = None
            if self.on_event:
                await self.on_event("agent_speak_start", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                    "timeout_seconds": STREAM_CHUNK_TIMEOUT_SECONDS,
                })
            batch = []
            last_flush = time.monotonic()
            async for chunk in _stream_with_timeout(
                _agent_speak_stream(agents[chosen.agent_name], agent_configs[chosen.agent_name], speak_prompt),
                timeout=STREAM_CHUNK_TIMEOUT_SECONDS):
                if speak_first_token_ms is None:
                    speak_first_token_ms = int((time.monotonic() - speak_started) * 1000)
                full_speech += chunk
                batch.append(chunk)
                if time.monotonic() - last_flush >= 0.08:
                    if self.on_event:
                        await self.on_event("agent_speak_chunk", {
                            "agent_id": chosen.agent_id,
                            "agent_name": chosen.agent_name,
                            "round": round_num,
                            "content": "".join(batch),
                            "first_token_ms": speak_first_token_ms,
                        })
                    batch.clear()
                    last_flush = time.monotonic()
            if batch and self.on_event:
                await self.on_event("agent_speak_chunk", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                    "content": "".join(batch),
                    "first_token_ms": speak_first_token_ms,
                })

            used_fallback = False
            if not full_speech.strip():
                logger.warning("Agent %s produced empty speech in round %d; trying fallback",
                               chosen.agent_name, round_num)
                used_fallback = True
                full_speech = await _agent_speak_once(
                    agents[chosen.agent_name],
                    agent_configs[chosen.agent_name],
                    speak_prompt,
                )
                if full_speech and self.on_event:
                    speak_first_token_ms = speak_first_token_ms or int(
                        (time.monotonic() - speak_started) * 1000
                    )
                    await self.on_event("agent_speak_chunk", {
                        "agent_id": chosen.agent_id,
                        "agent_name": chosen.agent_name,
                        "round": round_num,
                        "content": full_speech,
                        "first_token_ms": speak_first_token_ms,
                        "fallback": True,
                    })

            empty_speech = not full_speech.strip()
            if empty_speech:
                full_speech = EMPTY_SPEECH_FALLBACK_TEXT
                if self.on_event:
                    await self.on_event("agent_speak_timeout", {
                        "agent_id": chosen.agent_id,
                        "agent_name": chosen.agent_name,
                        "round": round_num,
                        "content": full_speech,
                        "speak_first_token_ms": speak_first_token_ms,
                        "speak_total_ms": int((time.monotonic() - speak_started) * 1000),
                        "empty_speech": True,
                    })
            if self.on_event:
                await self.on_event("agent_speak_end", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                    "content": full_speech,
                    "speak_first_token_ms": speak_first_token_ms,
                    "speak_total_ms": int((time.monotonic() - speak_started) * 1000),
                    "empty_speech": empty_speech,
                    "fallback": used_fallback,
                })

            self.messages.append({
                "round": round_num,
                "speaker": chosen.agent_name,
                "content": full_speech,
            })

            results.append(RoundResult(
                round_num=round_num,
                decisions=list(decisions),
                speaker_name=chosen.agent_name,
                speaker_agent_id=chosen.agent_id,
                speech_content=full_speech,
                was_forced=was_forced,
            ))

            if self._interrupt.is_set():
                self._interrupt.clear()
                continue

        # ── Host summary: LLM summarizes the full discussion ──
        if self.on_event:
            await self.on_event("host_summary_start", {"total_rounds": self.current_round})

        summary_prompt = (
            f"你是一个真实、有态度的讨论主持人。讨论结束了，做个收尾。\n\n"
            f"讨论主题：{self.topic}\n"
            f"共 {self.current_round} 轮发言。\n\n"
            f"讨论内容：\n"
        )
        for m in self.messages[-50:]:
            summary_prompt += f"  [{m['speaker']}]: {m['content']}\n"
        summary_prompt += (
            "\n收尾要求：\n"
            f"- 这是讨论的总结，必须是总结。简洁，{2 + len(agents)} 段左右。\n"
            f"- 回顾每位嘉宾的核心观点，指出真正的分歧和关键转折。\n"
            f"- 最后感谢嘉宾和观众。\n"
            f"- 段落之间用空行分隔。\n"
            f"- 绝对禁止用括号。任何括号都不允许。\n"
            f"- 禁止：包装词、审判性语言、强行升华、故弄玄虚。\n"
        )

        summary_content = ""
        if self.on_event:
            batch = []
            last_flush = time.monotonic()
            async for token in _stream_with_timeout(_call_host_llm_stream(summary_prompt), timeout=10):
                summary_content += token
                batch.append(token)
                if time.monotonic() - last_flush >= 0.08:
                    await self.on_event("host_summary_chunk", {"content": "".join(batch)})
                    batch.clear()
                    last_flush = time.monotonic()
            if batch:
                await self.on_event("host_summary_chunk", {"content": "".join(batch)})
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
            f"圆桌论坛现场。主持人引导着对话节奏。圆桌后方坐着几十个观众——他们是认真来听的。\n"
            f"讨论主题: {self.topic}\n"
            f"当前为第 {round_num} 轮。\n"
        )
        agent_msgs = [m for m in self.messages if not m['speaker'].startswith('观众')]
        user_msgs = [m for m in self.messages if m['speaker'].startswith('观众')]
        if agent_msgs:
            ctx += "已进行的发言:\n" + _format_history(agent_msgs[-50:], max_len=500)
            ctx += "\n"
        if user_msgs:
            ctx += "以下是观众刚才的发言:\n"
            for m in user_msgs[-10:]:
                ctx += f"  观众说：{m['content']}\n"
            ctx += "\n"
        ctx += (
            "这是圆桌论坛。后面有观众，周围有其他嘉宾。\n"
            "如果有人叫了你的名字——别让别人替你回答。\n"
            "如果你已经回应过了——把话递给还没说的人。\n"
            "如果别人在等你说话——别让他们等太久。\n\n"
            "请决定是否发言。\n"
            "必须严格输出JSON，不要输出其他任何文字。格式：\n"
            '{"decision":"speak"|"wait","confidence":0.76,"reasoning":"碎片化临场念头"}\n'
        )
        return ctx


def _format_history(messages: list[dict], max_len: int = 0) -> str:
    if max_len:
        return "\n".join(f"[{m['speaker']}]: {m['content'][:max_len]}" for m in messages)
    return "\n".join(f"[{m['speaker']}]: {m['content']}" for m in messages)


async def _call_host_llm_stream(prompt: str):
    """Stream host intro/summary — true per-token via ChatOpenAI astream()."""
    llm = _get_host_llm()
    messages = [{"role": "user", "content": prompt}]
    try:
        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
    except Exception:
        logger.warning("host stream failed, falling back to ainvoke")
        result = await llm.ainvoke(messages)
        text = result.content
        for i in range(0, len(text), max(1, len(text) // 10)):
            yield text[i:i + max(1, len(text) // 10)]
            await asyncio.sleep(0.03)


async def _call_host_llm(prompt: str) -> str:
    """Non-streaming fallback for host intro/summary."""
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
    model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
    llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                     temperature=0.8, timeout=30)
    result = await llm.ainvoke(prompt)
    return result.content
