"""AA component ablation specs (Brief C / Track 2)."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import memory_for_task
from experiments.baselines.faithful_runners import AgentAttentionTunedRuntime, default_modules


AA_ABLATION_IDS = (
    "aa_tuned_control",
    "aa_top1",
    "aa_no_adaptive_topk",
    "aa_no_memory",
    "aa_no_verifier",
    "aa_no_budget_gate",
    "aa_no_cost_penalty",
    "aa_lite_escalation",
    "aa_direct_first",
)


ABLATION_SPECS: dict[str, dict[str, Any]] = {
    "aa_tuned_control": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "P2 tuned control",
        "evidence_tier": "direct",
        "matrix_baseline_id": "agent_attention_llm_tuned",
        "note": "Adaptive top-k, strong budget gate, memory on, verifier on.",
        "overrides": {},
        "recommendation_hint": "keep_as_control",
    },
    "aa_top1": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "top-k = 1",
        "evidence_tier": "live_required",
        "matrix_baseline_id": None,
        "overrides": {
            "top_k": 1,
            "max_top_k": 1,
            "adaptive_top_k_enabled": False,
        },
        "recommendation_hint": "gate_if_escalation_only",
    },
    "aa_no_adaptive_topk": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "adaptive top-k off",
        "evidence_tier": "live_required",
        "matrix_baseline_id": None,
        "overrides": {
            "adaptive_top_k_enabled": False,
            "top_k": 2,
            "max_top_k": 2,
        },
        "recommendation_hint": "keep_fixed_top2",
    },
    "aa_no_memory": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "memory off",
        "evidence_tier": "proxy",
        "matrix_baseline_id": None,
        "proxy_baseline_id": "single_react_llm_agent",
        "proxy_note": "No-memory ReAct proxy; Phase2 toy shows +8.3pp success without memory.",
        "overrides": {
            "memory_enabled": False,
            "memory_write_enabled": False,
        },
        "recommendation_hint": "remove_or_gate",
    },
    "aa_no_verifier": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "verifier off",
        "evidence_tier": "live_required",
        "matrix_baseline_id": None,
        "overrides": {"verifier_enabled": False},
        "recommendation_hint": "keep_in_escalation",
    },
    "aa_no_budget_gate": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "no strong budget gate",
        "evidence_tier": "proxy",
        "matrix_baseline_id": None,
        "proxy_baseline_id": "moa_style_llm_agent",
        "proxy_note": "MoA proxy for higher fan-out when budget gate relaxed.",
        "overrides": {
            "strong_budget_gate": False,
            "budget_cost_fraction": 0.0,
        },
        "recommendation_hint": "keep_gate",
    },
    "aa_no_cost_penalty": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "no cost-quality frontier",
        "evidence_tier": "live_required",
        "matrix_baseline_id": None,
        "overrides": {
            "cost_quality_epsilon": 0.0,
            "budget_cost_fraction": 0.0,
        },
        "recommendation_hint": "keep_cost_penalty",
    },
    "aa_lite_escalation": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "AA lite escalation slot",
        "evidence_tier": "live_required",
        "matrix_baseline_id": None,
        "note": "Cascade middle stage: no verifier, no memory, fixed top-k=2, budget gate on.",
        "overrides": {
            "verifier_enabled": False,
            "memory_enabled": False,
            "memory_write_enabled": False,
            "adaptive_top_k_enabled": False,
            "top_k": 2,
            "max_top_k": 2,
            "strong_budget_gate": True,
            "budget_cost_fraction": 0.30,
        },
        "recommendation_hint": "keep_in_escalation_only",
    },
    "aa_direct_first": {
        "baseline_id": "agent_attention_agent_tuned",
        "label": "direct-first (ReAct then AA)",
        "evidence_tier": "direct",
        "matrix_baseline_id": None,
        "cascade_stages": ["single_react_llm_agent", "agent_attention_llm_tuned"],
        "note": "Deployment policy: AA only after cheap ReAct failure.",
        "overrides": {},
        "recommendation_hint": "keep_as_default_route",
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


def build_aa_ablation_runtime(ablation_id: str, task: dict[str, Any], max_steps: int) -> AgentAttentionTunedRuntime:
    if ablation_id not in ABLATION_SPECS:
        raise ValueError(f"Unknown ablation_id={ablation_id!r}")
    if ablation_id == "aa_direct_first":
        raise ValueError("aa_direct_first is a cascade policy; use cascade replay, not runtime build.")

    spec = ABLATION_SPECS[ablation_id]
    overrides = dict(spec.get("overrides", {}))
    memory_enabled = bool(overrides.get("memory_enabled", True))
    memory = memory_for_task(task) if memory_enabled else []

    defaults: dict[str, Any] = {
        "modules": default_modules(),
        "memory": memory,
        "max_steps": max_steps,
        "verifier_threshold": 0.64,
        "verifier_enabled": True,
        "memory_enabled": memory_enabled,
        "memory_write_enabled": bool(overrides.get("memory_write_enabled", memory_enabled)),
        "memory_write_policy": "success_plus_failure",
        "quarantine_aware": False,
        "top_k": 2,
        "max_top_k": 3,
        "router_strategy": "lexical",
        "adaptive_top_k_enabled": True,
        "strong_budget_gate": True,
        "budget_cost_fraction": 0.30,
        "cost_quality_epsilon": 0.05,
    }
    defaults.update(overrides)
    runtime = AgentAttentionTunedRuntime(**defaults)
    runtime.ablation_id = ablation_id
    return runtime
