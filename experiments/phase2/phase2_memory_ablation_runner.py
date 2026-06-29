#!/usr/bin/env python3
"""Run Phase 2 memory ablations on tuned Agent-Attention."""

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
from experiments.baselines.memory_ablations import (  # noqa: E402
    MEMORY_ABLATION_IDS,
    ablation_config_for,
    build_memory_ablation_runtime,
)


NEGATIVE_MEMORY_TASK = "phase0_seed_negative_memory_001"


def run_matrix(tasks_path: Path, output_dir: Path, task_filter: str | None = None) -> list[Path]:
    tasks = load_jsonl(tasks_path)
    if task_filter:
        tasks = [task for task in tasks if task["task_id"] == task_filter]
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for task in tasks:
        max_steps = int(task["budget"]["max_steps"])
        max_budget = float(task["budget"]["max_activation_cost"])
        for ablation_id in MEMORY_ABLATION_IDS:
            runtime = build_memory_ablation_runtime(ablation_id, task, max_steps)
            state = runtime.run(task["prompt"], max_budget=max_budget)
            config = ablation_config_for(ablation_id)
            envelope = envelope_for(
                task,
                config["baseline_id"],
                config,
                state,
                runtime.events,
                simulation=False,
                run_prefix="phase2_memory",
                ablation_id=ablation_id,
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


def summarize_ablation(metrics: dict[str, Any], ablation_id: str) -> dict[str, Any]:
    runs = [
        run
        for run in metrics["runs"]
        if run.get("ablation_id") == ablation_id or f"phase2_memory__{ablation_id}__" in run["trajectory_path"]
    ]
    if not runs:
        return {"ablation_id": ablation_id, "run_count": 0}

    def avg(getter):
        values = [getter(run) for run in runs]
        values = [value for value in values if value is not None]
        return round(mean(values), 6) if values else None

    return {
        "ablation_id": ablation_id,
        "run_count": len(runs),
        "success_rate": avg(lambda run: 1.0 if run["final"]["task_success"] else 0.0),
        "mean_cost_normalized_success": avg(lambda run: run["process"]["cost_normalized_success"]),
        "mean_activation_cost": avg(lambda run: run["process"]["activation_cost"]),
        "total_memory_reads": int(sum(run["memory"]["memory_reads"] for run in runs)),
        "total_harmful_memory_reads": int(sum(run["memory"]["harmful_memory_reads"] for run in runs)),
        "total_negative_transfer_cases": int(sum(run["memory"]["negative_transfer_cases"] for run in runs)),
    }


def write_summary(metrics: dict[str, Any], summary_path: Path) -> None:
    rows = [summarize_ablation(metrics, ablation_id) for ablation_id in MEMORY_ABLATION_IDS]
    negative_probe = {
        ablation_id: summarize_ablation(
            {"runs": [run for run in metrics["runs"] if run["task_id"] == NEGATIVE_MEMORY_TASK]},
            ablation_id,
        )
        for ablation_id in MEMORY_ABLATION_IDS
    }
    summary = {
        "scope": "Phase 2 memory ablations on tuned Agent-Attention.",
        "control_id": "aa_tuned_control",
        "task_count": len({run["task_id"] for run in metrics["runs"]}),
        "rows": rows,
        "negative_memory_probe": negative_probe,
        "negative_memory_task_id": NEGATIVE_MEMORY_TASK,
        "interpretation_hint": "Compare aa_no_memory vs control for transfer; aa_unfiltered_memory vs aa_quarantine_aware on negative-memory probe.",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 2 memory ablation matrix.")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_tasks.jsonl")
    parser.add_argument("--task-filter", default=None, help="Run only one task_id.")
    parser.add_argument("--output-dir", default="experiments/trajectories/phase2_memory_ablation")
    parser.add_argument("--metrics-output", default="experiments/metrics/phase2_memory_ablation_metrics.json")
    parser.add_argument("--summary-output", default="experiments/metrics/phase2_memory_ablation_summary.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = run_matrix(ROOT / args.tasks, ROOT / args.output_dir, task_filter=args.task_filter)
    metrics = score_outputs(paths, ROOT / args.metrics_output)
    write_summary(metrics, ROOT / args.summary_output)
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
