"""LLM-as-Judge final — two-stage scoring with pre-computed turn-count penalties.

v4 philosophy: A good discussion has UNEVEN participation. The expert on the
current sub-topic speaks more. Others speak less or stay silent. Equal turn
counts (A→B→C→A→B→C) are evidence of artificial scheduling, not good discussion.

Key design principle: the judge must understand that confidence arbitration
produces BETTER discussions by letting the most relevant agent speak — even
if that means some agents speak less. The mechanism's value is in creating
organic, expertise-driven dynamics, not equal airtime.
"""

import json, logging
from langchain_openai import ChatOpenAI
from exam.models import DiscussionScore
from exam.config import JUDGE_MODEL, JUDGE_TEMPERATURE, SCORING_DIMENSIONS

logger = logging.getLogger(__name__)

JUDGE_INTRO = """你是严格的圆桌讨论评审官。讨论上方已标注预计算的发言次数统计，直接使用。

**发言次数与评分上限的硬性规则：**
- 只有1个发言者（单智能体独白）：
  coherence上限=5（无人可互动），engagement=1（零互动），depth上限=7（没有他人视角补充）。
  但 consistency 和 relevance 不受影响。
- 所有Agent发言次数完全相等（如4-4-4或5-5-5）：
  机械轮转铁证。coherence和engagement上限=5分。
- 最大差距≤1（如4-4-3或5-5-4）：
  高度可疑。coherence和engagement上限=6分。
- 最大差距≥3：
  自然讨论特征。按内容质量正常评分。

**评分步骤：**
第1步：列出2-3个具体的闪光时刻和2-3个具体的缺陷时刻。引用原句或具体行为。
第2步：遵守上述硬性上限规则，给出1-10的整数分。上限是硬性的——即使内容再好，也不能突破。

输出严格JSON：{"strengths": [...], "weaknesses": [...], "score": <整数>, "reasoning": "..."}

讨论内容：
{discussion}"""

JUDGE_PROMPTS: dict[str, str] = {
    "coherence": """仅评连贯性——发言衔接是否自然。遵守上方硬性上限规则。锚定：9=内容驱动顺序不均, 7=大体自然偶有机械感, 5=明显均等轮转各说各话, 3=碎片化, 1=完全碎片。""" + JUDGE_INTRO,

    "depth": """仅评洞见深度——是否有新信息、独特视角、具体案例。如果在非专业领域被迫发言，内容是空洞的。锚定：9=只有这个人才能说出的洞察, 7=不错但有部分填充, 5=已知观点重排, 3=多数填充, 1=空洞。""" + JUDGE_INTRO,

    "consistency": """仅评角色一致性——发言是否符合角色语言风格和思维模式。锚定：9=标志性表达一眼认出, 7=特征明显偶有滑落, 5=可互换, 3=多处不符, 1=完全走形。""" + JUDGE_INTRO,

    "engagement": """仅评参与质量——是否真正碰撞而非轮流说话。遵守上方硬性上限规则。锚定：9=实质性争论+反驳+修正, 7=基本交锋但表面, 5=流水线模式或均等轮转, 3=几乎各说各的, 1=零互动。""" + JUDGE_INTRO,

    "relevance": """仅评主题相关性——是否紧扣主题无偏离。锚定：9=零冗余零偏离, 7=基本围绕偶有偏离, 5=明显偏离段落, 3=多处无关, 1=完全跑题。""" + JUDGE_INTRO,
}


def _build_discussion_text(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        speaker = m.get("speaker", "Unknown")
        content = m.get("content", "")
        lines.append(f"[{speaker}]: {content}\n")

    # Pre-compute turn distribution
    agent_msgs = [m for m in messages if m.get("speaker", "") != "主持人"]
    from collections import Counter
    counts = Counter(m["speaker"] for m in agent_msgs)
    count_vals = list(counts.values())
    max_gap = max(count_vals) - min(count_vals) if len(count_vals) >= 2 else 999

    transcript = "\n".join(lines)

    # Inject turn stats at the top
    stats_header = f"【发言次数统计（预计算，直接使用）】\n"
    for name, cnt in counts.most_common():
        stats_header += f"  {name}: {cnt}次\n"
    stats_header += f"  最大差距 = {max_gap}（{max_gap}≤1→机械调度，{max_gap}≥3→自然讨论）\n\n"

    return stats_header + transcript, counts, max_gap


def _parse_judge_response(raw: str) -> tuple[float, str, list[str], list[str]]:
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
        score = float(data.get("score", 5))
        reasoning = str(data.get("reasoning", ""))
        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        if isinstance(strengths, str): strengths = [strengths]
        if isinstance(weaknesses, str): weaknesses = [weaknesses]
        return min(10.0, max(1.0, score)), reasoning, strengths, weaknesses
    except (json.JSONDecodeError, ValueError, TypeError):
        import re
        m_score = re.search(r'"score"\s*:\s*(\d+)', raw)
        score = float(m_score.group(1)) if m_score else 5.0
        return min(10.0, max(1.0, score)), "parse error", [], []


async def judge_discussion(discussion_messages: list[dict], topic: str) -> DiscussionScore:
    transcript, turn_counts, max_gap = _build_discussion_text(discussion_messages)
    scores, reasonings = {}, {}
    all_strengths, all_weaknesses = {}, {}

    from backend.config import settings

    llm = ChatOpenAI(
        model=JUDGE_MODEL,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_api_base,
        temperature=JUDGE_TEMPERATURE,
        timeout=60,
    )

    for dim in SCORING_DIMENSIONS:
        prompt = JUDGE_PROMPTS[dim].replace("{discussion}", transcript)
        try:
            result = await llm.ainvoke([{"role": "user", "content": prompt}])
            score, reasoning, strengths, weaknesses = _parse_judge_response(result.content)
            scores[dim] = score
            reasonings[dim] = reasoning
            all_strengths[dim] = strengths
            all_weaknesses[dim] = weaknesses
        except Exception as exc:
            logger.error("Judge failed for dimension %s: %s", dim, exc)
            scores[dim] = 5.0
            reasonings[dim] = f"error: {exc}"
            all_strengths[dim] = []
            all_weaknesses[dim] = [str(exc)]

    overall = sum(scores[d] * 0.2 for d in SCORING_DIMENSIONS)
    return DiscussionScore(
        model="", topic=topic, run=0,
        scores=scores, reasonings=reasonings,
        strengths=all_strengths, weaknesses=all_weaknesses,
        overall=overall,
    )
