#!/usr/bin/env python3
"""Phase 4 learned routing comparison: lexical vs rule vs learned vs oracle."""

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
from experiments.phase4.oracle_matrix import build_oracle_matrix, oracle_regret_for_selection  # noqa: E402
from experiments.phase4.router_variants import (  # noqa: E402
    PHASE4_ROUTER_IDS,
    build_router_variant_runtime,
    router_config_for,
)
from experiments.phase4.train_learned_router import train_policy  # noqa: E402


def run_matrix(
    tasks: list[dict[str, Any]],
    output_dir: Path,
    learned_policy_path: Path,
    oracle_matrix: dict[str, Any],
) -> list[Path]:
    from experiments.phase4.learned_router_policy import LearnedRouterPolicy

    learned_policy = LearnedRouterPolicy.load(learned_policy_path)
    oracle_by_task = oracle_matrix["entries_by_task_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for task in tasks:
        max_steps = int(task["budget"]["max_steps"])
        max_budget = float(task["budget"]["max_activation_cost"])
        oracle_entry = oracle_by_task[task["task_id"]]
        for router_id in PHASE4_ROUTER_IDS:
            runtime = build_router_variant_runtime(
                router_id,
                task,
                max_steps,
                learned_policy=learned_policy,
                oracle_utilities=oracle_entry.get("module_utilities"),
            )
            state = runtime.run(task["prompt"], max_budget=max_budget)
            config = router_config_for(router_id)
            envelope = envelope_for(
                task,
                config["baseline_id"],
                config,
                state,
                runtime.events,
                simulation=False,
                run_prefix="phase4_router",
                ablation_id=router_id,
            )
            envelope["router_id"] = router_id
            envelope["oracle_route_regret"] = oracle_regret_for_selection(task, state.selected_modules)
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


def summarize_router(metrics: dict[str, Any], router_id: str) -> dict[str, Any]:
    runs = [
        run
        for run in metrics["runs"]
        if run.get("ablation_id") == router_id or run.get("router_id") == router_id
    ]
    if not runs:
        return {"router_id": router_id, "run_count": 0}

    def avg(getter):
        values = [getter(run) for run in runs]
        values = [value for value in values if value is not None]
        return round(mean(values), 6) if values else None

    return {
        "router_id": router_id,
        "run_count": len(runs),
        "success_rate": avg(lambda run: 1.0 if run["final"]["task_success"] else 0.0),
        "mean_cost_normalized_success": avg(lambda run: run["process"]["cost_normalized_success"]),
        "mean_activation_cost": avg(lambda run: run["process"]["activation_cost"]),
        "mean_proxy_route_regret": avg(lambda run: run["routing"].get("proxy_route_regret_mean")),
        "mean_oracle_route_regret": avg(
            lambda run: (
                run["oracle_route_regret"]
                if run.get("oracle_route_regret") is not None
                else run["routing"].get("oracle_route_regret_mean")
            )
        ),
    }


def write_summary(metrics: dict[str, Any], summary_path: Path, policy_meta: dict[str, Any]) -> dict[str, Any]:
    rows = [summarize_router(metrics, router_id) for router_id in PHASE4_ROUTER_IDS]
    summary = {
        "scope": "Phase 4 router family comparison on tuned Agent-Attention (12 tasks).",
        "control_id": "aa_lexical_router",
        "learned_policy": policy_meta,
        "task_count": len({run["task_id"] for run in metrics["runs"]}),
        "rows": rows,
        "interpretation_hint": (
            "Compare aa_learned_router_replay vs aa_lexical_router on success, proxy regret, "
            "and oracle regret. aa_oracle_router is an upper-bound calibration row, not a deployable policy."
        ),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 learned routing matrix.")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_tasks.jsonl")
    parser.add_argument(
        "--trajectory-dir",
        default="experiments/trajectories/phase1_faithful_matrix",
        help="Trajectories used to augment learned-router training.",
    )
    parser.add_argument("--policy-output", default="experiments/phase4/learned_router_policy.json")
    parser.add_argument("--oracle-output", default="experiments/phase4/oracle_matrix.json")
    parser.add_argument("--output-dir", default="experiments/trajectories/phase4_learned_routing")
    parser.add_argument("--metrics-output", default="experiments/metrics/phase4_learned_routing_metrics.json")
    parser.add_argument("--summary-output", default="experiments/metrics/phase4_learned_routing_summary.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks_path = ROOT / args.tasks
    tasks = load_jsonl(tasks_path)
    policy, oracle_matrix = train_policy(
        tasks_path,
        ROOT / args.trajectory_dir,
        policy_output=ROOT / args.policy_output,
        oracle_output=ROOT / args.oracle_output,
    )
    paths = run_matrix(tasks, ROOT / args.output_dir, ROOT / args.policy_output, oracle_matrix)
    metrics = score_outputs(paths, ROOT / args.metrics_output)
    summary = write_summary(metrics, ROOT / args.summary_output, policy.to_dict())
    print(
        json.dumps(
            {
                "runs": len(paths),
                "policy": args.policy_output,
                "summary": args.summary_output,
                "rows": summary["rows"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
