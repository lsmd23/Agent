#!/usr/bin/env python3
"""Cascade pilot: replay on existing matrix or live LLM eval (Brief B)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.cascade.cascade_policy import CASCADE_POLICIES, ESCALATION_TRIGGER_TABLE  # noqa: E402
from experiments.cascade.cascade_replay import analyze, render_audit_markdown  # noqa: E402
from experiments.cascade.cascade_runner import run_cascade_llm, summarize_cascade_runs  # noqa: E402
from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402
from experiments.real_benchmarks.llm_client import LLMClient  # noqa: E402
from experiments.real_benchmarks.run_gsm8k_llm import load_jsonl  # noqa: E402

load_project_env(start=_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cascade pilot (Brief B).")
    parser.add_argument("--mode", choices=["replay", "live"], default="replay")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--policy", default="react_aa_moa", choices=list(CASCADE_POLICIES))
    parser.add_argument("--policies", nargs="+", choices=list(CASCADE_POLICIES))
    parser.add_argument("--tasks", default="experiments/tasks/phase1_code_all.jsonl")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini")
    parser.add_argument("--output-json", default="experiments/metrics/cascade_pilot_summary.json")
    parser.add_argument("--output-md", default="experiments/analysis/cascade_pilot_audit.md")
    parser.add_argument("--output-dir", default="experiments/llm_runs/cascade_pilot")
    return parser.parse_args()


def run_replay(args: argparse.Namespace) -> dict:
    policies = args.policies or list(CASCADE_POLICIES)
    result = analyze(args.input, policies=policies)
    result["escalation_trigger_table"] = ESCALATION_TRIGGER_TABLE
    return result


def run_live(args: argparse.Namespace) -> dict:
    """Run live cascade; prefer `run_real_llm_eval.py --family cascade` for unified summaries."""
    tasks = load_jsonl(Path(args.tasks), args.limit)
    runs: list[dict] = []
    output_root = Path(args.output_dir) / args.policy
    output_root.mkdir(parents=True, exist_ok=True)

    client = LLMClient(provider=args.provider, model=args.model)
    for task in tasks:
        trajectory = run_cascade_llm(args.policy, task, client)
        target = output_root / f"{trajectory['run_id']}.json"
        target.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        runs.append(trajectory)
        print(
            json.dumps(
                {
                    "task_id": task["task_id"],
                    "success": trajectory["final_success_label"],
                    "halt_stage": trajectory["cascade"]["halt_stage"],
                    "model_calls": trajectory["metrics_summary"]["model_calls"],
                },
                ensure_ascii=False,
            )
        )

    summary_stats = summarize_cascade_runs(runs)
    return {
        "scope": "Live cascade pilot (Brief B).",
        "mode": "live",
        "policy_id": args.policy,
        "tasks": len(tasks),
        "provider": args.provider,
        "model": args.model,
        "summary": summary_stats,
        "escalation_trigger_table": ESCALATION_TRIGGER_TABLE,
    }


def main() -> None:
    args = parse_args()
    if args.mode == "replay":
        result = run_replay(args)
    else:
        result = run_live(args)

    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.mode == "replay":
        md_path = Path(args.output_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_audit_markdown(result), encoding="utf-8")
        print(
            json.dumps(
                {
                    "output_json": str(json_path),
                    "output_md": str(args.output_md),
                    "evidence_outcome": result["evidence_outcome"],
                    "primary_accuracy": result["policies"][result["primary_policy_id"]]["accuracy"],
                    "primary_mean_calls": result["policies"][result["primary_policy_id"]]["mean_model_calls"],
                },
                indent=2,
            )
        )
    else:
        print(json.dumps({"output_json": str(json_path), "summary": result["summary"]}, indent=2))


if __name__ == "__main__":
    main()
