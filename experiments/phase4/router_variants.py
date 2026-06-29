"""Phase 4 router variant builders on tuned Agent-Attention."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import memory_for_task
from experiments.baselines.faithful_runners import AgentAttentionTunedRuntime, default_modules
from experiments.phase4.learned_router_policy import LearnedRouterPolicy


PHASE4_ROUTER_IDS = (
    "aa_lexical_router",
    "aa_rule_router",
    "aa_learned_router_replay",
    "aa_oracle_router",
)


ROUTER_SPECS: dict[str, dict[str, Any]] = {
    "aa_lexical_router": {
        "router_strategy": "lexical",
        "note": "P2 tuned control with lexical semantic_match (Phase 0 default).",
    },
    "aa_rule_router": {
        "router_strategy": "rule",
        "note": "P2 tuned with deterministic rule semantic_match.",
    },
    "aa_learned_router_replay": {
        "router_strategy": "learned",
        "note": "P2 tuned with trajectory+oracle-trained logistic router.",
    },
    "aa_oracle_router": {
        "router_strategy": "oracle",
        "note": "Upper-bound oracle semantic routing for regret calibration.",
    },
}


def router_config_for(router_id: str) -> dict[str, Any]:
    spec = ROUTER_SPECS.get(router_id, {})
    return {"router_id": router_id, "baseline_id": "agent_attention_agent_tuned", **spec}


class OracleRouterTunedRuntime(AgentAttentionTunedRuntime):
    """Routes using offline oracle utilities as semantic_match."""

    baseline_id = "agent_attention_agent_tuned_oracle"
    routing_policy_label = "oracle_upper_bound"

    def __init__(self, *, oracle_utilities: dict[str, float] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.oracle_utilities = oracle_utilities or {}

    def route(self, state, gate_decisions):  # type: ignore[no-untyped-def]
        decisions = super().route(state, gate_decisions)
        if not self.oracle_utilities:
            return decisions
        rescored = []
        for decision in decisions:
            utility = float(self.oracle_utilities.get(decision.module_id, 0.0))
            score_terms = dict(decision.score_terms)
            score_terms["semantic_match"] = round(utility, 4)
            score = round(sum(score_terms[key] * decision.score_weights[key] for key in decision.score_weights), 4)
            reject_reason = decision.reject_reason
            if reject_reason in {None, "below_top_k", "low_score"} and decision.budget_valid and decision.risk_valid:
                reject_reason = None
            rescored.append(
                decision.__class__(
                    module_id=decision.module_id,
                    score=score,
                    score_terms=score_terms,
                    score_weights=decision.score_weights,
                    selected=False,
                    budget_valid=decision.budget_valid,
                    risk_valid=decision.risk_valid,
                    reject_reason=reject_reason,
                )
            )
        eligible = [item for item in rescored if item.reject_reason is None and item.score > 0.0]
        eligible.sort(key=lambda item: item.score, reverse=True)
        effective_k = self.effective_top_k(state, gate_decisions)
        selected_ids = {item.module_id for item in eligible[:effective_k]}
        final = []
        for item in rescored:
            selected = item.module_id in selected_ids
            reject_reason = item.reject_reason
            if not selected and reject_reason is None:
                reject_reason = "below_top_k" if item.score > 0 else "low_score"
            final.append(
                item.__class__(
                    module_id=item.module_id,
                    score=item.score,
                    score_terms=item.score_terms,
                    score_weights=item.score_weights,
                    selected=selected,
                    budget_valid=item.budget_valid,
                    risk_valid=item.risk_valid,
                    reject_reason=reject_reason if not selected else None,
                )
            )
        final.sort(key=lambda item: item.score, reverse=True)
        return final


def build_router_variant_runtime(
    router_id: str,
    task: dict[str, Any],
    max_steps: int,
    *,
    learned_policy: LearnedRouterPolicy | None = None,
    oracle_utilities: dict[str, float] | None = None,
) -> AgentAttentionTunedRuntime:
    if router_id not in ROUTER_SPECS:
        raise ValueError(f"Unknown router_id={router_id!r}")

    spec = ROUTER_SPECS[router_id]
    memory = memory_for_task(task, quarantine_at_load=True)
    common: dict[str, Any] = {
        "modules": default_modules(),
        "memory": memory,
        "max_steps": max_steps,
        "verifier_threshold": 0.64,
        "verifier_enabled": True,
        "memory_enabled": True,
        "memory_write_enabled": True,
        "memory_write_policy": "success_plus_failure",
        "quarantine_aware": False,
        "adaptive_top_k_enabled": True,
        "strong_budget_gate": True,
        "budget_cost_fraction": 0.30,
        "cost_quality_epsilon": 0.05,
        "task_family": task.get("task_family", ""),
    }

    if router_id == "aa_oracle_router":
        return OracleRouterTunedRuntime(oracle_utilities=oracle_utilities or {}, **common)

    if router_id == "aa_learned_router_replay":
        if learned_policy is None:
            raise ValueError("learned_policy is required for aa_learned_router_replay")
        bound = learned_policy.bind_task_family(task.get("task_family", ""))

        def semantic_fn(state, module, query_tokens):  # type: ignore[no-untyped-def]
            return bound.semantic_match(state, module, query_tokens)

        return AgentAttentionTunedRuntime(
            router_strategy="learned",
            learned_semantic_fn=semantic_fn,
            learned_router_version=bound.version,
            **common,
        )

    return AgentAttentionTunedRuntime(router_strategy=spec["router_strategy"], **common)
