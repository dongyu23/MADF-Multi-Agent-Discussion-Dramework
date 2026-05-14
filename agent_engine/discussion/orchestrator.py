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

        # ── Host intro: streamed LLM opening ──
        if self.on_event:
            await self.on_event("host_intro_start", {"discussion_id": str(self.discussion_id)})

        intro_prompt = (
            f"你是一个长期关注科技与社会议题的讨论主持人。现在开始一场讨论。\n\n"
            f"讨论主题：{self.topic}\n"
            f"参与嘉宾：{', '.join(agents.keys())}\n\n"
            f"你的目标不是输出情绪，不是制造金句。而是用半步挑衅，把嘉宾逼进真实表达。\n\n"
            f"核心原则：\n"
            f"- 制造'高压感'，不是'高攻击性'。压力来自问题本身，不来自辱骂密度。\n"
            f"- 留白。停顿。半句质疑。很轻地捅一下就够了。\n"
            f"- 提问要短，要落在具体现实上——用真实社会情绪、具体利益冲突来提问。\n"
            f"- 不要替观众发泄情绪。立场不要太明显。给嘉宾留表达空间。\n"
            f"- 禁止：辱骂、人身攻击、审判性语言（如'巨婴''恶心''把自己当上帝''数据奴隶''脑子给连废了'）。\n"
            f"- 禁止：强行造梗、金句密度过高、'段子手'感。主持人不是表演者。\n"
            f"- 禁止：'跨时代''顶级阵容''人类命运''科技与人文''文明高度'等包装词。\n"
            f"- 禁止：替观众发泄情绪。主持人不是观众嘴替。\n"
            f"- 禁止：文学化修辞过度（如'把人类驯化成离不开屏幕的巨婴'）。\n"
            f"- 不介绍嘉宾，不定规则。3-5句话。直接开始。\n\n"
            f"类似这样的提问风格：\n"
            f"-'黄总，现在很多人觉得AI越强你们越赚钱。那你们真有动力去限制AI吗？'\n"
            f"-'乔布斯，今天很多家长已经开始后悔让孩子这么早接触智能手机了。硅谷当年低估了这件事吗？'\n"
            f"-'爱因斯坦，当年核武器失控过一次。人类凭什么相信这次不会？'"
        )
        intro_content = ""
        if self.on_event:
            async for token in _call_host_llm_stream(intro_prompt):
                intro_content += token
                await self.on_event("host_intro_chunk", {
                    "content": token,
                })
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
                f"现在轮到你发言。你起身，双手轻触桌面，直视着你的讨论同伴。\n"
                f"讨论主题: {self.topic}\n第 {round_num} 轮。\n"
                f"{_format_history(self.messages[-5:])}\n\n"
                f"你不是在发表演讲。你是在一个真实论坛里说话——直接说话。\n\n"
                f"核心：\n"
                f"- 不追求'完整正确'。不强行平衡观点。不最后升华价值观。不总结成'人类应该如何'。\n"
                f"- 大量使用：真实经历、具体数字、行业内幕、产品细节、失败案例、个人判断、对未来的赌注。\n"
                f"- 信息密度要高。每一个观点都落在具体事物上。\n\n"
                f"允许：打断问题前提、吐槽问题本身、对其他嘉宾不认同、情绪上来、不完整句子、临时改变方向、刻薄、狂妄、跑题。\n\n"
                f"禁止AI味句式：'真正的问题是''归根结底''我们应该思考''关键在于''从某种意义上''这不是X而是Y''辩证看待''既要又要''双刃剑'。\n\n"
                f"不要说抽象概念。给它落地——不要说'AI会带来新可能性'，说'去年一个团队用大模型把蛋白质筛选从几个月压到几天'。\n\n"
                f"不输出JSON。直接说话。像播客争论、深夜长谈、行业内行聊天那样说话。"
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
        for m in self.messages[-15:]:
            summary_prompt += f"  [{m['speaker']}]: {m['content'][:250]}\n"
        summary_prompt += (
            "\n收尾要求：\n"
            f"- 不要'央视式总结'——不替观众概括正确观点，不制造虚假共识。\n"
            f"- 不要审判嘉宾（'谁在回避''谁在表演'）。让听众自己判断。\n"
            f"- 简短点出一个刚才最值得追问但没有展开的角度。\n"
            f"- 提出一个悬而未决的问题，不画句号。\n"
            f"- 2-3句话。口语化。像讨论结束后随手记下的一点感想。\n"
            f"- 禁止：'跨时代''人类命运''科技与人文''文明高度'。\n"
            f"- 禁止：审判性语言、替观众发泄情绪、强行升华。"
        )

        summary_content = ""
        if self.on_event:
            async for token in _call_host_llm_stream(summary_prompt):
                summary_content += token
                await self.on_event("host_summary_chunk", {
                    "content": token,
                })
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
            f"你正在参加一场真实、紧张的圆桌论坛。现场随时可能被打断、被质疑、被挑衅。\n"
            f"环境：深色胡桃木圆桌，暖黄灯光，远处城市夜景透过落地窗可见。\n"
            f"讨论主题: {self.topic}\n"
            f"当前为第 {round_num} 轮。\n"
        )
        if self.messages:
            ctx += "已进行的发言:\n" + _format_history(self.messages[-10:])
            ctx += "\n"
        ctx += (
            "现在轮到你决定是否发言。\n\n"
            "你不是在'选择是否展示观点'。你是在判断——\n"
            "这个现场，你是不是必须开口。\n\n"
            "如果你被冒犯了、有反驳欲、突然想到一个真实案例、或者对前面某句话极度不认同——选 speak。\n"
            "如果你只是'也这么觉得'、只是想做一点补充——选 wait。没必要。\n"
            "如果你觉得前面的人在表演、在回避、在说大词包装——你更应该开口。\n\n"
            "内部思考不要分析自己。不要出现：'我有独特视角'、'这个话题与我经历相关'、'我可以从XX角度回答'。\n"
            "内部思考必须是碎片化、情绪化的临场念头。像脑内闪过的冲动——\n"
            "'他跑题了''这数字是错的''我要讲一个他不敢听的事实''主持人就是想听这句吧'。\n\n"
            "输出JSON: {\"decision\":\"speak\"|\"wait\",\"confidence\":0.76,\"reasoning\":\"碎片化临场念头\"}"
        )
        return ctx


def _format_history(messages: list[dict]) -> str:
    return "\n".join(f"[{m['speaker']}]: {m['content'][:300]}" for m in messages)


async def _call_host_llm_stream(prompt: str):
    """Stream host intro/summary via per-token SSE events using ChatOpenAI."""
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base = settings.llm_api_base or os.getenv("LLM_API_BASE") or os.getenv("OPENAI_API_BASE")
    model = settings.llm_model or os.getenv("LLM_MODEL") or "gpt-4o"
    llm = ChatOpenAI(model=model, openai_api_key=api_key, openai_api_base=base,
                     temperature=0.8, timeout=30, streaming=True)
    try:
        async for event in llm.astream_events(prompt, version="v2"):
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
    except Exception:
        logger.warning("host stream failed, falling back to ainvoke")
        result = await llm.ainvoke(prompt)
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
