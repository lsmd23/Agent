"""Shared live LLM runners for AA component ablations."""

from __future__ import annotations

from typing import Any

from experiments.ablations.aa_ablation_specs import ablation_config_for, build_aa_ablation_runtime
from experiments.baselines.faithful_runners import baseline_config_for
from experiments.real_benchmarks.faithful_llm_runners import (
    AgentAttentionTunedLLMRuntime,
    build_memory_ablation_llm_runtime,
)
from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.llm_executors import default_module_specs
from experiments.real_benchmarks.real_llm_envelope import envelope_for_real_llm


def build_aa_ablation_llm_runtime(
    ablation_id: str,
    task: dict[str, Any],
    client: LLMClient,
    max_steps: int,
) -> AgentAttentionTunedLLMRuntime:
    if ablation_id == "aa_no_memory":
        return build_memory_ablation_llm_runtime("aa_no_memory", task, client, max_steps)

    toy = build_aa_ablation_runtime(ablation_id, task, max_steps)
    runtime = AgentAttentionTunedLLMRuntime(
        client=client,
        task=task,
        modules=default_module_specs(),
        memory=toy.memory,
        max_steps=toy.max_steps,
        verifier_threshold=toy.verifier_threshold,
        verifier_enabled=toy.verifier_enabled,
        memory_enabled=toy.memory_enabled,
        memory_write_enabled=toy.memory_write_enabled,
        memory_write_policy=toy.memory_write_policy,
        quarantine_aware=toy.quarantine_aware,
        top_k=toy.top_k,
        max_top_k=toy.max_top_k,
        router_strategy=toy.router_strategy,
        adaptive_top_k_enabled=toy.adaptive_top_k_enabled,
        strong_budget_gate=toy.strong_budget_gate,
        budget_cost_fraction=toy.budget_cost_fraction,
        cost_quality_epsilon=toy.cost_quality_epsilon,
        task_family=task.get("task_family", ""),
    )
    runtime.ablation_id = ablation_id
    return runtime


def run_aa_ablation_llm(
    ablation_id: str,
    task: dict[str, Any],
    client: LLMClient,
    *,
    report_baseline_id: str | None = None,
) -> dict[str, Any]:
    budget = task.get("budget", {})
    max_steps = int(budget.get("max_steps", 4))
    max_budget = float(budget.get("max_activation_cost", 5.0))
    runtime = build_aa_ablation_llm_runtime(ablation_id, task, client, max_steps)
    state = runtime.run(task["prompt"], max_budget=max_budget)
    envelope = envelope_for_real_llm(
        task,
        report_baseline_id or "agent_attention_llm_tuned",
        state,
        runtime.events,
        client,
        baseline_config=ablation_config_for(ablation_id),
        ablation_id=f"{ablation_id}_llm",
        extra_known_deviations=[f"aa_component_ablation:{ablation_id}"],
    )
    envelope["ablation_id"] = ablation_id
    if report_baseline_id:
        envelope["baseline_id"] = report_baseline_id
    return envelope
