#!/usr/bin/env python3
"""Judge scoring for completed experiment results.

Reads baseline_full.json or ablation_full.json, scores each discussion
with LLM-as-Judge, writes scores back into the file.

Usage:
    python exam/score_results.py --baseline
    python exam/score_results.py --ablation
    python exam/score_results.py --baseline --ablation
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exam.judge import judge_discussion
from exam.config import SCORING_DIMENSIONS

RESULTS_DIR = Path(__file__).resolve().parent / "results"


async def score_file(filename: str) -> None:
    path = RESULTS_DIR / filename
    if not path.exists():
        print(f"Not found: {path}")
        return

    data = json.loads(path.read_text())
    results = data.get("results", [])

    total = len([r for r in results if "error" not in r])
    done = 0
    for item in results:
        if "error" in item:
            continue
        if "scores" in item and item.get("overall"):
            done += 1
            continue  # already scored

        topic = item.get("topic", "")
        transcript = item.get("transcript", [])
        cond = item.get("condition", "")
        rep = item.get("rep", "")

        label = f"[{done+1}/{total}]"
        if cond:
            label += f" cond={cond}"
        label += f" rep={rep}"

        print(f"{label} topic={topic[:30]}...")
        try:
            score = await judge_discussion(transcript, topic)
            item["scores"] = score.scores
            item["overall"] = score.overall
            item["reasonings"] = score.reasonings
            item["strengths"] = score.strengths
            item["weaknesses"] = score.weaknesses
            print(f"  overall={score.overall:.2f}  " +
                  " ".join(f"{d[:4]}={score.scores[d]:.1f}" for d in SCORING_DIMENSIONS))
        except Exception as exc:
            print(f"  FAILED: {exc}")
            item["scores"] = {d: 5.0 for d in SCORING_DIMENSIONS}
            item["overall"] = 5.0
            item["reasonings"] = {d: f"error: {exc}" for d in SCORING_DIMENSIONS}
        done += 1
        # Save after each discussion (crash-safe)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    print(f"\nScored {done} discussions → {path}")


async def main():
    args = set(sys.argv[1:])
    do_baseline = "--baseline" in args or not args
    do_ablation = "--ablation" in args or not args

    if do_baseline:
        await score_file("baseline_full.json")
    if do_ablation:
        await score_file("ablation_full.json")


if __name__ == "__main__":
    asyncio.run(main())
