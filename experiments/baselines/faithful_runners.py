"""Faithful baseline runners with distinct control policies."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from experiments.baselines.common import memory_for_task, primary_executor_for_task
from src.agent_attention_runtime import (
    AgentAttentionRuntime,
    ModuleSpec,
    RouteDecision,
    RuntimeState,
    SCORE_WEIGHTS,
    build_default_runtime,
    route_intent_bonus,
    tokenize,
)


REACT_MODULE_ORDER = ("code_agent", "search_agent", "critic_agent", "aggregator")
MOA_PROPOSERS = ("code_agent", "search_agent", "critic_agent")
WORKFLOW_STAGES = ("planner", "executor", "critic", "summarizer")

FAITHFUL_BASELINE_IDS = (
    "single_react_agent",
    "fixed_workflow_agent",
    "full_history_agent",
    "retrieval_memory_agent",
    "moa_style_agent",
    "agent_attention_agent",
)


def default_modules() -> list[ModuleSpec]:
    template = build_default_runtime()
    return list(template.modules.values())


def react_next_module(
    state: RuntimeState,
    executor_module: str | None = None,
    discouraged_modules: set[str] | None = None,
) -> str:
    """Single-controller ReAct policy: one action per step, no sparse router."""
    discouraged = discouraged_modules or set()
    query_tokens = tokenize(state.query_text())

    def allowed(module_id: str) -> bool:
        return module_id not in discouraged

    if state.failure_signals and "critic_agent" not in state.selected_modules[-2:] and allowed("critic_agent"):
        return "critic_agent"
    if state.step <= 1:
        if executor_module and allowed(executor_module):
            return executor_module
        if query_tokens & {"code", "test", "tests", "bug", "fix", "python", "repo"} and allowed("code_agent"):
            return "code_agent"
        if query_tokens & {"research", "paper", "evidence", "search", "source", "sources", "metric", "metrics"} and allowed("search_agent"):
            return "search_agent"
    if state.confidence < 0.65 and "aggregator" not in state.selected_modules[-1:] and allowed("aggregator"):
        return "aggregator"
    if executor_module and executor_module not in state.selected_modules and allowed(executor_module):
        return executor_module
    for module_id in REACT_MODULE_ORDER:
        if module_id not in state.selected_modules and allowed(module_id):
            return module_id
    for module_id in REACT_MODULE_ORDER:
        if allowed(module_id):
            return module_id
    return "aggregator"


class FaithfulRuntimeBase(AgentAttentionRuntime):
    """Base for faithful baselines with explicit routing_policy logging."""

    baseline_id: str = "faithful_base"
    routing_policy_label: str = "none"

    def route_decisions_for_modules(
        self,
        state: RuntimeState,
        selected_ids: list[str],
        gate_decisions: list[dict],
    ) -> list[RouteDecision]:
        gate_status = {item["gate"]: item["status"] for item in gate_decisions}
        remaining_budget = max(state.max_budget - state.budget_used, 0.0)
        memory_bonus_by_module = self.memory_bonus_by_module()
        decisions: list[RouteDecision] = []

        for module in self.modules.values():
            if module.module_id == "verifier":
                continue
            budget_valid = module.cost <= remaining_budget
            gate_reason = self.module_gate_reject_reason(module, gate_status)
            selected = module.module_id in selected_ids
            reject_reason = None
            if not selected:
                if not budget_valid:
                    reject_reason = "budget_exceeded"
                elif gate_reason:
                    reject_reason = gate_reason
                else:
                    reject_reason = "policy_not_selected"
            elif not budget_valid:
                reject_reason = "budget_exceeded"
                selected = False
            elif gate_reason:
                reject_reason = gate_reason
                selected = False

            decisions.append(
                RouteDecision(
                    module_id=module.module_id,
                    score=1.0 if selected else 0.0,
                    score_terms={
                        "semantic_match": round(
                            route_intent_bonus(tokenize(state.query_text()), module.module_id, state.failure_signals),
                            4,
                        ),
                        "reliability": round(module.reliability, 4),
                        "historical_success": round(module.historical_success, 4),
                        "cost": round(module.cost, 4),
                        "latency": round(module.latency, 4),
                        "risk": round(module.risk, 4),
                        "repetition": round(state.selected_modules.count(module.module_id), 4),
                        "memory_bonus": round(memory_bonus_by_module.get(module.module_id, 0.0), 4),
                    },
                    score_weights=SCORE_WEIGHTS.copy(),
                    selected=selected,
                    budget_valid=budget_valid,
                    risk_valid=module.risk < 0.8,
                    reject_reason=reject_reason,
                )
            )
        decisions.sort(key=lambda item: item.score, reverse=True)
        return decisions


class SingleReActRuntime(FaithfulRuntimeBase):
    baseline_id = "single_react_agent"
    routing_policy_label = "react_loop"

    def __init__(
        self,
        executor_module: str | None = None,
        discouraged_modules: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("memory_enabled", False)
        kwargs.setdefault("top_k", 1)
        kwargs.setdefault("router_strategy", "rule")
        super().__init__(**kwargs)
        self.executor_module = executor_module
        self.discouraged_modules = discouraged_modules or set()

    def route(self, state: RuntimeState, gate_decisions: list[dict]) -> list[RouteDecision]:
        next_module = react_next_module(state, self.executor_module, self.discouraged_modules)
        return self.route_decisions_for_modules(state, [next_module], gate_decisions)


class RetrievalMemoryRuntime(SingleReActRuntime):
    baseline_id = "retrieval_memory_agent"
    routing_policy_label = "react_loop_with_memory"

    def __init__(
        self,
        executor_module: str | None = None,
        discouraged_modules: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("memory_enabled", True)
        super().__init__(
            executor_module=executor_module,
            discouraged_modules=discouraged_modules,
            **kwargs,
        )


class FullHistoryRuntime(SingleReActRuntime):
    baseline_id = "full_history_agent"
    routing_policy_label = "react_full_history"

    def __init__(
        self,
        executor_module: str | None = None,
        discouraged_modules: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            executor_module=executor_module,
            discouraged_modules=discouraged_modules,
            **kwargs,
        )

    def run(self, task: str, max_budget: float = 4.0) -> RuntimeState:
        state = RuntimeState(goal=task, max_budget=max_budget)
        self.events = []
        self.current_memory_reads = []
        self._log(state, "start", {"goal": task, "config": self.config_snapshot(), "full_history": True})
        while state.step < self.max_steps:
            state.step += 1
            state.observations.append(f"FullHistory: step={state.step} transcript_size={len(state.observations)}")
            self._log(state, "memory_retrieval", {"enabled": False, "items": []})
            gate_decisions = self.apply_gates(state)
            self._log(state, "gates", {"decisions": gate_decisions, "budget_snapshot": self.budget_snapshot(state)})
            route = self.route(state, gate_decisions)
            self._log(
                state,
                "route",
                {
                    "decision_id": f"route-{state.step}",
                    "routing_policy": self.routing_policy_label,
                    "top_k": 1,
                    "query": " ".join(state.observations),
                    "selected_modules": [decision.module_id for decision in route if decision.selected],
                    "candidates": [
                        {
                            "module_id": decision.module_id,
                            "score": decision.score,
                            "score_terms": decision.score_terms,
                            "selected": decision.selected,
                            "reject_reason": decision.reject_reason,
                        }
                        for decision in route
                    ],
                    "budget_snapshot": self.budget_snapshot(state),
                },
            )
            outputs = self.execute(state, [decision for decision in route if decision.selected])
            self._log(state, "module_execution", {"outputs": [asdict(output) for output in outputs]})
            self.aggregate(state, outputs)
            self._log(state, "state_update", {"action_type": "aggregate", "state": self.state_snapshot(state)})
            verifier_payload = self.maybe_verify(state)
            self._log(state, "verifier_result", verifier_payload)
            halt, reason = self.should_halt(state)
            self._log(state, "halt_gate", self.halt_payload(state, halt, reason))
            if halt:
                break
        if state.final_answer is None:
            state.final_answer = self.compose_final_answer(state, "max_steps_reached")
        self.write_reflection(state)
        self._log(state, "finish", self.state_snapshot(state))
        return state


class FixedWorkflowRuntime(FaithfulRuntimeBase):
    baseline_id = "fixed_workflow_agent"
    routing_policy_label = "static_workflow"

    def __init__(self, executor_module: str, **kwargs: Any) -> None:
        kwargs.setdefault("memory_enabled", False)
        kwargs.setdefault("top_k", 1)
        kwargs.setdefault("router_strategy", "rule")
        super().__init__(**kwargs)
        self.executor_module = executor_module
        self._stage_index = 0

    def workflow_module_for_stage(self, stage: str) -> str:
        if stage == "planner":
            return "critic_agent"
        if stage == "executor":
            return self.executor_module
        if stage == "critic":
            return "critic_agent"
        if stage == "summarizer":
            return "aggregator"
        return "aggregator"

    def route(self, state: RuntimeState, gate_decisions: list[dict]) -> list[RouteDecision]:
        stage = WORKFLOW_STAGES[self._stage_index % len(WORKFLOW_STAGES)]
        module_id = self.workflow_module_for_stage(stage)
        self._stage_index += 1
        return self.route_decisions_for_modules(state, [module_id], gate_decisions)


class MoAStyleRuntime(FaithfulRuntimeBase):
    baseline_id = "moa_style_agent"
    routing_policy_label = "static_all_proposers"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("memory_enabled", False)
        kwargs.setdefault("top_k", len(MOA_PROPOSERS) + 1)
        kwargs.setdefault("router_strategy", "rule")
        super().__init__(**kwargs)

    def route(self, state: RuntimeState, gate_decisions: list[dict]) -> list[RouteDecision]:
        remaining_budget = max(state.max_budget - state.budget_used, 0.0)
        selected: list[str] = []
        proposer_cost = sum(self.modules[module_id].cost for module_id in MOA_PROPOSERS if module_id in self.modules)
        aggregator_cost = self.modules["aggregator"].cost if "aggregator" in self.modules else 0.0
        if proposer_cost + aggregator_cost <= remaining_budget:
            selected = list(MOA_PROPOSERS)
            if "aggregator" in self.modules:
                selected.append("aggregator")
        else:
            for module_id in MOA_PROPOSERS:
                if module_id in self.modules and self.modules[module_id].cost <= remaining_budget:
                    selected.append(module_id)
                    remaining_budget -= self.modules[module_id].cost
            if aggregator_cost <= remaining_budget and "aggregator" in self.modules:
                selected.append("aggregator")
        return self.route_decisions_for_modules(state, selected, gate_decisions)


class AgentAttentionFaithfulRuntime(FaithfulRuntimeBase):
    baseline_id = "agent_attention_agent"
    routing_policy_label = "lexical_sparse"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("memory_enabled", True)
        kwargs.setdefault("top_k", 2)
        kwargs.setdefault("router_strategy", "lexical")
        kwargs.setdefault("verifier_enabled", True)
        kwargs.setdefault("adaptive_top_k_enabled", False)
        kwargs.setdefault("strong_budget_gate", False)
        super().__init__(**kwargs)


class AgentAttentionTunedRuntime(FaithfulRuntimeBase):
    """P2 tuned variant: adaptive top-k + strong budget gate + cost-quality frontier."""

    baseline_id = "agent_attention_agent_tuned"
    routing_policy_label = "lexical_sparse_adaptive"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("memory_enabled", True)
        kwargs.setdefault("top_k", 2)
        kwargs.setdefault("max_top_k", 3)
        kwargs.setdefault("router_strategy", "lexical")
        kwargs.setdefault("verifier_enabled", True)
        kwargs.setdefault("adaptive_top_k_enabled", True)
        kwargs.setdefault("strong_budget_gate", True)
        kwargs.setdefault("budget_cost_fraction", 0.30)
        kwargs.setdefault("cost_quality_epsilon", 0.05)
        super().__init__(**kwargs)


def baseline_config_for(baseline_id: str) -> dict[str, Any]:
    configs = {
        "single_react_agent": {
            "routing_policy": "react_loop",
            "memory_policy": "none",
            "controller_policy": "react_loop",
            "note": "Faithful single-controller ReAct loop with one module per step.",
        },
        "fixed_workflow_agent": {
            "routing_policy": "static_workflow",
            "memory_policy": "none",
            "controller_policy": "static_workflow",
            "workflow_stages": list(WORKFLOW_STAGES),
            "note": "Faithful planner->executor->critic->summarizer workflow.",
        },
        "full_history_agent": {
            "routing_policy": "react_full_history",
            "memory_policy": "full_in_run_history",
            "controller_policy": "react_loop",
            "note": "Faithful ReAct with full in-run transcript retained each step.",
        },
        "retrieval_memory_agent": {
            "routing_policy": "react_loop_with_memory",
            "memory_policy": "read_write_behavior_kv",
            "controller_policy": "react_loop",
            "note": "Faithful ReAct plus memory retrieval before each action.",
        },
        "moa_style_agent": {
            "routing_policy": "static_all_proposers",
            "memory_policy": "none",
            "controller_policy": "static_all_proposers",
            "proposers": list(MOA_PROPOSERS),
            "note": "Faithful MoA-style all-proposer activation plus aggregator.",
        },
        "agent_attention_agent": {
            "routing_policy": "lexical_sparse",
            "memory_policy": "read_write_behavior_kv",
            "controller_policy": "heuristic_router",
            "top_k": 2,
            "adaptive_top_k_enabled": False,
            "strong_budget_gate": False,
            "note": "Proposed Agent-Attention lexical sparse routing with memory and gates.",
        },
        "agent_attention_agent_tuned": {
            "routing_policy": "lexical_sparse_adaptive",
            "memory_policy": "read_write_behavior_kv",
            "controller_policy": "heuristic_router",
            "top_k": 2,
            "max_top_k": 3,
            "adaptive_top_k_enabled": True,
            "strong_budget_gate": True,
            "budget_cost_fraction": 0.30,
            "cost_quality_epsilon": 0.05,
            "note": "P2 tuned: adaptive top-k, strong budget gate, cost-quality frontier.",
        },
    }
    return configs.get(baseline_id, {"routing_policy": "unknown"})


def discouraged_modules_for_task(task: dict[str, Any]) -> set[str]:
    expected = task.get("expected_route", {})
    return set(expected.get("discouraged_modules", []))


def build_faithful_runtime(baseline_id: str, task: dict[str, Any], max_steps: int) -> FaithfulRuntimeBase:
    executor = primary_executor_for_task(task)
    discouraged = discouraged_modules_for_task(task)
    modules = default_modules()
    memory_enabled = baseline_id in {"retrieval_memory_agent", "agent_attention_agent", "agent_attention_agent_tuned"}
    memory = memory_for_task(task) if memory_enabled else []

    common: dict[str, Any] = {
        "modules": modules,
        "memory": memory,
        "max_steps": max_steps,
        "verifier_threshold": 0.64,
        "verifier_enabled": True,
    }

    if baseline_id == "single_react_agent":
        return SingleReActRuntime(
            executor_module=executor,
            discouraged_modules=discouraged,
            memory_enabled=False,
            **common,
        )
    if baseline_id == "fixed_workflow_agent":
        return FixedWorkflowRuntime(executor_module=executor, **common)
    if baseline_id == "full_history_agent":
        return FullHistoryRuntime(
            executor_module=executor,
            discouraged_modules=discouraged,
            memory_enabled=False,
            **common,
        )
    if baseline_id == "retrieval_memory_agent":
        return RetrievalMemoryRuntime(
            executor_module=executor,
            discouraged_modules=discouraged,
            memory_enabled=True,
            **common,
        )
    if baseline_id == "moa_style_agent":
        return MoAStyleRuntime(**common)
    if baseline_id == "agent_attention_agent":
        return AgentAttentionFaithfulRuntime(memory_enabled=True, **common)
    if baseline_id == "agent_attention_agent_tuned":
        return AgentAttentionTunedRuntime(memory_enabled=True, **common)
    raise ValueError(f"Unknown baseline_id={baseline_id!r}")
