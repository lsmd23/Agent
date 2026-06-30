"""Live cascade runner: sequential faithful LLM stages until pass or exhaust."""

from __future__ import annotations

from typing import Any

from experiments.cascade.aa_lite_runner import STAGE_AA_LITE, run_aa_lite_llm
from experiments.cascade.cascade_policy import (
    cascade_baseline_id,
    cascade_config_for,
    policy_for,
    policy_id_from_baseline_id,
)
from experiments.real_benchmarks.faithful_llm_runners import run_faithful_llm
from experiments.real_benchmarks.llm_client import LLMClient


def run_cascade_stage(stage_id: str, task: dict[str, Any], client: LLMClient) -> dict[str, Any]:
    if stage_id == STAGE_AA_LITE:
        return run_aa_lite_llm(task, client)
    return run_faithful_llm(stage_id, task, client)


def run_cascade_llm(
    policy_id: str,
    task: dict[str, Any],
    client: LLMClient,
    *,
    baseline_id: str | None = None,
) -> dict[str, Any]:
    """Run cascade policy on one task; each stage uses a fresh client for isolated call counts."""
    policy = policy_for(policy_id)
    stages: list[str] = policy["stages"]
    stage_trajectories: list[dict[str, Any]] = []
    halt_stage: str | None = None
    success = False
    rescued_by: str | None = None

    for stage_id in stages:
        stage_client = LLMClient(
            provider=client.provider,
            model=client.model,
            max_tokens=client.max_tokens,
            temperature=client.temperature,
        )
        trajectory = run_cascade_stage(stage_id, task, stage_client)
        stage_trajectories.append(trajectory)
        if trajectory["final_success_label"] == "pass":
            success = True
            halt_stage = stage_id
            if stage_id != stages[0]:
                rescued_by = stage_id
            break

    if not success:
        halt_stage = stages[-1]

    total_calls = sum(t["metrics_summary"].get("model_calls", 0) for t in stage_trajectories)
    total_tokens = sum(t["metrics_summary"].get("total_tokens", 0) for t in stage_trajectories)
    total_latency = sum(t["metrics_summary"].get("latency_ms", 0) for t in stage_trajectories)
    final = stage_trajectories[-1]
    resolved_baseline_id = baseline_id or cascade_baseline_id(policy_id)
    cascade_cfg = cascade_config_for(policy_id)

    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": f"real_llm__{resolved_baseline_id}__{client.provider}__{client.model.replace('/', '_')}__{task['task_id']}",
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": resolved_baseline_id,
        "task_family": task.get("task_family", ""),
        "final_answer": final.get("final_answer"),
        "final_success_label": "pass" if success else "fail",
        "known_deviations": [
            "cascade_multi_stage_faithful_llm",
            "stages_halt_on_first_pytest_pass",
            *(final.get("known_deviations") or []),
        ],
        "runtime_config": {
            "provider": client.provider,
            "model": client.model,
            "baseline_config": cascade_cfg,
            "cascade_policy_id": policy_id,
            "cascade_stages": stages,
            "stages_run": len(stage_trajectories),
            "halt_stage": halt_stage,
            "rescued_by": rescued_by,
            "model_calls": total_calls,
        },
        "cascade": {
            "policy_id": policy_id,
            "policy_label": policy["label"],
            "halt_stage": halt_stage,
            "escalated": len(stage_trajectories) > 1,
            "rescued_by": rescued_by,
            "stage_trajectories": [
                {
                    "baseline_id": t["baseline_id"],
                    "run_id": t["run_id"],
                    "final_success_label": t["final_success_label"],
                    "model_calls": t["metrics_summary"].get("model_calls", 0),
                    "total_tokens": t["metrics_summary"].get("total_tokens", 0),
                    "latency_ms": t["metrics_summary"].get("latency_ms", 0),
                }
                for t in stage_trajectories
            ],
        },
        "events": final.get("events", []),
        "metrics_summary": {
            **(final.get("metrics_summary") or {}),
            "model_calls": total_calls,
            "total_tokens": total_tokens,
            "latency_ms": total_latency,
            "cascade_policy_id": policy_id,
            "stages_run": len(stage_trajectories),
            "halt_stage": halt_stage,
            "escalated": len(stage_trajectories) > 1,
            "rescued_by": rescued_by,
        },
    }


def summarize_cascade_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(runs) or 1
    correct = sum(1 for r in runs if r["final_success_label"] == "pass")
    calls = [r["metrics_summary"].get("model_calls", 0) for r in runs]
    tokens = [r["metrics_summary"].get("total_tokens", 0) for r in runs]
    latencies = [r["metrics_summary"].get("latency_ms", 0) for r in runs]
    mean_calls = sum(calls) / n
    return {
        "runs": n,
        "correct": correct,
        "accuracy": correct / n,
        "mean_model_calls": round(mean_calls, 4),
        "mean_total_tokens": round(sum(tokens) / n, 2),
        "mean_latency_ms": round(sum(latencies) / n, 2),
        "cost_normalized_success": round((correct / n) / mean_calls, 4) if mean_calls else 0.0,
        "escalation_rate": round(
            sum(1 for r in runs if r.get("cascade", {}).get("escalated")) / n,
            4,
        ),
        "rescued_task_count": sum(1 for r in runs if r.get("cascade", {}).get("rescued_by")),
    }


def run_cascade_baseline_llm(
    baseline_id: str,
    task: dict[str, Any],
    client: LLMClient,
) -> dict[str, Any]:
    """Entry point for unified eval harness (`run_real_llm_eval.py`)."""
    policy_id = policy_id_from_baseline_id(baseline_id)
    return run_cascade_llm(policy_id, task, client, baseline_id=baseline_id)
