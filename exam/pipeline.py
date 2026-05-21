"""Full experiment pipeline — runs baseline and ablation experiments inside the
MADF container, scores with an independent judge, and saves structured results.

Designed to be executed INSIDE the backend container where all agent_engine
imports resolve naturally:

    docker exec madf-backend python /app/exam_pipeline.py

Output:
    exam/results/baseline_full.json   — 3 topics × 3 reps
    exam/results/ablation_full.json   — 6 conditions × 3 reps
"""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from exam.ablation import AblationOrchestrator
from exam.config import (
    COMPARISON_TOPICS,
    ABLATION_TOPIC,
    ABLATION_CONDITIONS,
    SCORING_DIMENSIONS,
    DIMENSION_LABELS_ZH,
)


RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SKILLS_ROOT = Path(os.getenv("SKILLS_ROOT", str(Path(__file__).parent.parent / "skills")))
OWNER = "2fd16265-c1bd-4ca0-bc7e-de7923c651f0"  # user with high-quality skills


def find_skills() -> dict[str, str]:
    """Find available character skills for experiments."""
    skills: dict[str, str] = {}
    owner_dir = SKILLS_ROOT / OWNER
    if not owner_dir.exists():
        return skills
    for d in sorted(owner_dir.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            name = d.name.replace("-perspective", "")
            skills[name] = str(d)
    return skills


async def run_one(
    topic: str,
    agent_paths: dict[str, str],
    duration: int = 180,
    ablation: dict | None = None,
) -> dict:
    """Run one discussion, return {topic, transcript, stats, ...}."""
    transcript: list[dict] = []
    confidences: list[float] = []
    speech_lengths: list[int] = []

    async def on_event(event_type: str, data: dict) -> None:
        if event_type == "agent_speak_end":
            transcript.append({
                "speaker": data.get("agent_name", "?"),
                "content": data.get("content", ""),
                "round": data.get("round", 0),
            })
            speech_lengths.append(len(data.get("content", "")))
        elif event_type == "agent_think":
            confidences.append(float(data.get("confidence", 0)))
        elif event_type == "host_intro":
            transcript.insert(0, {"speaker": "主持人", "content": data.get("content", ""), "round": 0})
        elif event_type == "host_summary":
            transcript.append({"speaker": "主持人", "content": data.get("content", ""), "round": -1})

    kwargs: dict = {
        "discussion_id": uuid.uuid4(),
        "topic": topic,
        "duration": duration,
        "agent_skill_paths": agent_paths,
        "on_event": on_event,
    }

    if ablation:
        orch = AblationOrchestrator(
            enable_intro=ablation.get("enable_intro", True),
            enable_summary=ablation.get("enable_summary", True),
            enable_confidence=ablation.get("enable_confidence", True),
            enable_jitter=ablation.get("enable_jitter", True),
            enable_rules=ablation.get("enable_rules", True),
            **kwargs,
        )
    else:
        orch = AblationOrchestrator(**kwargs)  # all defaults = full system

    t0 = time.time()
    results = await orch.run()
    elapsed = time.time() - t0

    forced = sum(1 for r in results if r.was_forced)
    return {
        "topic": topic,
        "elapsed": round(elapsed, 1),
        "stats": {
            "total_rounds": len(results),
            "forced_speaks": forced,
            "forced_speak_rate": round(forced / max(len(results), 1), 3),
            "avg_confidence": round(sum(confidences) / max(len(confidences), 1), 4),
            "avg_speech_length": round(sum(speech_lengths) / max(len(speech_lengths), 1), 1),
        },
        "transcript": transcript,
        "ablation": ablation,
    }


async def run_baseline(agent_paths: dict[str, str], topics: list[str] | None = None,
                       repetitions: int = 3, duration: int = 180) -> list[dict]:
    """Run single-model baseline: topics × repetitions."""
    topics = topics or COMPARISON_TOPICS
    total = len(topics) * repetitions
    results: list[dict] = []
    done = 0

    for topic in topics:
        for rep in range(1, repetitions + 1):
            print(f"[baseline {done+1}/{total}] topic={topic[:30]}... rep={rep}")
            try:
                r = await run_one(topic, agent_paths, duration=duration)
                r["rep"] = rep
                results.append(r)
                print(f"  {r['stats']['total_rounds']} rounds, {r['stats']['forced_speaks']} forced")
            except Exception as exc:
                print(f"  FAILED: {exc}")
                results.append({"topic": topic, "rep": rep, "error": str(exc)})
            done += 1

    return results


async def run_ablation(agent_paths: dict[str, str], topic: str | None = None,
                       repetitions: int = 3, duration: int = 180) -> list[dict]:
    """Run ablation experiment: conditions × repetitions."""
    topic = topic or ABLATION_TOPIC
    results: list[dict] = []
    total = len(ABLATION_CONDITIONS) * repetitions
    done = 0

    for cond_key, cond_label in ABLATION_CONDITIONS.items():
        ablation_config = _ablation_config(cond_key)
        for rep in range(1, repetitions + 1):
            print(f"[ablation {done+1}/{total}] cond={cond_key} ({cond_label}) rep={rep}")
            try:
                r = await run_one(topic, agent_paths, duration=duration, ablation=ablation_config)
                r["condition"] = cond_key
                r["condition_label"] = cond_label
                r["rep"] = rep
                results.append(r)
                print(f"  {r['stats']['total_rounds']} rounds, {r['stats']['forced_speaks']} forced")
            except Exception as exc:
                print(f"  FAILED: {exc}")
                results.append({"condition": cond_key, "rep": rep, "error": str(exc)})
            done += 1

    return results


def _ablation_config(cond_key: str) -> dict:
    """Map condition key to AblationOrchestrator parameters."""
    configs = {
        "A": dict(enable_intro=True, enable_summary=True, enable_confidence=True,
                   enable_jitter=True, enable_rules=True),
        "B": dict(enable_intro=True, enable_summary=True, enable_confidence=False,
                   enable_jitter=True, enable_rules=True),
        "C": dict(enable_intro=True, enable_summary=True, enable_confidence=True,
                   enable_jitter=False, enable_rules=True),
        "D": dict(enable_intro=False, enable_summary=True, enable_confidence=True,
                   enable_jitter=True, enable_rules=True),
        "E": dict(enable_intro=True, enable_summary=False, enable_confidence=True,
                   enable_jitter=True, enable_rules=True),
        "F": dict(enable_intro=True, enable_summary=True, enable_confidence=True,
                   enable_jitter=True, enable_rules=False),
    }
    return configs.get(cond_key, configs["A"])


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="MADF Experiment Pipeline")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--duration", type=int, default=180)
    parser.add_argument("--topics", nargs="*", default=None)
    args = parser.parse_args()

    skills = find_skills()
    if len(skills) < 3:
        print(f"ERROR: Need >= 3 skills, found {len(skills)}: {list(skills.keys())}")
        return
    selected = dict(list(skills.items())[:3])
    print(f"Skills: {list(selected.keys())}")

    all_data: dict = {"skills": list(selected.keys()), "model": os.getenv("LLM_MODEL", "unknown")}

    if args.baseline:
        print("\n=== BASELINE EXPERIMENT ===")
        baseline = await run_baseline(selected, topics=args.topics,
                                       repetitions=args.repetitions,
                                       duration=args.duration)
        out = RESULTS_DIR / "baseline_full.json"
        out.write_text(json.dumps({**all_data, "results": baseline}, ensure_ascii=False, indent=2))
        print(f"Saved {len(baseline)} results → {out}")

    if args.ablation:
        print("\n=== ABLATION EXPERIMENT ===")
        abl = await run_ablation(selected, repetitions=args.repetitions,
                                  duration=args.duration)
        out = RESULTS_DIR / "ablation_full.json"
        out.write_text(json.dumps({**all_data, "results": abl}, ensure_ascii=False, indent=2))
        print(f"Saved {len(abl)} results → {out}")


if __name__ == "__main__":
    asyncio.run(main())
