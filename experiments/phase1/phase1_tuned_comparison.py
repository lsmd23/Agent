#!/usr/bin/env python3
"""Compare default vs P2-tuned Agent-Attention on phase1 tasks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baselines.common import envelope_for, load_jsonl  # noqa: E402
from experiments.baselines.faithful_runners import baseline_config_for, build_faithful_runtime  # noqa: E402


VARIANTS = ("agent_attention_agent", "agent_attention_agent_tuned")


def run_comparison(tasks_path: Path, output_dir: Path) -> list[Path]:
    tasks = load_jsonl(tasks_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for task in tasks:
        max_steps = int(task["budget"]["max_steps"])
        max_budget = float(task["budget"]["max_activation_cost"])
        for baseline_id in VARIANTS:
            runtime = build_faithful_runtime(baseline_id, task, max_steps)
            state = runtime.run(task["prompt"], max_budget=max_budget)
            envelope = envelope_for(
                task,
                baseline_id,
                baseline_config_for(baseline_id),
                state,
                runtime.events,
                simulation=False,
            )
            target = output_dir / f"{envelope['run_id']}.json"
            target.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(target)
    return written


def score_outputs(paths: list[Path], metrics_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "docs/deliverables/07/scoring_script.py"),
        *[str(path) for path in paths],
        "--output",
        str(metrics_path),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def summarize_variant(metrics: dict[str, Any], baseline_id: str) -> dict[str, Any]:
    runs = [run for run in metrics["runs"] if run["baseline_id"] == baseline_id]
    if not runs:
        return {"baseline_id": baseline_id, "run_count": 0}

    def avg(key_path: tuple[str, str]) -> float | None:
        values = [run[key_path[0]][key_path[1]] for run in runs if run[key_path[0]][key_path[1]] is not None]
        return round(mean(values), 6) if values else None

    return {
        "baseline_id": baseline_id,
        "run_count": len(runs),
        "success_rate": avg(("final", "task_success")) if False else round(
            mean([1.0 if run["final"]["task_success"] else 0.0 for run in runs]), 6
        ),
        "mean_cost_normalized_success": avg(("process", "cost_normalized_success")),
        "mean_activation_cost": avg(("process", "activation_cost")),
        "mean_module_calls": avg(("process", "module_calls")),
        "mean_repeated_action_ratio": avg(("process", "repeated_action_ratio")),
        "budget_exhaustion_rate": round(mean([1.0 if run["process"]["budget_exhaustion"] else 0.0 for run in runs]), 6),
        "mean_proxy_route_regret": avg(("routing", "proxy_route_regret_mean")),
    }


def write_comparison_summary(metrics: dict[str, Any], summary_path: Path) -> None:
    default_row = summarize_variant(metrics, "agent_attention_agent")
    tuned_row = summarize_variant(metrics, "agent_attention_agent_tuned")
    delta = {}
    for key in (
        "success_rate",
        "mean_cost_normalized_success",
        "mean_activation_cost",
        "mean_module_calls",
        "mean_repeated_action_ratio",
        "budget_exhaustion_rate",
        "mean_proxy_route_regret",
    ):
        d = default_row.get(key)
        t = tuned_row.get(key)
        if isinstance(d, (int, float)) and isinstance(t, (int, float)):
            delta[key] = round(float(t) - float(d), 6)

    summary = {
        "scope": "P2 Agent-Attention tuning comparison on phase1_mixed tasks.",
        "variants": {
            "default": default_row,
            "tuned": tuned_row,
            "delta_tuned_minus_default": delta,
        },
        "tuning_changes": [
            "adaptive_top_k_enabled: k=1 default, k=2 on failure/low confidence, k=3 on high risk",
            "strong_budget_gate: block module if cost > 30% remaining budget unless high risk/verifier",
            "cost_quality_frontier: prefer cheaper module within epsilon=0.05 score",
        ],
        "interpretation_hint": "Positive delta on success_rate and cost_normalized_success with lower activation_cost is desired.",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run P2 Agent-Attention tuning comparison.")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_tasks.jsonl")
    parser.add_argument("--output-dir", default="experiments/trajectories/phase1_tuned_comparison")
    parser.add_argument("--metrics-output", default="experiments/metrics/phase1_tuned_comparison_metrics.json")
    parser.add_argument("--summary-output", default="experiments/metrics/phase1_tuned_comparison_summary.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = run_comparison(ROOT / args.tasks, ROOT / args.output_dir)
    metrics = score_outputs(paths, ROOT / args.metrics_output)
    write_comparison_summary(metrics, ROOT / args.summary_output)
    print(
        json.dumps(
            {
                "runs": len(paths),
                "metrics": args.metrics_output,
                "summary": args.summary_output,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
