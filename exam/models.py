"""Experiment data models — typed containers for all experimental data."""

from dataclasses import dataclass, field


@dataclass
class DimensionScore:
    """单个维度的评分结果，含 judge 理由。"""

    dimension: str
    score: float  # 1.0–10.0
    reasoning: str = ""


@dataclass
class DiscussionScore:
    """一场讨论的完整 LLM-as-Judge 评分。"""

    model: str
    topic: str
    run: int
    scores: dict[str, float] = field(default_factory=dict)
    reasonings: dict[str, str] = field(default_factory=dict)
    strengths: dict[str, list] = field(default_factory=dict)
    weaknesses: dict[str, list] = field(default_factory=dict)
    overall: float = 0.0


@dataclass
class DiscussionStats:
    """一场讨论的运行时统计。"""

    model: str
    topic: str
    run: int
    total_rounds: int = 0
    forced_speaks: int = 0
    forced_speak_rate: float = 0.0
    avg_confidence: float = 0.0
    avg_speech_length: float = 0.0  # 字符数


@dataclass
class AblationScore:
    """消融实验单条件评分。"""

    condition: str
    run: int
    scores: dict[str, float] = field(default_factory=dict)
    reasonings: dict[str, str] = field(default_factory=dict)
    strengths: dict[str, list] = field(default_factory=dict)
    weaknesses: dict[str, list] = field(default_factory=dict)
    overall: float = 0.0


@dataclass
class AblationStats:
    """消融实验单条件运行时统计。"""

    condition: str
    run: int
    total_rounds: int = 0
    forced_speaks: int = 0
    forced_speak_rate: float = 0.0
