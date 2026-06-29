"""Phase 2 memory ablations on tuned Agent-Attention control."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import memory_for_task, primary_executor_for_task
from experiments.baselines.faithful_runners import AgentAttentionTunedRuntime, default_modules


MEMORY_ABLATION_IDS = (
    "aa_tuned_control",
    "aa_no_memory",
    "aa_memory_read_only",
    "aa_success_only_memory_write",
    "aa_unfiltered_memory",
    "aa_quarantine_aware",
)


ABLATION_SPECS: dict[str, dict[str, Any]] = {
    "aa_tuned_control": {
        "baseline_id": "agent_attention_agent_tuned",
        "memory_enabled": True,
        "memory_write_enabled": True,
        "memory_write_policy": "success_plus_failure",
        "quarantine_at_load": True,
        "quarantine_aware": False,
        "note": "P2 tuned control with default load-time quarantine.",
    },
    "aa_no_memory": {
        "baseline_id": "agent_attention_agent_tuned",
        "memory_enabled": False,
        "memory_write_enabled": False,
        "memory_write_policy": "none",
        "quarantine_at_load": True,
        "quarantine_aware": False,
        "note": "Disable memory read/write and memory_bonus routing.",
    },
    "aa_memory_read_only": {
        "baseline_id": "agent_attention_agent_tuned",
        "memory_enabled": True,
        "memory_write_enabled": False,
        "memory_write_policy": "none",
        "quarantine_at_load": True,
        "quarantine_aware": False,
        "note": "Allow memory reads; disable all writes/reflections to memory store.",
    },
    "aa_success_only_memory_write": {
        "baseline_id": "agent_attention_agent_tuned",
        "memory_enabled": True,
        "memory_write_enabled": True,
        "memory_write_policy": "success_only",
        "quarantine_at_load": True,
        "quarantine_aware": False,
        "note": "Write memory only after successful final signal.",
    },
    "aa_unfiltered_memory": {
        "baseline_id": "agent_attention_agent_tuned",
        "memory_enabled": True,
        "memory_write_enabled": True,
        "memory_write_policy": "success_plus_failure",
        "quarantine_at_load": False,
        "quarantine_aware": False,
        "note": "Load harmful/stale memories; no read-time quarantine filter.",
    },
    "aa_quarantine_aware": {
        "baseline_id": "agent_attention_agent_tuned",
        "memory_enabled": True,
        "memory_write_enabled": True,
        "memory_write_policy": "success_plus_failure",
        "quarantine_at_load": False,
        "quarantine_aware": True,
        "note": "Load harmful memories but filter harmful reads at retrieval time.",
    },
}


def ablation_config_for(ablation_id: str) -> dict[str, Any]:
    spec = ABLATION_SPECS.get(ablation_id, {})
    return {
        "ablation_id": ablation_id,
        "control_id": "aa_tuned_control",
        "baseline_id": spec.get("baseline_id", "agent_attention_agent_tuned"),
        **spec,
    }


def build_memory_ablation_runtime(ablation_id: str, task: dict[str, Any], max_steps: int) -> AgentAttentionTunedRuntime:
    if ablation_id not in ABLATION_SPECS:
        raise ValueError(f"Unknown ablation_id={ablation_id!r}")

    spec = ABLATION_SPECS[ablation_id]
    memory_enabled = bool(spec["memory_enabled"])
    memory = (
        memory_for_task(task, quarantine_at_load=bool(spec.get("quarantine_at_load", True)))
        if memory_enabled
        else []
    )

    return AgentAttentionTunedRuntime(
        modules=default_modules(),
        memory=memory,
        max_steps=max_steps,
        verifier_threshold=0.64,
        verifier_enabled=True,
        memory_enabled=memory_enabled,
        memory_write_enabled=bool(spec.get("memory_write_enabled", True)),
        memory_write_policy=str(spec.get("memory_write_policy", "success_plus_failure")),
        quarantine_aware=bool(spec.get("quarantine_aware", False)),
        adaptive_top_k_enabled=True,
        strong_budget_gate=True,
        budget_cost_fraction=0.30,
        cost_quality_epsilon=0.05,
    )
