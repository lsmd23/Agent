#!/usr/bin/env python3
"""Smoke runner for Terminal-Bench adapter with local fallback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402
from experiments.terminal_bench.adapter import (  # noqa: E402
    FAITHFUL_TB_BASELINES,
    docker_available,
    dataset_path_exists,
    list_task_ids,
    run_adapter_smoke,
    run_local_code_fallback,
    run_tb_smoke,
    tb_cli_available,
)

load_project_env(start=_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Terminal-Bench / local fallback smoke runner.")
    parser.add_argument("--mode", choices=["auto", "tb", "local"], default="auto")
    parser.add_argument("--baseline", choices=FAITHFUL_TB_BASELINES, default="single_react_llm_agent")
    parser.add_argument("--task-id")
    parser.add_argument("--dataset-path", default="external/terminal-bench-core")
    parser.add_argument("--use-oracle", action="store_true", help="Use TB oracle agent instead of faithful agent.")
    parser.add_argument("--local-tasks", default="experiments/tasks/phase1_code_tasks.jsonl")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = Path(args.dataset_path)
    status = {
        "docker_available": docker_available(),
        "tb_cli_available": tb_cli_available(),
        "dataset_available": dataset_path_exists(dataset),
        "listed_tasks": list_task_ids(dataset, limit=5) if dataset_path_exists(dataset) else [],
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, "status": status}, indent=2))
        return

    if args.mode == "local":
        result = run_local_code_fallback(
            baseline_id=args.baseline,
            tasks_path=_ROOT / args.local_tasks,
            limit=args.limit,
        )
    elif args.mode == "tb":
        result = run_tb_smoke(
            baseline_id=args.baseline,
            task_id=args.task_id,
            dataset_path=dataset,
            use_oracle_agent=args.use_oracle,
        )
    else:
        result = run_adapter_smoke(prefer_tb=True, fallback_limit=args.limit)

    print(json.dumps({"status": status, "result": result}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
