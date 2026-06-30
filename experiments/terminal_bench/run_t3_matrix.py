#!/usr/bin/env python3
"""T3: Matched-budget Terminal-Bench matrix from pre-registered subset manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402
from experiments.terminal_bench.adapter import (  # noqa: E402
    FAITHFUL_TB_BASELINES,
    classify_tb_failure,
    docker_python_sdk_available,
    list_task_ids,
    run_tb_smoke,
)
from experiments.terminal_bench.run_terminal_bench_matrix import summarize_runs  # noqa: E402

load_project_env(start=_ROOT)

DEFAULT_MANIFEST = _ROOT / "experiments/tasks/terminal_bench_subset_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run T3 matched-budget TB matrix.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default="experiments/llm_runs/terminal_bench/t3")
    parser.add_argument("--summary-output", default="experiments/metrics/terminal_bench_matrix_summary.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-tasks", type=int, default=0, help="Run first N tasks only (0 = all)")
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid manifest: {path}")
    return payload


def main() -> None:
    args = parse_args()
    manifest = load_manifest(Path(args.manifest))
    budget = manifest.get("matched_budget", {})
    dataset = Path(manifest.get("dataset_path", "external/terminal-bench-core"))
    baselines = manifest.get("baselines", list(FAITHFUL_TB_BASELINES))
    task_ids = manifest.get("task_ids", [])
    if args.limit_tasks > 0:
        task_ids = task_ids[: args.limit_tasks]

    available = set(list_task_ids(dataset))
    tasks = [task_id for task_id in task_ids if task_id in available]
    missing = [task_id for task_id in task_ids if task_id not in available]

    preflight = {
        "manifest": str(args.manifest),
        "manifest_name": manifest.get("name"),
        "docker_python_sdk": docker_python_sdk_available(),
        "tasks_requested": task_ids,
        "tasks_selected": tasks,
        "tasks_missing": missing,
        "baselines": baselines,
        "matched_budget": budget,
        "model": os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL"),
        "provider": os.environ.get("LLM_PROVIDER", "openai"),
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, "preflight": preflight}, indent=2))
        return

    if not docker_python_sdk_available():
        print(json.dumps({"blocked": True, "blocker": "docker_python_sdk_permission", "preflight": preflight}, indent=2))
        sys.exit(2)

    max_shell_steps = int(budget.get("max_shell_steps", 8))
    timeout_s = int(budget.get("timeout_s", 900))

    runs: list[dict[str, Any]] = []
    for baseline_id in baselines:
        if baseline_id not in FAITHFUL_TB_BASELINES:
            raise SystemExit(f"Unsupported baseline: {baseline_id}")
        for task_id in tasks:
            result = run_tb_smoke(
                baseline_id=baseline_id,
                task_id=task_id,
                dataset_path=dataset,
                output_dir=Path(args.output_dir),
                use_oracle_agent=False,
                timeout_s=timeout_s,
                max_shell_steps=max_shell_steps,
            )
            envelope = result.get("envelope", {})
            metrics = envelope.get("metrics_summary", {})
            stderr = result.get("stderr_tail", "")
            run_dir = Path(result.get("run_dir", ""))
            runs.append(
                {
                    "baseline_id": baseline_id,
                    "task_id": task_id,
                    "end_task_success": metrics.get("end_task_success"),
                    "final_success_label": envelope.get("final_success_label"),
                    "failure_category": classify_tb_failure(metrics, stderr, run_dir=run_dir),
                    "elapsed_s": result.get("elapsed_s"),
                    "model_calls": metrics.get("model_calls"),
                    "max_shell_steps": max_shell_steps,
                    "envelope_path": result.get("envelope_path"),
                    "run_dir": result.get("run_dir"),
                }
            )
            print(json.dumps(runs[-1], ensure_ascii=False))

    summary = summarize_runs(runs)
    summary["scope"] = "T3 matched-budget Terminal-Bench matrix."
    summary["manifest"] = str(args.manifest)
    summary["preflight"] = preflight
    summary["provider"] = preflight["provider"]
    summary["model"] = preflight["model"]
    summary["per_task"] = runs

    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "total_runs": len(runs)}, indent=2))


if __name__ == "__main__":
    main()
