"""Data loading for final experiment results."""

import json
from pathlib import Path
from collections import defaultdict
import numpy as np

SCORING_DIMENSIONS = ['coherence', 'depth', 'consistency', 'engagement', 'relevance']
DIMS_ZH = ['连贯性', '洞见深度', '角色一致性', '参与质量', '主题相关性']
COND_LABELS = {"BL":"单LLM饰三角","A":"完整MADF","B":"无仲裁","C":"无Jitter","D":"无开场","E":"无总结","F":"无铁律"}
COND_ORDER = ["BL", "A", "B", "C", "D", "E", "F"]

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_data():
    grouped = defaultdict(list)
    for fname, co in [("single_agent_baseline.json","BL"),("baseline_full.json","A"),("ablation_full.json",None)]:
        data = json.loads((RESULTS_DIR / fname).read_text())
        for r in data.get("results", []):
            if "final_scores" not in r: continue
            grouped[co or r.get("condition","?")].append(r)
    return dict(grouped)


def aggregate(data):
    agg = {}
    for cond in COND_ORDER:
        if cond not in data: continue
        items = data[cond]
        ovs = [r["final_overall"] for r in items]
        agg[cond] = {
            "label": COND_LABELS.get(cond, cond),
            "n": len(items),
            "overall_mean": round(float(np.mean(ovs)), 2),
            "overall_std": round(float(np.std(ovs)), 2),
            "dim_means": {d: round(float(np.mean([r["final_scores"][d] for r in items])), 2) for d in SCORING_DIMENSIONS},
        }
    return agg
