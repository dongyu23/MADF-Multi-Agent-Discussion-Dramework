"""Ablation support — all in exam/, zero changes to agent_engine/.

Provides AblationOrchestrator (subclass of Orchestrator) with component switches:
    enable_intro: bool      — host intro (default True)
    enable_summary: bool    — host summary (default True)
    enable_confidence: bool — confidence-based arbitration (False → round-robin)
    enable_jitter: bool     — deterministic jitter on confidence scores
    enable_rules: bool      — 三条铁律 in system prompt

Also provides factory/think patching so ablation flags propagate without
touching the original agent_engine source.
"""

import asyncio
import hashlib
import logging
import os
import random
import re
import time
import uuid
from collections.abc import Callable
from typing import Any

from langchain_openai import ChatOpenAI

from agent_engine.discussion.orchestrator import (
    Orchestrator,
    AgentDecision,
    RoundResult,
    _stream_with_timeout,
    _call_host_llm_stream,
    _agent_speak_stream,
    _format_history,
)
from agent_engine.discussion.factory import create_roundtable_agent as _original_create_agent
from agent_engine.discussion.factory import DISCUSSION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ── Factory patch: strip 三条铁律 when enable_rules=False ──

def _make_no_rules_prompt(skill_name: str) -> str:
    """DISCUSSION_SYSTEM_PROMPT with 三条铁律 removed."""
    import re
    prompt = DISCUSSION_SYSTEM_PROMPT
    prompt = re.sub(
        r'## 三条铁律\n\n.*?(?=## 思考)',
        '## 思考',
        prompt,
        flags=re.DOTALL,
    )
    return prompt.replace("{skill_name}", skill_name)


# ── Think patch: skip jitter when enable_jitter=False ──

def _make_no_jitter_think(original_think_fn):
    """Wrap _agent_think_fast to optionally skip jitter."""
    async def wrapper(system_prompt: str, agent_id: str, agent_name: str,
                      context: str, apply_jitter: bool = True) -> AgentDecision:
        if apply_jitter:
            return await original_think_fn(system_prompt, agent_id, agent_name, context)
        # Call original but patch out the jitter block
        # We reimplement the core logic without jitter
        from agent_engine.discussion.orchestrator import _get_think_llm, _extract_decision
        llm = _get_think_llm()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]
        result = await llm.ainvoke(messages)
        raw = result.content
        parsed = _extract_decision(raw)
        if parsed is None:
            parsed = {"decision": "wait", "confidence": 0.0, "reasoning": "无法解析思考输出"}
        conf = round(float(parsed.get("confidence", 0.0)), 2)
        return AgentDecision(
            agent_id=agent_id, agent_name=agent_name,
            decision=parsed.get("decision", "wait"), confidence=conf,
            reasoning=str(parsed.get("reasoning", "")), raw_output=raw,
        )
    return wrapper


# ── Ablation Orchestrator ──

class AblationOrchestrator(Orchestrator):
    """Orchestrator with component-level ablation switches.

    All switches default to True (full MADF system).  Set to False to ablate.
    """

    def __init__(
        self,
        *args,
        enable_intro: bool = True,
        enable_summary: bool = True,
        enable_confidence: bool = True,
        enable_jitter: bool = True,
        enable_rules: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._abl_intro = enable_intro
        self._abl_summary = enable_summary
        self._abl_confidence = enable_confidence
        self._abl_jitter = enable_jitter
        self._abl_rules = enable_rules
        self._rr_index = 0  # round-robin pointer

    async def run(self) -> list[RoundResult]:
        """Execute discussion with ablation switches applied.

        Identical to Orchestrator.run() except for the ablation control points
        marked with ── ABLATION ── comments.
        """
        self.status = "running"
        results: list[RoundResult] = []
        start_time = time.time()

        # Build agents — with ablation-controlled factory
        agents: dict[str, Any] = {}
        agent_configs: dict[str, dict] = {}
        agent_prompts: dict[str, str] = {}
        for name, path in self.agent_skill_paths.items():
            agent, prompt = self._create_agent_ablated(path)
            agents[name] = agent
            agent_prompts[name] = prompt
            agent_configs[name] = {"configurable": {"thread_id": f"disc-{self.discussion_id}-{name}"}}

        # ── ABLATION: Host intro ──
        if self._abl_intro and self.on_event:
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
            batch: list[str] = []
            last_flush = time.monotonic()
            async for token in _stream_with_timeout(_call_host_llm_stream(intro_prompt), timeout=10):
                intro_content += token
                batch.append(token)
                if time.monotonic() - last_flush >= 0.08:
                    await self.on_event("host_intro_chunk", {"content": "".join(batch)})
                    batch.clear()
                    last_flush = time.monotonic()
            if batch:
                await self.on_event("host_intro_chunk", {"content": "".join(batch)})
            await self.on_event("host_intro", {
                "discussion_id": str(self.discussion_id), "content": intro_content,
            })

        # ── Main round loop ──
        while time.time() - start_time < self.duration:
            self.current_round += 1
            round_num = self.current_round

            if self.on_event:
                await self.on_event("round_start", {"round": round_num})

            context = self._build_think_context(round_num)
            think_tasks = {
                name: asyncio.create_task(
                    self._think_ablated(agent_prompts[name], str(uuid.uuid4()), name, context)
                )
                for name in agents
            }
            decisions: list[AgentDecision] = []
            interrupted = False
            for name, task in think_tasks.items():
                if self._interrupt.is_set():
                    for t in think_tasks.values():
                        if not t.done():
                            t.cancel()
                    for t in think_tasks.values():
                        try:
                            await t
                        except (asyncio.CancelledError, Exception):
                            pass
                    self._interrupt.clear()
                    interrupted = True
                    break
                is_timeout = False
                try:
                    d = await asyncio.wait_for(task, timeout=30)
                except asyncio.TimeoutError:
                    logger.warning("Agent %s think timeout (30s), falling back to wait", name)
                    is_timeout = True
                    d = AgentDecision(
                        agent_id=str(uuid.uuid4()), agent_name=name,
                        decision="wait", confidence=0.0,
                        reasoning="思考超时，降级为等待", raw_output="",
                    )
                    if self.on_event:
                        await self.on_event("agent_think", {
                            "agent_id": d.agent_id, "agent_name": name,
                            "round": round_num, "decision": "wait",
                            "confidence": 0.0, "reasoning": "思考超时（30s）",
                        })
                decisions.append(d)
                if self.on_event and not is_timeout:
                    await self.on_event("agent_think", {
                        "agent_id": d.agent_id, "agent_name": d.agent_name,
                        "round": round_num, "decision": d.decision,
                        "confidence": d.confidence, "reasoning": d.reasoning,
                    })

            if interrupted:
                continue

            # ── ABLATION: Speaker selection ──
            if self._abl_confidence:
                speakers = [d for d in decisions if d.decision == "speak"]
                if speakers:
                    chosen = max(speakers, key=lambda d: d.confidence)
                    was_forced = False
                else:
                    chosen = random.choice(decisions)
                    was_forced = True
                    logger.info("Round %d: all silent, forced speaker %s", round_num, chosen.agent_name)
            else:
                agent_names = list(agents.keys())
                chosen_name = agent_names[self._rr_index % len(agent_names)]
                self._rr_index += 1
                chosen = next(d for d in decisions if d.agent_name == chosen_name)
                was_forced = False

            # Step 3: Speaker speaks
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
            full_speech = ""
            if self.on_event:
                await self.on_event("agent_speak_start", {
                    "agent_id": chosen.agent_id, "agent_name": chosen.agent_name,
                    "round": round_num,
                })
            batch_tokens: list[str] = []
            last_flush = time.monotonic()
            async for chunk in _stream_with_timeout(
                _agent_speak_stream(agents[chosen.agent_name], agent_configs[chosen.agent_name], speak_prompt),
                timeout=10,
            ):
                full_speech += chunk
                batch_tokens.append(chunk)
                if time.monotonic() - last_flush >= 0.08:
                    if self.on_event:
                        await self.on_event("agent_speak_chunk", {
                            "agent_id": chosen.agent_id, "agent_name": chosen.agent_name,
                            "round": round_num, "content": "".join(batch_tokens),
                        })
                    batch_tokens.clear()
                    last_flush = time.monotonic()
            if batch_tokens and self.on_event:
                await self.on_event("agent_speak_chunk", {
                    "agent_id": chosen.agent_id, "agent_name": chosen.agent_name,
                    "round": round_num, "content": "".join(batch_tokens),
                })
            if self.on_event:
                await self.on_event("agent_speak_end", {
                    "agent_id": chosen.agent_id, "agent_name": chosen.agent_name,
                    "round": round_num, "content": full_speech,
                })

            self.messages.append({
                "round": round_num, "speaker": chosen.agent_name,
                "content": full_speech,
            })
            results.append(RoundResult(
                round_num=round_num, decisions=list(decisions),
                speaker_name=chosen.agent_name, speaker_agent_id=chosen.agent_id,
                speech_content=full_speech, was_forced=was_forced,
            ))

            if self._interrupt.is_set():
                self._interrupt.clear()
                continue

        # ── ABLATION: Host summary ──
        if self._abl_summary:
            if self.on_event:
                await self.on_event("host_summary_start", {"total_rounds": self.current_round})

            summary_prompt = (
                f"你是一个真实、有态度的讨论主持人。讨论结束了，做个收尾。\n\n"
                f"讨论主题：{self.topic}\n"
                f"共 {self.current_round} 轮发言。\n\n讨论内容：\n"
            )
            for m in self.messages[-50:]:
                summary_prompt += f"  [{m['speaker']}]: {m['content']}\n"
            summary_prompt += (
                f"\n收尾要求：\n"
                f"- 这是讨论的总结，必须是总结。简洁，{2 + len(agents)} 段左右。\n"
                f"- 回顾每位嘉宾的核心观点，指出真正的分歧和关键转折。\n"
                f"- 最后感谢嘉宾和观众。\n"
                f"- 段落之间用空行分隔。\n"
                f"- 绝对禁止用括号。任何括号都不允许。\n"
                f"- 禁止：包装词、审判性语言、强行升华、故弄玄虚。\n"
            )

            summary_content = ""
            batch_s: list[str] = []
            last_flush = time.monotonic()
            async for token in _stream_with_timeout(_call_host_llm_stream(summary_prompt), timeout=10):
                summary_content += token
                batch_s.append(token)
                if time.monotonic() - last_flush >= 0.08:
                    await self.on_event("host_summary_chunk", {"content": "".join(batch_s)})
                    batch_s.clear()
                    last_flush = time.monotonic()
            if batch_s:
                await self.on_event("host_summary_chunk", {"content": "".join(batch_s)})
            await self.on_event("host_summary", {
                "discussion_id": str(self.discussion_id), "total_rounds": self.current_round,
                "content": summary_content,
            })
        await self.on_event("discussion_end", {
            "discussion_id": str(self.discussion_id), "total_rounds": self.current_round,
        })

        self.status = "completed"
        return results

    def _create_agent_ablated(self, skill_path: str):
        """Create agent with ablation-controlled factory (rules on/off)."""
        if not self._abl_rules:
            # Strip rules from prompt
            from pathlib import Path
            import re
            skill_dir = Path(skill_path).resolve()
            skill_name = skill_dir.name.replace("-perspective", "")
            source_dir = str(skill_dir.resolve())
            from deepagents.backends.filesystem import FilesystemBackend
            backend = FilesystemBackend(root_dir="/", virtual_mode=True)

            skill_files: list[str] = []
            for md in sorted(skill_dir.rglob("*.md")):
                try:
                    skill_files.append(f"### {md.relative_to(skill_dir)}\n\n{md.read_text(encoding='utf-8')}")
                except Exception:
                    pass
            skill_content = "\n\n---\n\n".join(skill_files)

            prompt = _make_no_rules_prompt(skill_name)
            prompt += f"\n\n## 你的技能文件\n\n{skill_content}"

            from deepagents import create_deep_agent
            from agent_engine.discussion.factory import _make_model
            agent = create_deep_agent(
                model=_make_model(),
                system_prompt=prompt,
                skills=[source_dir],
                backend=backend,
            )
            return agent, prompt
        else:
            return _original_create_agent(skill_path)

    def _think_ablated(self, system_prompt: str, agent_id: str, agent_name: str, context: str):
        """Think with ablation-controlled jitter."""
        if self._abl_jitter:
            from agent_engine.discussion.orchestrator import _agent_think_fast
            return _agent_think_fast(system_prompt, agent_id, agent_name, context)
        else:
            return _no_jitter_think(system_prompt, agent_id, agent_name, context)

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


async def _no_jitter_think(system_prompt: str, agent_id: str, agent_name: str, context: str) -> AgentDecision:
    """Think without jitter — identical to _agent_think_fast but no deterministic jitter."""
    from agent_engine.discussion.orchestrator import _get_think_llm, _extract_decision
    llm = _get_think_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    result = await llm.ainvoke(messages)
    raw = result.content
    parsed = _extract_decision(raw)
    if parsed is None:
        parsed = {"decision": "wait", "confidence": 0.0, "reasoning": "无法解析思考输出"}
    conf = round(float(parsed.get("confidence", 0.0)), 2)
    return AgentDecision(
        agent_id=agent_id, agent_name=agent_name,
        decision=parsed.get("decision", "wait"), confidence=conf,
        reasoning=str(parsed.get("reasoning", "")), raw_output=raw,
    )
