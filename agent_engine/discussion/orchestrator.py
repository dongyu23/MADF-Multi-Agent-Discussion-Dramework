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


def _get_host_llm() -> ChatOpenAI:
    global _host_llm
    if _host_llm is None:
        api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
        model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
        _host_llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                               temperature=0.8, timeout=30, streaming=True)
    return _host_llm




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


def _sanitize_json(text: str) -> str:
    """Repair common LLM JSON mistakes before parsing."""
    # Remove trailing commas before } or ] (most common LLM error)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Fix single-quoted keys/values: replace ' with " for JSON syntax
    # Only within JSON-like braces to avoid damaging prose
    text = re.sub(r"'([^']*)':", r'"\1":', text)
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
    return text


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
    raw = result["messages"][-1].content
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

        # ── Host intro: streamed LLM opening ──
        if self.on_event:
            await self.on_event("host_intro_start", {"discussion_id": str(self.discussion_id)})

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
        if self.on_event:
            batch: list[str] = []
            last_flush = time.monotonic()
            async for token in _call_host_llm_stream(intro_prompt):
                intro_content += token
                batch.append(token)
                if time.monotonic() - last_flush >= 0.08:
                    await self.on_event("host_intro_chunk", {"content": "".join(batch)})
                    batch.clear()
                    last_flush = time.monotonic()
            if batch:
                await self.on_event("host_intro_chunk", {"content": "".join(batch)})
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
                f"轮到你了。现在是发言模式——不是思考模式。\n\n"
                f"讨论主题：{self.topic}  第{round_num}轮\n\n"
                f"## 切题锚点（每次发言前后自检）\n"
                f"你说的每一段话都必须能直接回答：这和讨论主题有什么关系？\n"
                f"如果你的故事需要绕三个弯才能联系到主题——删掉它，直接说主题。\n\n"
                f"## 观众价值（发言结束前自检）\n"
                f"你说话的时候，后面坐着几十个年轻人。他们不是来听传奇的——\n"
                f"他们是来做选择的。你的每一段话结束时问自己：\n"
                f"「一个20岁的人能从这里带走什么？」如果答案模糊，加一句总结。\n\n"
                f"## 介绍自己（仅第一次发言）\n"
                f"如果这是你本场第一次开口——用一两句话简单介绍你是谁、做什么的，\n"
                f"让观众知道你凭什么坐在这里。但不要罗列成就——说你是做什么的、为什么关心这个话题。\n\n"
                f"## 回应对话\n"
                f"你不是在独白。先快速回应前面的讨论——别人说了什么让你想接话？\n"
                f"是补充、是纠正、还是换个角度？让观众看到对话的脉络。\n\n"
                f"刚才说过的：\n{_format_history(self.messages[-50:])}\n\n"
                f"## 发言要求（按重要性排序）\n\n"
                f"0. 不重复。如果你发现自己又在讲之前说过的故事或案例——立刻停下来。\n"
                f"   每个经历故事在一场讨论中最多只能讲一次。用一句话总结旧故事，\n"
                f"   然后马上转到新角度。如果找不到新角度——缩短发言，让给别人。\n"
                f"1. 切题。如果发现自己在说和主题无关的故事——立刻停下来，拉回主题。\n"
                f"1. 事实边界。你唯一的事实来源是你的技能文件。\n"
                f"   输出任何数字前, 必须在技能文件中找到确切出处。没有出处 -- 不准说。\n"
                f"   技能文件说「惊人」-- 你就说「惊人」, 不要自己翻译成「1000倍」。\n"
                f"2. 术语即解释。每提到一个专业概念, 立刻用一两句大白话解释。\n"
                f"   标准: 一个高中生能听懂。\n"
                f"3. 写完整段落。不要用短句分行来模拟语气 -- 信息会碎掉。\n"
                f"4. 陈述, 不反问。分享困境, 不是分享传奇。观众不需要知道你多成功 --\n"
                f"   他们想知道你犯过什么错、怎么想的、学到了什么。\n\n"
                f"绝对不要输出JSON。绝对不要输出括号动作提示。"
            )
            # Stream speak tokens — typewriter effect via on_event callbacks
            full_speech = ""
            if self.on_event:
                await self.on_event("agent_speak_start", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                })
            batch = []
            last_flush = time.monotonic()
            async for chunk in _agent_speak_stream(agents[chosen.agent_name], agent_configs[chosen.agent_name], speak_prompt):
                full_speech += chunk
                batch.append(chunk)
                if time.monotonic() - last_flush >= 0.08:
                    if self.on_event:
                        await self.on_event("agent_speak_chunk", {
                            "agent_id": chosen.agent_id,
                            "agent_name": chosen.agent_name,
                            "round": round_num,
                            "content": "".join(batch),
                        })
                    batch.clear()
                    last_flush = time.monotonic()
            if batch and self.on_event:
                await self.on_event("agent_speak_chunk", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                    "content": "".join(batch),
                })
            if self.on_event:
                await self.on_event("agent_speak_end", {
                    "agent_id": chosen.agent_id,
                    "agent_name": chosen.agent_name,
                    "round": round_num,
                    "content": full_speech,
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
            summary_prompt += f"  [{m['speaker']}]: {m['content'][:250]}\n"
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
            async for token in _call_host_llm_stream(summary_prompt):
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
        if self.messages:
            ctx += "已进行的发言:\n" + _format_history(self.messages[-50:])
            ctx += "\n"
        ctx += (
            "轮到你决定是否发言。\n\n"
            "## 切题检查（每次思考必做）\n"
            f"本场讨论的唯一主题：{self.topic}\n"
            "你要说的话必须直接回答这个问题。检查方法：\n"
            "如果你的故事去掉三句话就没法联系到主题——那不是切题，是跑题。不要强行类比。\n\n"
            "## 重复检查\n"
            "前面有人说过你想说的观点了吗？如果只是换个说法说同一件事——不要发言。\n"
            "如果你已经在本场发过两次以上的言——只有当你手上有全新的、前面没出现过的角度时，才考虑发言。\n\n"
            "## 判断标准\n"
            "不是你有没有想说的话——你永远有想说的话。\n"
            "是你能不能给讨论带来之前没有的东西？\n\n"
            "## 置信度\n"
            "恰好两位小数，均匀分布在0.00到1.00之间。\n"
            "脑中想一个0到100之间的随机整数，除以100。\n"
            "禁止用0.30、0.50、0.70、0.80这类整齐数字。\n"
            "刚发过言时confidence偏低（但仍是随机小数）。\n\n"
            "必须严格输出JSON，不要输出其他任何文字。格式：\n"
            '{"decision":"speak"|"wait","confidence":0.76,"reasoning":"碎片化临场念头"}\n'
        )
        return ctx


def _format_history(messages: list[dict]) -> str:
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
