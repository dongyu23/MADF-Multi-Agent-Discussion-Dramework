"""Statistical analysis for experiment results."""

import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np

from exam.config import SCORING_DIMENSIONS, DIMENSION_LABELS_ZH

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def aggregate_baseline(data: dict) -> dict:
    """Aggregate baseline results by topic: mean, std per dimension."""
    results = data["results"]
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        if "error" in r:
            continue
        by_topic[r["topic"]].append(r)

    aggregated: dict = {"topics": {}, "overall": {}}

    all_scores: dict[str, list[float]] = {d: [] for d in SCORING_DIMENSIONS}
    all_rounds: list[int] = []
    all_forced: list[float] = []
    all_text_len: list[float] = []

    for topic, items in by_topic.items():
        t_scores: dict[str, list[float]] = {d: [] for d in SCORING_DIMENSIONS}
        t_overalls: list[float] = []
        t_rounds: list[int] = []
        t_forced: list[float] = []

        for item in items:
            s = item.get("scores", {})
            for d in SCORING_DIMENSIONS:
                t_scores[d].append(float(s.get(d, 5)))
                all_scores[d].append(float(s.get(d, 5)))
            ov = float(item.get("overall", sum(float(s.get(d, 5)) * 0.2 for d in SCORING_DIMENSIONS)))
            t_overalls.append(ov)
            stats = item.get("stats", {})
            t_rounds.append(int(stats.get("total_rounds", 0)))
            t_forced.append(float(stats.get("forced_speak_rate", 0)))
            all_rounds.append(int(stats.get("total_rounds", 0)))
            all_forced.append(float(stats.get("forced_speak_rate", 0)))
            all_text_len.append(float(stats.get("avg_speech_length", 0)))

        aggregated["topics"][topic[:40]] = {
            "dim_means": {d: round(float(np.mean(t_scores[d])), 2) for d in SCORING_DIMENSIONS},
            "dim_stds": {d: round(float(np.std(t_scores[d])), 2) for d in SCORING_DIMENSIONS},
            "overall_mean": round(float(np.mean(t_overalls)), 2),
            "overall_std": round(float(np.std(t_overalls)), 2),
            "avg_rounds": round(float(np.mean(t_rounds)), 1),
            "avg_forced_rate": round(float(np.mean(t_forced)), 3),
        }

    aggregated["overall"] = {
        "dim_means": {d: round(float(np.mean(all_scores[d])), 2) for d in SCORING_DIMENSIONS},
        "dim_stds": {d: round(float(np.std(all_scores[d])), 2) for d in SCORING_DIMENSIONS},
        "overall_mean": round(float(np.mean([
            sum(float(all_scores[d][i]) * 0.2 for d in SCORING_DIMENSIONS)
            for i in range(len(all_scores[SCORING_DIMENSIONS[0]]))
        ])), 2),
        "overall_std": round(float(np.std([
            sum(float(all_scores[d][i]) * 0.2 for d in SCORING_DIMENSIONS)
            for i in range(len(all_scores[SCORING_DIMENSIONS[0]]))
        ])), 2),
        "avg_rounds": round(float(np.mean(all_rounds)), 1),
        "avg_forced_rate": round(float(np.mean(all_forced)), 3),
        "avg_speech_length": round(float(np.mean(all_text_len)), 1),
        "num_observations": len(all_rounds),
    }
    return aggregated


def aggregate_ablation(data: dict) -> dict:
    """Aggregate ablation results by condition: mean, std."""
    results = data["results"]
    by_cond: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        if "error" in r:
            continue
        by_cond[r["condition"]].append(r)

    aggregated: dict = {"conditions": {}, "overall": {}}

    for cond, items in sorted(by_cond.items()):
        c_scores: dict[str, list[float]] = {d: [] for d in SCORING_DIMENSIONS}
        c_rounds: list[int] = []
        c_forced: list[float] = []

        for item in items:
            s = item.get("scores", {})
            for d in SCORING_DIMENSIONS:
                c_scores[d].append(float(s.get(d, 5)))
            stats = item.get("stats", {})
            c_rounds.append(int(stats.get("total_rounds", 0)))
            c_forced.append(float(stats.get("forced_speak_rate", 0)))

        cond_label = items[0].get("condition_label", cond) if items else cond
        aggregated["conditions"][cond] = {
            "label": cond_label,
            "dim_means": {d: round(float(np.mean(c_scores[d])), 2) for d in SCORING_DIMENSIONS},
            "dim_stds": {d: round(float(np.std(c_scores[d])), 2) for d in SCORING_DIMENSIONS},
            "overall_mean": round(float(np.mean([
                sum(float(c_scores[d][i]) * 0.2 for d in SCORING_DIMENSIONS)
                for i in range(len(c_scores[SCORING_DIMENSIONS[0]]))
            ])), 2),
            "avg_rounds": round(float(np.mean(c_rounds)), 1),
            "avg_forced_rate": round(float(np.mean(c_forced)), 3),
        }

    # Baseline comparison
    if "A" in aggregated["conditions"]:
        baseline = aggregated["conditions"]["A"]["overall_mean"]
        for cond in aggregated["conditions"]:
            delta = baseline - aggregated["conditions"][cond]["overall_mean"]
            aggregated["conditions"][cond]["delta_from_baseline"] = round(delta, 2)

    return aggregated


def compute_effect_size(mean_a: float, mean_b: float, std_pooled: float) -> float:
    """Cohen's d."""
    if std_pooled == 0:
        return 0.0
    return abs(mean_a - mean_b) / std_pooled


def print_summary(agg: dict, title: str = "Results Summary") -> None:
    """Pretty-print aggregated results."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    if "topics" in agg:
        for topic, t in agg["topics"].items():
            print(f"\n  {topic}")
            print(f"    Overall: {t['overall_mean']:.2f} ± {t['overall_std']:.2f}")
            print(f"    Rounds: {t['avg_rounds']:.1f}  Forced: {t['avg_forced_rate']:.1%}")
            for d in SCORING_DIMENSIONS:
                print(f"    {DIMENSION_LABELS_ZH[d]:6s}: {t['dim_means'][d]:.2f} ± {t['dim_stds'][d]:.2f}")

        o = agg["overall"]
        print(f"\n  ── OVERALL ──")
        print(f"    Overall: {o['overall_mean']:.2f} ± {o['overall_std']:.2f}")
        print(f"    N = {o['num_observations']} runs, avg {o['avg_rounds']:.1f} rounds")

    if "conditions" in agg:
        baseline = agg["conditions"].get("A", {}).get("overall_mean", 0)
        for cond, c in sorted(agg["conditions"].items()):
            delta = c.get("delta_from_baseline", 0)
            marker = " ← baseline" if cond == "A" else f" (Δ={delta:+.2f})"
            print(f"\n  [{cond}] {c['label']}{marker}")
            print(f"    Overall: {c['overall_mean']:.2f}  Rounds: {c['avg_rounds']:.1f}  Forced: {c['avg_forced_rate']:.1%}")
            for d in SCORING_DIMENSIONS:
                print(f"    {DIMENSION_LABELS_ZH[d]:6s}: {c['dim_means'][d]:.2f} ± {c['dim_stds'][d]:.2f}")
