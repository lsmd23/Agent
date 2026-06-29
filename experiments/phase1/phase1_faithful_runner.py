#!/usr/bin/env python3
"""Run Phase 1 faithful baseline matrix over code/search/research tasks."""

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
from experiments.baselines.faithful_runners import (  # noqa: E402
    FAITHFUL_BASELINE_IDS,
    baseline_config_for,
    build_faithful_runtime,
)


def applicable_baselines(task: dict[str, Any]) -> list[str]:
    applicability = task.get("baseline_applicability", {})
    baselines = [baseline_id for baseline_id in FAITHFUL_BASELINE_IDS if applicability.get(baseline_id, True)]
    if applicability.get("fixed_moa_agent") and "moa_style_agent" not in baselines:
        baselines.append("moa_style_agent")
    if "full_history_agent" not in baselines and applicability.get("single_react_agent"):
        baselines.append("full_history_agent")
    return baselines


def run_matrix(tasks_path: Path, output_dir: Path) -> list[Path]:
    tasks = load_jsonl(tasks_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for task in tasks:
        max_steps = int(task["budget"]["max_steps"])
        max_budget = float(task["budget"]["max_activation_cost"])
        for baseline_id in applicable_baselines(task):
            runtime = build_faithful_runtime(baseline_id, task, max_steps)
            state = runtime.run(task["prompt"], max_budget=max_budget)
            baseline_config = baseline_config_for(baseline_id)
            envelope = envelope_for(
                task,
                baseline_id,
                baseline_config,
                state,
                runtime.events,
                simulation=False,
            )
            target = output_dir / f"{envelope['run_id']}.json"
            target.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written.append(target)
    return written


def score_outputs(paths: list[Path], metrics_path: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "docs/deliverables/07/scoring_script.py"),
        *[str(path) for path in paths],
        "--output",
        str(metrics_path),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)


def compact(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def average(values: list[float]) -> float | None:
    return compact(mean(values)) if values else None


def write_baseline_summary(metrics_path: Path, summary_path: Path) -> None:
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for baseline_id in FAITHFUL_BASELINE_IDS:
        runs = [run for run in data["runs"] if run["baseline_id"] == baseline_id]
        if not runs:
            continue
        rows.append(
            {
                "baseline_id": baseline_id,
                "run_count": len(runs),
                "success_rate": average([1.0 if run["final"]["task_success"] else 0.0 for run in runs]),
                "mean_cost_normalized_success": average(
                    [run["process"]["cost_normalized_success"] for run in runs if run["process"]["cost_normalized_success"] is not None]
                ),
                "mean_activation_cost": average([run["process"]["activation_cost"] for run in runs if run["process"]["activation_cost"] is not None]),
                "mean_module_calls": average([run["process"]["module_calls"] for run in runs if run["process"]["module_calls"] is not None]),
                "mean_repeated_action_ratio": average(
                    [run["process"]["repeated_action_ratio"] for run in runs if run["process"]["repeated_action_ratio"] is not None]
                ),
                "budget_exhaustion_rate": average([1.0 if run["process"]["budget_exhaustion"] else 0.0 for run in runs]),
                "premature_halt_rate": average([1.0 if run["process"]["premature_halt"] else 0.0 for run in runs]),
                "mean_route_entropy": average([run["routing"]["route_entropy"] for run in runs if run["routing"]["route_entropy"] is not None]),
                "mean_proxy_route_regret": average(
                    [run["routing"]["proxy_route_regret_mean"] for run in runs if run["routing"]["proxy_route_regret_mean"] is not None]
                ),
                "total_memory_reads": sum(run["memory"]["memory_reads"] for run in runs),
                "total_negative_transfer_cases": sum(run["memory"]["negative_transfer_cases"] for run in runs),
                "known_deviations": sorted({item for run in runs for item in run["known_deviations"]}),
            }
        )
    summary = {
        "scope": "Phase 1 faithful baseline matrix on toy runtime with distinct control policies.",
        "warning": "Faithful control policies on deterministic toy runtime; not real LLM results.",
        "rows": rows,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_manifest(paths: list[Path], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "run_id": data["run_id"],
                "task_id": data["task_id"],
                "benchmark_id": data["benchmark_id"],
                "task_family": data["task_family"],
                "baseline_id": data["baseline_id"],
                "trajectory_path": str(path.relative_to(ROOT)),
                "known_deviations": data["known_deviations"],
            }
        )
    manifest_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1 faithful baseline matrix.")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_tasks.jsonl")
    parser.add_argument("--output-dir", default="experiments/trajectories/phase1_faithful_matrix")
    parser.add_argument("--metrics-output", default="experiments/metrics/phase1_faithful_matrix_metrics.json")
    parser.add_argument("--summary-output", default="experiments/metrics/phase1_faithful_matrix_by_baseline.json")
    parser.add_argument("--manifest-output", default="experiments/phase1/phase1_faithful_matrix_manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = run_matrix(ROOT / args.tasks, ROOT / args.output_dir)
    write_manifest(paths, ROOT / args.manifest_output)
    score_outputs(paths, ROOT / args.metrics_output)
    write_baseline_summary(ROOT / args.metrics_output, ROOT / args.summary_output)
    print(
        json.dumps(
            {
                "runs": len(paths),
                "trajectory_dir": args.output_dir,
                "manifest": args.manifest_output,
                "metrics": args.metrics_output,
                "summary": args.summary_output,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
