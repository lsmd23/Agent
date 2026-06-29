#!/usr/bin/env python3
"""Run the Phase 1 toy baseline matrix over seed tasks.

This runner intentionally uses deterministic runtime configurations as toy
baseline simulations. It validates the benchmark/scoring pipeline before any
claim about strong ReAct, workflow, retrieval-memory, or Agent-Attention wins.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent_attention_runtime import build_default_runtime  # noqa: E402


BASELINE_CONFIGS: dict[str, dict[str, Any]] = {
    "single_react_agent": {
        "top_k": 1,
        "memory_enabled": False,
        "verifier_enabled": True,
        "router_strategy": "rule",
        "simulation_note": "Single recurrent controller approximation: one module per step, no cross-task memory.",
    },
    "fixed_workflow_agent": {
        "top_k": 2,
        "memory_enabled": False,
        "verifier_enabled": True,
        "router_strategy": "rule",
        "simulation_note": "Static workflow approximation using rule-biased routing without memory.",
    },
    "retrieval_memory_agent": {
        "top_k": 1,
        "memory_enabled": True,
        "verifier_enabled": True,
        "router_strategy": "rule",
        "simulation_note": "Single-controller-plus-memory approximation: memory enabled, sparse routing limited to one module per step.",
    },
    "agent_attention_agent": {
        "top_k": 2,
        "memory_enabled": True,
        "verifier_enabled": True,
        "router_strategy": "lexical",
        "simulation_note": "Current proposed toy runtime: lexical sparse routing with memory, gates, verifier, and halt logging.",
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def final_failure_reason(final_answer: str | None, success_label: str) -> str | None:
    if success_label == "pass":
        return None
    if not final_answer:
        return "no_final_answer"
    marker = "Finalized because "
    if marker in final_answer:
        return final_answer.split(marker, 1)[1].split(".", 1)[0].strip()
    return "route_or_oracle_mismatch"


def route_proxy_oracle(task: dict[str, Any], route_payload: dict[str, Any]) -> dict[str, Any]:
    expected = task.get("expected_route", {})
    required = set(expected.get("required_modules", []))
    discouraged = set(expected.get("discouraged_modules", []))
    oracle_best_module_id = expected.get("oracle_best_module_id")
    selected = set(str(module) for module in route_payload.get("selected_modules", []))
    candidates = route_payload.get("candidates", [])

    candidate_scores = {
        candidate.get("module_id"): candidate.get("score")
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("score"), (int, float))
    }
    selected_scores = [float(candidate_scores[module]) for module in selected if module in candidate_scores]
    selected_score = max(selected_scores) if selected_scores else None
    oracle_best_score = candidate_scores.get(oracle_best_module_id)

    missing_required = sorted(required - selected)
    selected_discouraged = sorted(discouraged & selected)
    if oracle_best_score is not None and selected_score is not None:
        score_gap = max(0.0, float(oracle_best_score) - float(selected_score))
    else:
        score_gap = 0.0 if not missing_required else 1.0
    proxy_penalty = 0.35 * len(missing_required) + 0.25 * len(selected_discouraged)
    proxy_regret = round(score_gap + proxy_penalty, 6)

    return {
        "oracle_available": False,
        "proxy_available": True,
        "oracle_best_module_id": oracle_best_module_id,
        "selected_score": selected_score,
        "oracle_best_score": oracle_best_score,
        "oracle_regret": None,
        "proxy_regret": proxy_regret,
        "missing_required_modules": missing_required,
        "selected_discouraged_modules": selected_discouraged,
        "rationale": expected.get("route_rationale"),
    }


def add_route_proxy_oracles(task: dict[str, Any], events: list[dict[str, Any]]) -> None:
    for event in events:
        if event.get("kind") == "route" and isinstance(event.get("payload"), dict):
            event["payload"]["oracle"] = route_proxy_oracle(task, event["payload"])


def success_label_for(task: dict[str, Any], state: Any) -> str:
    selected = set(state.selected_modules)
    expected = task.get("expected_route", {})
    required = set(expected.get("required_modules", []))
    discouraged = set(expected.get("discouraged_modules", []))
    required_ok = required.issubset(selected)
    discouraged_ok = not (discouraged & selected)
    verifier_ok = state.verifier_status in {"pass", "skipped"}
    budget_ok = not any("budget" in signal for signal in state.failure_signals)
    if required_ok and discouraged_ok and verifier_ok and budget_ok:
        return "pass"
    if required_ok and verifier_ok:
        return "partial"
    return "fail"


def envelope_for(
    task: dict[str, Any],
    baseline_id: str,
    runtime_config: dict[str, Any],
    state: Any,
    events: list[Any],
) -> dict[str, Any]:
    success_label = success_label_for(task, state)
    run_id = f"phase1_minimal__{baseline_id}__{task['task_id']}"
    known_deviations = [
        "phase1_toy_baseline_simulation",
        "toy_route_oracle_success_label",
        "legacy_event_payloads_inside_target_envelope",
        "toy_scalar_activation_cost_not_full_cost_delta",
        "oracle_route_regret_unavailable",
    ]
    serialized_events = [asdict(event) for event in events]
    add_route_proxy_oracles(task, serialized_events)
    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": run_id,
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": baseline_id,
        "runtime_config": {
            "baseline_config": runtime_config,
            "budget": task["budget"],
            "simulation": True,
        },
        "task_family": task["task_family"],
        "module_registry_snapshot": [],
        "events": serialized_events,
        "final_answer": state.final_answer,
        "final_success_label": success_label,
        "failure_reason": final_failure_reason(state.final_answer, success_label),
        "known_deviations": known_deviations,
        "metrics_summary": {},
    }


def run_matrix(tasks_path: Path, output_dir: Path) -> list[Path]:
    tasks = load_jsonl(tasks_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for task in tasks:
        max_steps = int(task["budget"]["max_steps"])
        max_budget = float(task["budget"]["max_activation_cost"])
        for baseline_id, config in BASELINE_CONFIGS.items():
            runtime = build_default_runtime(
                top_k=int(config["top_k"]),
                max_steps=max_steps,
                memory_enabled=bool(config["memory_enabled"]),
                verifier_enabled=bool(config["verifier_enabled"]),
                router_strategy=str(config["router_strategy"]),
            )
            state = runtime.run(task["prompt"], max_budget=max_budget)
            envelope = envelope_for(task, baseline_id, config, state, runtime.events)
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
    for baseline_id in BASELINE_CONFIGS:
        runs = [run for run in data["runs"] if run["baseline_id"] == baseline_id]
        if not runs:
            continue
        rows.append(
            {
                "baseline_id": baseline_id,
                "run_count": len(runs),
                "success_rate": average([1.0 if run["final"]["task_success"] else 0.0 for run in runs]),
                "mean_cost_normalized_success": average([run["process"]["cost_normalized_success"] for run in runs if run["process"]["cost_normalized_success"] is not None]),
                "mean_activation_cost": average([run["process"]["activation_cost"] for run in runs if run["process"]["activation_cost"] is not None]),
                "mean_module_calls": average([run["process"]["module_calls"] for run in runs if run["process"]["module_calls"] is not None]),
                "mean_repeated_action_ratio": average([run["process"]["repeated_action_ratio"] for run in runs if run["process"]["repeated_action_ratio"] is not None]),
                "budget_exhaustion_rate": average([1.0 if run["process"]["budget_exhaustion"] else 0.0 for run in runs]),
                "premature_halt_rate": average([1.0 if run["process"]["premature_halt"] else 0.0 for run in runs]),
                "mean_route_entropy": average([run["routing"]["route_entropy"] for run in runs if run["routing"]["route_entropy"] is not None]),
                "mean_proxy_route_regret": average([run["routing"]["proxy_route_regret_mean"] for run in runs if run["routing"]["proxy_route_regret_mean"] is not None]),
                "total_memory_reads": sum(run["memory"]["memory_reads"] for run in runs),
                "total_negative_transfer_cases": sum(run["memory"]["negative_transfer_cases"] for run in runs),
                "known_deviations": sorted({item for run in runs for item in run["known_deviations"]}),
            }
        )
    summary = {
        "scope": "Phase 1 minimal matrix grouped by toy baseline simulation.",
        "warning": "These are deterministic toy simulations for pipeline validation, not final strong-baseline results.",
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
    parser = argparse.ArgumentParser(description="Run Phase 1 toy baseline matrix.")
    parser.add_argument("--tasks", default="experiments/tasks/phase0_seed_tasks.jsonl")
    parser.add_argument("--output-dir", default="experiments/trajectories/phase1_minimal_matrix")
    parser.add_argument("--metrics-output", default="experiments/metrics/phase1_minimal_matrix_metrics.json")
    parser.add_argument("--summary-output", default="experiments/metrics/phase1_minimal_matrix_by_baseline.json")
    parser.add_argument("--manifest-output", default="experiments/phase1/phase1_minimal_matrix_manifest.json")
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
