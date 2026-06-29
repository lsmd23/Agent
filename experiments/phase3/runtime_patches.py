"""Apply textual update patches to tuned Agent-Attention runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from experiments.baselines.memory_ablations import build_memory_ablation_runtime
from experiments.baselines.faithful_runners import AgentAttentionTunedRuntime
from src.agent_attention_runtime import ModuleSpec, RouteDecision, RuntimeState, route_intent_bonus, tokenize


@dataclass
class RuntimePatch:
    patch_id: str
    update_target: str
    target_id: str
    parameters: dict[str, Any] = field(default_factory=dict)


def patches_from_attribution(attribution: dict[str, Any]) -> list[RuntimePatch]:
    proposed = attribution["proposed_update"]
    update_id = f"patch__{attribution['case_id']}"
    params = dict(proposed.get("patch_parameters", {}))
    return [
        RuntimePatch(
            patch_id=update_id,
            update_target=proposed["target"],
            target_id=proposed["target_id"],
            parameters=params,
        )
    ]


class PatchedTunedRuntime(AgentAttentionTunedRuntime):
    """Tuned runtime with bounded textual patches from Phase 3 backprop."""

    def __init__(
        self,
        *,
        patches: list[RuntimePatch] | None = None,
        task_family: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.patches = list(patches or [])
        self.task_family = task_family or ""
        self._apply_config_patches()

    def _apply_config_patches(self) -> None:
        for patch in self.patches:
            if patch.update_target == "memory_write_policy" and patch.parameters.get("quarantine_aware"):
                self.quarantine_aware = True
            if patch.update_target == "halt_threshold":
                if patch.parameters.get("require_verifier_on_code_tasks") and self.task_family == "code_agent_task":
                    cap = float(patch.parameters.get("verifier_threshold_cap", 0.50))
                    self.verifier_threshold = min(self.verifier_threshold, cap)
                    self.verifier_enabled = True

    def _patch_applies(self, patch: RuntimePatch) -> bool:
        if patch.update_target == "router_rule":
            if patch.target_id in {"budget_conservation", "global"}:
                return True
            return patch.target_id == self.task_family
        return True

    def module_gate_reject_reason(self, module: ModuleSpec, gate_status: dict[str, str]) -> str | None:
        reason = super().module_gate_reject_reason(module, gate_status)
        if reason:
            return reason
        for patch in self.patches:
            if not self._patch_applies(patch):
                continue
            if patch.update_target != "router_rule":
                continue
            discouraged = patch.parameters.get("discouraged_modules", [])
            if module.module_id in discouraged:
                return "patch_discouraged_module"
        return None

    def effective_top_k(self, state: RuntimeState, gate_decisions: list[dict]) -> int:
        effective_k = super().effective_top_k(state, gate_decisions)
        remaining_budget = max(state.max_budget - state.budget_used, 0.0)
        for patch in self.patches:
            if not self._patch_applies(patch):
                continue
            if patch.update_target != "router_rule":
                continue
            if patch.parameters.get("cap_top_k") is not None:
                threshold = float(patch.parameters.get("budget_threshold", 1.0))
                if remaining_budget < threshold:
                    effective_k = min(effective_k, int(patch.parameters["cap_top_k"]))
            if patch.parameters.get("force_top_k") is not None:
                effective_k = min(effective_k, int(patch.parameters["force_top_k"]))
        return effective_k

    def route(self, state: RuntimeState, gate_decisions: list[dict]) -> list[RouteDecision]:
        decisions = super().route(state, gate_decisions)
        bonus_modules: dict[str, float] = {}
        for patch in self.patches:
            if not self._patch_applies(patch):
                continue
            if patch.update_target != "router_rule":
                continue
            delta = float(patch.parameters.get("intent_bonus_delta", 0.25))
            for module_id in patch.parameters.get("intent_bonus_for", []):
                bonus_modules[module_id] = bonus_modules.get(module_id, 0.0) + delta
            max_step = int(patch.parameters.get("early_priority_max_step", 2))
            if state.step <= max_step:
                bonus = float(patch.parameters.get("early_priority_bonus", 1.5))
                for module_id in patch.parameters.get("early_priority_modules", []):
                    bonus_modules[module_id] = max(bonus_modules.get(module_id, 0.0), bonus)

        if not bonus_modules:
            return decisions

        query_tokens = tokenize(state.query_text())
        rescored: list[RouteDecision] = []
        for decision in decisions:
            extra = bonus_modules.get(decision.module_id, 0.0)
            if extra <= 0:
                rescored.append(decision)
                continue
            intent = route_intent_bonus(query_tokens, decision.module_id, state.failure_signals)
            score_terms = dict(decision.score_terms)
            score_terms["semantic_match"] = round(score_terms.get("semantic_match", 0.0) + extra + intent * 0.1, 4)
            score = round(
                sum(score_terms[key] * decision.score_weights[key] for key in decision.score_weights),
                4,
            )
            reject_reason = decision.reject_reason
            if reject_reason in {None, "below_top_k", "low_score"} and decision.budget_valid and decision.risk_valid:
                reject_reason = None
            rescored.append(
                RouteDecision(
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
        final: list[RouteDecision] = []
        for item in rescored:
            selected = item.module_id in selected_ids
            reject_reason = item.reject_reason
            if not selected and reject_reason is None:
                reject_reason = "below_top_k" if item.score > 0 else "low_score"
            final.append(
                RouteDecision(
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


def build_patched_runtime(
    task: dict[str, Any],
    max_steps: int,
    patches: list[RuntimePatch],
    *,
    ablation_id: str = "aa_tuned_control",
) -> PatchedTunedRuntime:
    base = build_memory_ablation_runtime(ablation_id, task, max_steps)
    return PatchedTunedRuntime(
        modules=list(base.modules.values()),
        memory=list(base.memory),
        max_steps=max_steps,
        verifier_threshold=base.verifier_threshold,
        verifier_enabled=base.verifier_enabled,
        memory_enabled=base.memory_enabled,
        memory_write_enabled=base.memory_write_enabled,
        memory_write_policy=base.memory_write_policy,
        quarantine_aware=base.quarantine_aware,
        adaptive_top_k_enabled=base.adaptive_top_k_enabled,
        strong_budget_gate=base.strong_budget_gate,
        budget_cost_fraction=base.budget_cost_fraction,
        cost_quality_epsilon=base.cost_quality_epsilon,
        top_k=base.top_k,
        max_top_k=base.max_top_k,
        patches=patches,
        task_family=task.get("task_family", ""),
    )
