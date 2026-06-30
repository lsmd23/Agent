#!/usr/bin/env python3
"""T2: Terminal-Bench smoke matrix (3 baselines × N tasks)."""

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
    docker_available,
    docker_python_sdk_available,
    list_task_ids,
    run_tb_smoke,
)

load_project_env(start=_ROOT)

# Smoke subset: prefer tasks without apt-get in Dockerfile (more reliable on flaky mirrors).
DEFAULT_TB_TASKS = [
    "fix-permissions",
    "fibonacci-server",
    "configure-git-webserver",
    "count-dataset-tokens",
    "download-youtube",
]

DEFAULT_BASELINES = (
    "single_react_llm_agent",
    "fixed_workflow_llm_agent",
    "agent_attention_llm_tuned",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Terminal-Bench smoke matrix.")
    parser.add_argument("--tasks", nargs="+", default=DEFAULT_TB_TASKS)
    parser.add_argument("--baselines", nargs="+", default=list(DEFAULT_BASELINES))
    parser.add_argument("--dataset-path", default="external/terminal-bench-core")
    parser.add_argument("--output-dir", default="experiments/llm_runs/terminal_bench/matrix")
    parser.add_argument("--summary-output", default="experiments/metrics/terminal_bench_smoke_summary.json")
    parser.add_argument("--use-oracle", action="store_true", help="Oracle agent (harness validation).")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    return parser.parse_args()


def summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_baseline[run["baseline_id"]].append(run)

    summary: dict[str, Any] = {
        "scope": "Terminal-Bench smoke matrix (T2).",
        "total_runs": len(runs),
        "baselines": {},
        "failure_categories": defaultdict(int),
    }
    for baseline_id, items in by_baseline.items():
        end_pass = sum(1 for item in items if item.get("end_task_success"))
        timeouts = sum(1 for item in items if item.get("failure_category") == "timeout")
        latencies = [item["elapsed_s"] for item in items if item.get("elapsed_s") is not None]
        model_calls = [item["model_calls"] for item in items if item.get("model_calls") is not None]
        summary["baselines"][baseline_id] = {
            "runs": len(items),
            "success_rate": end_pass / len(items) if items else None,
            "correct": end_pass,
            "timeout_rate": timeouts / len(items) if items else None,
            "mean_latency_s": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "mean_model_calls": round(sum(model_calls) / len(model_calls), 2) if model_calls else None,
        }
        for item in items:
            cat = item.get("failure_category") or "none"
            summary["failure_categories"][cat] += 1
    summary["failure_categories"] = dict(summary["failure_categories"])
    return summary


def main() -> None:
    args = parse_args()
    dataset = Path(args.dataset_path)
    available = set(list_task_ids(dataset))
    tasks = [task_id for task_id in args.tasks if task_id in available]
    missing = [task_id for task_id in args.tasks if task_id not in available]

    preflight = {
        "docker_cli": docker_available(),
        "docker_python_sdk": docker_python_sdk_available(),
        "tasks_requested": args.tasks,
        "tasks_selected": tasks,
        "tasks_missing": missing,
        "baselines": args.baselines,
        "model": os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL"),
        "provider": os.environ.get("LLM_PROVIDER", "openai"),
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, "preflight": preflight}, indent=2))
        return

    if not docker_python_sdk_available():
        print(
            json.dumps(
                {
                    "blocked": True,
                    "blocker": "docker_python_sdk_permission",
                    "message": "Add user to docker group: sudo usermod -aG docker $USER && newgrp docker",
                    "preflight": preflight,
                },
                indent=2,
            )
        )
        sys.exit(2)

    runs: list[dict[str, Any]] = []
    for baseline_id in args.baselines:
        if baseline_id not in FAITHFUL_TB_BASELINES:
            raise SystemExit(f"Unsupported baseline: {baseline_id}")
        for task_id in tasks:
            started = time.time()
            result = run_tb_smoke(
                baseline_id=baseline_id,
                task_id=task_id,
                dataset_path=dataset,
                output_dir=Path(args.output_dir),
                use_oracle_agent=args.use_oracle,
                timeout_s=args.timeout_s,
                max_shell_steps=8,
            )
            envelope = result.get("envelope", {})
            metrics = envelope.get("metrics_summary", {})
            stderr = result.get("stderr_tail", "")
            runs.append(
                {
                    "baseline_id": baseline_id,
                    "task_id": task_id,
                    "end_task_success": metrics.get("end_task_success"),
                    "final_success_label": envelope.get("final_success_label"),
                    "failure_category": classify_tb_failure(
                        metrics, stderr, run_dir=Path(result.get("run_dir", ""))
                    ),
                    "elapsed_s": result.get("elapsed_s"),
                    "model_calls": metrics.get("model_calls"),
                    "envelope_path": result.get("envelope_path"),
                    "run_dir": result.get("run_dir"),
                }
            )
            print(json.dumps(runs[-1], ensure_ascii=False))

    summary = summarize_runs(runs)
    summary["preflight"] = preflight
    summary["provider"] = preflight["provider"]
    summary["model"] = preflight["model"]
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "total_runs": len(runs)}, indent=2))


if __name__ == "__main__":
    main()
