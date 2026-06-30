#!/usr/bin/env python3
"""AA component ablation pilot: matrix replay or live LLM eval (Brief C)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.ablations.aa_ablation_llm import run_aa_ablation_llm
from experiments.ablations.aa_ablation_replay import analyze, render_audit_markdown  # noqa: E402
from experiments.ablations.aa_ablation_specs import AA_ABLATION_IDS  # noqa: E402
from experiments.real_benchmarks.llm_client import LLMClient  # noqa: E402
from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402
from experiments.real_benchmarks.run_gsm8k_llm import load_jsonl  # noqa: E402

load_project_env(start=_ROOT)

RESCUE_TASK_IDS = (
    "phase1_code_csv_001",
    "phase1_code_email_001",
    "phase1_code_env_flag_001",
)
LIVE_ABLATION_IDS = tuple(
    ablation_id for ablation_id in AA_ABLATION_IDS if ablation_id not in {"aa_tuned_control", "aa_direct_first"}
)
DEFAULT_LIVE_ABLATIONS = ("aa_no_verifier", "aa_no_adaptive_topk", "aa_top1", "aa_lite_escalation")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AA component ablation pilot (Brief C).")
    parser.add_argument("--mode", choices=["replay", "live"], default="replay")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument(
        "--trajectory-root",
        default="experiments/llm_runs/code_full_matrix",
        help="Root containing code_all/<baseline>/ trajectories for rescue forensics.",
    )
    parser.add_argument(
        "--phase2-summary",
        default="experiments/metrics/phase2_memory_ablation_summary.json",
    )
    parser.add_argument("--tasks", default="experiments/tasks/phase1_code_all.jsonl")
    parser.add_argument("--subset", choices=["rescue", "all"], default="all")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ablations", nargs="+", choices=list(LIVE_ABLATION_IDS))
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini")
    parser.add_argument("--output-json", default="experiments/metrics/aa_ablation_pilot.json")
    parser.add_argument("--output-md", default="experiments/analysis/aa_ablation_audit.md")
    parser.add_argument("--output-dir", default="experiments/llm_runs/aa_ablation_pilot")
    return parser.parse_args()


def _has_api_key(provider: str) -> bool:
    if provider == "ollama":
        return True
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"))


def run_live(args: argparse.Namespace) -> dict:
    if not _has_api_key(args.provider):
        return {
            "scope": "Live AA ablation blocked (no API key).",
            "mode": "live",
            "blocked": True,
            "reason": "Set OPENAI_API_KEY or LLM_API_KEY for live ablation runs.",
        }

    tasks = load_jsonl(Path(args.tasks), args.limit)
    if args.subset == "rescue":
        tasks = [task for task in tasks if task["task_id"] in RESCUE_TASK_IDS]

    ablation_ids = args.ablations or list(DEFAULT_LIVE_ABLATIONS)
    output_root = Path(args.output_dir) / args.subset
    runs: list[dict] = []

    for ablation_id in ablation_ids:
        if ablation_id not in AA_ABLATION_IDS or ablation_id in {"aa_direct_first", "aa_tuned_control"}:
            continue
        for task in tasks:
            client = LLMClient(provider=args.provider, model=args.model)
            trajectory = run_aa_ablation_llm(ablation_id, task, client)
            trajectory["ablation_id"] = ablation_id
            out_dir = output_root / ablation_id
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / f"{trajectory['run_id']}.json"
            target.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            runs.append(trajectory)
            print(
                json.dumps(
                    {
                        "ablation_id": ablation_id,
                        "task_id": task["task_id"],
                        "success": trajectory["final_success_label"],
                        "model_calls": trajectory["metrics_summary"].get("model_calls"),
                    },
                    ensure_ascii=False,
                )
            )

    by_ablation: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        aid = run.get("ablation_id") or "unknown"
        by_ablation.setdefault(aid, []).append(run)

    summary_by_ablation: dict[str, Any] = {}
    for ablation_id, items in by_ablation.items():
        n = len(items)
        correct = sum(1 for item in items if item["final_success_label"] == "pass")
        calls = [item["metrics_summary"].get("model_calls", 0) for item in items]
        mean_calls = sum(calls) / n if n else 0
        summary_by_ablation[ablation_id] = {
            "runs": n,
            "correct": correct,
            "accuracy": round(correct / n, 4) if n else 0,
            "mean_model_calls": round(mean_calls, 4),
            "cost_normalized_success": round((correct / n) / mean_calls, 4) if mean_calls else 0,
        }

    return {
        "scope": "Live AA component ablation pilot (Brief C).",
        "mode": "live",
        "subset": args.subset,
        "tasks": len(tasks),
        "ablations": ablation_ids,
        "runs": len(runs),
        "summary_by_ablation": summary_by_ablation,
        "provider": args.provider,
        "model": args.model,
    }


def main() -> None:
    args = parse_args()

    if args.mode == "replay":
        result = analyze(
            args.input,
            trajectory_root=args.trajectory_root,
            phase2_summary_path=args.phase2_summary,
        )
    else:
        live = run_live(args)
        result = analyze(
            args.input,
            trajectory_root=args.trajectory_root,
            phase2_summary_path=args.phase2_summary,
        )
        result["live_pilot"] = live

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
                    "control_accuracy": result["variants"]["aa_tuned_control"].get("accuracy"),
                    "direct_first_cost_norm_gain": result["comparison_vs_control"].get(
                        "direct_first_gain_cost_norm"
                    ),
                },
                indent=2,
            )
        )
    else:
        print(json.dumps({"output_json": str(json_path), "live_pilot": result.get("live_pilot")}, indent=2))


if __name__ == "__main__":
    main()
