"""Experiment configuration — all tunable parameters in one place."""

from dataclasses import dataclass, field

# ── 对比实验：参测模型 ──
COMPARISON_MODELS = [
    "gpt-4o",
    "claude-sonnet-4-6",
    "deepseek-v3",
    "qwen-max",
    "gpt-4o-mini",
]

# ── 消融实验：条件标签 ──
ABLATION_CONDITIONS = {
    "A": "完整系统 (Baseline)",
    "B": "无确信度仲裁",
    "C": "无 Jitter",
    "D": "无主持人开场",
    "E": "无主持人总结",
    "F": "无铁律约束",
}

# ── 讨论主题 ──
COMPARISON_TOPICS = [
    "AI 创业公司应该追求技术领先还是商业落地速度？",
    "在信息过载时代，年轻人最需要培养的核心能力是什么？",
    "教育的本质是传授知识还是培养思维方式？",
]

ABLATION_TOPIC = "AI 创业公司应该追求技术领先还是商业落地速度？"

# ── 固定角色组合 ──
CHARACTERS = ["Jobs", "Feynman", "Munger"]

# ── 讨论参数 ──
DISCUSSION_DURATION = 180  # 秒
REPETITIONS = 3  # 每条件重复次数
ABLATION_REPETITIONS = 5

# ── LLM-as-Judge 配置 ──
JUDGE_MODEL = "step-3.6"  # 裁判模型 (唯一可用模型)
JUDGE_TEMPERATURE = 0.1

# ── 评分维度 ──
SCORING_DIMENSIONS = [
    "coherence",     # 连贯性
    "depth",         # 洞见深度
    "consistency",   # 角色一致性
    "engagement",    # 参与质量
    "relevance",     # 主题相关性
]

DIMENSION_LABELS_ZH = {
    "coherence": "连贯性",
    "depth": "洞见深度",
    "consistency": "角色一致性",
    "engagement": "参与质量",
    "relevance": "主题相关性",
}

DIMENSION_WEIGHTS = {d: 0.2 for d in SCORING_DIMENSIONS}  # 等权

# ── 图表配置 ──
CHART_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c"]
MODEL_COLORS = dict(zip(COMPARISON_MODELS, CHART_COLORS))
ABLATION_COLORS = {
    "A": "#2563eb",
    "B": "#dc2626",
    "C": "#f59e0b",
    "D": "#8b5cf6",
    "E": "#10b981",
    "F": "#ef4444",
}

DPI = 150
FONT_FAMILY = "sans-serif"
