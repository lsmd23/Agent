"""Trajectory envelope builder for real LLM runs."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from experiments.baselines.common import add_route_proxy_oracles, final_failure_reason
from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.task_oracles import evaluate_task_success


def envelope_for_real_llm(
    task: dict[str, Any],
    baseline_id: str,
    state: Any,
    events: list[Any],
    client: LLMClient,
    *,
    baseline_config: dict[str, Any] | None = None,
    run_prefix: str = "real_llm",
    ablation_id: str | None = None,
    router_id: str | None = None,
    extra_known_deviations: list[str] | None = None,
) -> dict[str, Any]:
    success_label, oracle_metrics = evaluate_task_success(task, state)
    run_id = f"{run_prefix}__{baseline_id}__{client.provider}__{client.model.replace('/', '_')}__{task['task_id']}"
    if ablation_id:
        run_id = f"{run_prefix}__{ablation_id}__{client.provider}__{client.model.replace('/', '_')}__{task['task_id']}"
    if router_id:
        run_id = f"{run_prefix}__{router_id}__{client.provider}__{client.model.replace('/', '_')}__{task['task_id']}"

    known_deviations = [
        "real_llm_module_executors",
        "real_model_calls_logged",
        "toy_scalar_activation_cost_not_full_token_cost",
    ]
    if oracle_metrics.get("oracle_type") == "route_proxy":
        known_deviations.append("route_proxy_success_label")
    if extra_known_deviations:
        known_deviations.extend(extra_known_deviations)

    serialized_events = [asdict(event) for event in events]
    add_route_proxy_oracles(task, serialized_events)
    total_latency = sum(call["latency_ms"] for call in client.calls)

    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": run_id,
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": baseline_id,
        "ablation_id": ablation_id,
        "router_id": router_id,
        "runtime_config": {
            "provider": client.provider,
            "model": client.model,
            "baseline_config": baseline_config or {},
            "budget": task.get("budget", {}),
            "model_calls": len(client.calls),
            "selected_modules": list(state.selected_modules),
        },
        "task_family": task.get("task_family", ""),
        "events": serialized_events,
        "final_answer": state.final_answer,
        "final_success_label": success_label,
        "failure_reason": final_failure_reason(state.final_answer, success_label),
        "known_deviations": known_deviations,
        "metrics_summary": {
            **oracle_metrics,
            "model_calls": len(client.calls),
            "latency_ms": total_latency,
            "selected_modules": list(state.selected_modules),
        },
    }


def envelope_for_standalone_llm(
    task: dict[str, Any],
    baseline_id: str,
    client: LLMClient,
    *,
    events: list[dict[str, Any]],
    final_answer: str,
    success_label: str,
    oracle_metrics: dict[str, Any],
    known_deviations: list[str],
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total_latency = sum(call["latency_ms"] for call in client.calls)
    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": f"real_llm__{baseline_id}__{client.provider}__{client.model.replace('/', '_')}__{task['task_id']}",
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": baseline_id,
        "runtime_config": {
            "provider": client.provider,
            "model": client.model,
            **(runtime_config or {}),
            "model_calls": len(client.calls),
        },
        "task_family": task.get("task_family", ""),
        "events": events,
        "final_answer": final_answer,
        "final_success_label": success_label,
        "failure_reason": None if success_label == "pass" else "exact_match_failed",
        "known_deviations": known_deviations,
        "metrics_summary": {
            **oracle_metrics,
            "model_calls": len(client.calls),
            "latency_ms": total_latency,
        },
        "timestamp": time.time(),
    }
