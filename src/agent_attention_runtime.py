#!/usr/bin/env python3
"""Deterministic toy runtime for agent-level attention experiments."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable


WORD_RE = re.compile(r"[a-zA-Z0-9_]+")
MEMORY_BONUS_CAP = 0.20
MEMORY_BONUS_FLOOR = -0.40
SCORE_WEIGHTS = {
    "semantic_match": 1.0,
    "reliability": 0.45,
    "historical_success": 0.25,
    "cost": -0.18,
    "latency": -0.10,
    "risk": -0.25,
    "repetition": -0.14,
    "memory_bonus": 1.0,
}


def tokenize(text: str) -> set[str]:
    return {word.lower() for word in WORD_RE.findall(text)}


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class ModuleSpec:
    module_id: str
    kind: str
    description: str
    cost: float
    latency: float
    risk: float
    reliability: float
    historical_success: float = 0.5
    executor: Callable[["RuntimeState", "ModuleSpec"], "ModuleOutput"] | None = None

    @property
    def key_tokens(self) -> set[str]:
        return tokenize(f"{self.module_id} {self.kind} {self.description}")


@dataclass
class MemoryItem:
    key: str
    value: str
    usefulness: float = 0.5
    failures: int = 0
    memory_type: str = "behavior_kv"
    usefulness_label: str = "unknown"
    route_signature: str = "unknown"
    evidence_refs: list[str] = field(default_factory=list)
    negative_transfer_count: int = 0

    @property
    def key_tokens(self) -> set[str]:
        return tokenize(self.key)

    @property
    def value_summary(self) -> str:
        return self.value[:240]


@dataclass
class MemoryRead:
    key: str
    value_summary: str
    memory_type: str
    usefulness_label: str
    retrieval_score: float
    route_signature: str
    evidence_refs: list[str]
    negative_transfer_count: int
    memory_bonus: float


@dataclass
class ModuleOutput:
    module_id: str
    content: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    failure_signal: str | None = None


@dataclass
class RouteDecision:
    module_id: str
    score: float
    score_terms: dict
    score_weights: dict
    selected: bool
    schema_valid: bool = True
    budget_valid: bool = True
    risk_valid: bool = True
    reject_reason: str | None = None


@dataclass
class RuntimeState:
    goal: str
    step: int = 0
    observations: list[str] = field(default_factory=list)
    active_hypotheses: list[str] = field(default_factory=list)
    selected_modules: list[str] = field(default_factory=list)
    budget_used: float = 0.0
    max_budget: float = 4.0
    confidence: float = 0.0
    risk: float = 0.2
    failure_signals: list[str] = field(default_factory=list)
    memory_reads: list[str] = field(default_factory=list)
    memory_writes: list[str] = field(default_factory=list)
    final_answer: str | None = None
    verifier_status: str = "skipped"
    verifier_required: bool = False

    def query_text(self) -> str:
        non_memory_observations = [obs for obs in self.observations if not obs.startswith("Memory:")]
        return " ".join(
            [
                self.goal,
                " ".join(non_memory_observations[-4:]),
                " ".join(self.failure_signals[-2:]),
                " ".join(self.active_hypotheses[-3:]),
            ]
        )


@dataclass
class TrajectoryEvent:
    event_id: int
    step: int
    kind: str
    payload: dict
    timestamp: float = field(default_factory=time.time)


class AgentAttentionRuntime:
    def __init__(
        self,
        modules: list[ModuleSpec],
        memory: list[MemoryItem] | None = None,
        top_k: int = 2,
        max_steps: int = 5,
        verifier_threshold: float = 0.68,
        memory_enabled: bool = True,
        verifier_enabled: bool = True,
        router_strategy: str = "lexical",
        adaptive_top_k_enabled: bool = False,
        max_top_k: int = 3,
        strong_budget_gate: bool = False,
        budget_cost_fraction: float = 0.30,
        cost_quality_epsilon: float = 0.05,
        memory_write_enabled: bool = True,
        memory_write_policy: str = "success_plus_failure",
        quarantine_aware: bool = False,
        learned_semantic_fn: Callable[["RuntimeState", "ModuleSpec", set[str]], float] | None = None,
        learned_router_version: str | None = None,
        task_family: str | None = None,
    ) -> None:
        if router_strategy not in {"rule", "lexical", "learned"}:
            raise ValueError(
                f"Unsupported router_strategy={router_strategy!r}; supported: rule, lexical, learned"
            )
        if router_strategy == "learned" and learned_semantic_fn is None:
            raise ValueError("router_strategy='learned' requires learned_semantic_fn")
        self.modules = {module.module_id: module for module in modules}
        self.memory = memory or []
        self.top_k = top_k
        self.max_steps = max_steps
        self.verifier_threshold = verifier_threshold
        self.memory_enabled = memory_enabled
        self.verifier_enabled = verifier_enabled
        self.router_strategy = router_strategy
        self.adaptive_top_k_enabled = adaptive_top_k_enabled
        self.max_top_k = max(1, max_top_k)
        self.strong_budget_gate = strong_budget_gate
        self.budget_cost_fraction = budget_cost_fraction
        self.cost_quality_epsilon = cost_quality_epsilon
        self.memory_write_enabled = memory_write_enabled
        if memory_write_policy not in {"success_plus_failure", "success_only", "none"}:
            raise ValueError(f"Unsupported memory_write_policy={memory_write_policy!r}")
        self.memory_write_policy = memory_write_policy
        self.quarantine_aware = quarantine_aware
        self.learned_semantic_fn = learned_semantic_fn
        self.learned_router_version = learned_router_version
        self.task_family = task_family or ""
        self.events: list[TrajectoryEvent] = []
        self.current_memory_reads: list[MemoryRead] = []
        self._last_effective_top_k = top_k

    def run(self, task: str, max_budget: float = 4.0) -> RuntimeState:
        self.events = []
        self.current_memory_reads = []
        state = RuntimeState(goal=task, max_budget=max_budget)
        self._log(state, "start", {"goal": task, "config": self.config_snapshot()})

        while state.step < self.max_steps:
            state.step += 1
            memories = self.retrieve_memory(state)
            self._log(state, "memory_retrieval", {"enabled": self.memory_enabled, "items": [asdict(item) for item in memories]})
            for memory in memories:
                state.memory_reads.append(memory.key)
                state.observations.append(f"Memory: {memory.value_summary}")
                self._log(state, "memory_read", asdict(memory))

            gate_decisions = self.apply_gates(state)
            self._log(state, "gates", {"decisions": gate_decisions, "budget_snapshot": self.budget_snapshot(state)})

            route = self.route(state, gate_decisions)
            self._log(
                state,
                "route",
                {
                    "decision_id": f"route-{state.step}",
                    "routing_policy": self.router_strategy,
                    "top_k": self.top_k,
                    "effective_top_k": self._last_effective_top_k,
                    "adaptive_top_k_enabled": self.adaptive_top_k_enabled,
                    "strong_budget_gate": self.strong_budget_gate,
                    "query": state.query_text(),
                    "selected_modules": [decision.module_id for decision in route if decision.selected],
                    "candidates": [asdict(decision) for decision in route],
                    "route_scores": {decision.module_id: decision.score_terms | {"score_total": decision.score, "reject_reason": decision.reject_reason} for decision in route},
                    "budget_snapshot": self.budget_snapshot(state),
                }
                | (
                    {"learned_router_version": self.learned_router_version}
                    if self.learned_router_version
                    else {}
                ),
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

    def config_snapshot(self) -> dict:
        return {
            "top_k": self.top_k,
            "max_steps": self.max_steps,
            "memory_enabled": self.memory_enabled,
            "verifier_enabled": self.verifier_enabled,
            "router_strategy": self.router_strategy,
            "adaptive_top_k_enabled": self.adaptive_top_k_enabled,
            "max_top_k": self.max_top_k,
            "strong_budget_gate": self.strong_budget_gate,
            "budget_cost_fraction": self.budget_cost_fraction,
            "cost_quality_epsilon": self.cost_quality_epsilon,
            "memory_write_enabled": self.memory_write_enabled,
            "memory_write_policy": self.memory_write_policy,
            "quarantine_aware": self.quarantine_aware,
            "memory_bonus_cap": MEMORY_BONUS_CAP,
            "memory_bonus_floor": MEMORY_BONUS_FLOOR,
        }

    def effective_top_k(self, state: RuntimeState, gate_decisions: list[dict]) -> int:
        if not self.adaptive_top_k_enabled:
            return self.top_k

        remaining = max(state.max_budget - state.budget_used, 0.0)
        gate_status = {item["gate"]: item["status"] for item in gate_decisions}
        verifier_required = gate_status.get("VerifierGate") == "require"

        k = 1
        if state.failure_signals or state.confidence < 0.55:
            k = 2
        if state.risk >= 0.45 or verifier_required:
            k = max(k, 2)
        if state.risk >= 0.50 and remaining >= 1.5:
            k = min(self.max_top_k, 3)

        if repeated_action_ratio(state.selected_modules) > 0.35:
            k = 1
        if remaining < 1.0:
            k = 1
        if remaining < 0.5:
            k = 1

        return max(1, min(k, self.max_top_k))

    def strong_budget_reject_reason(
        self,
        module: ModuleSpec,
        state: RuntimeState,
        remaining_budget: float,
    ) -> str | None:
        if not self.strong_budget_gate or remaining_budget <= 0:
            return None
        if module.cost > remaining_budget:
            return None
        high_cost = module.cost > self.budget_cost_fraction * remaining_budget
        if not high_cost:
            return None
        if state.risk >= 0.45 or state.verifier_required:
            return None
        if module.module_id in {"verifier", "code_agent", "search_agent"} and state.failure_signals:
            return None
        return "budget_high_cost_fraction"

    def retrieve_memory(self, state: RuntimeState, limit: int = 2) -> list[MemoryRead]:
        self.current_memory_reads = []
        if not self.memory_enabled:
            return []

        query_tokens = tokenize(state.query_text())
        scored: list[tuple[float, MemoryItem, float]] = []
        for item in self.memory:
            if self.quarantine_aware and self._memory_is_quarantined(item):
                continue
            semantic = jaccard(query_tokens, item.key_tokens)
            if semantic <= 0.0:
                continue
            score = semantic + 0.15 * item.usefulness
            if score > 0.14:
                scored.append((score, item, semantic))

        for score, item, semantic in sorted(scored, reverse=True, key=lambda pair: pair[0])[:limit]:
            bonus = self.compute_memory_bonus(item, semantic, route_match=semantic)
            self.current_memory_reads.append(
                MemoryRead(
                    key=item.key,
                    value_summary=item.value_summary,
                    memory_type=item.memory_type,
                    usefulness_label=item.usefulness_label,
                    retrieval_score=round(score, 4),
                    route_signature=item.route_signature,
                    evidence_refs=item.evidence_refs,
                    negative_transfer_count=item.negative_transfer_count,
                    memory_bonus=bonus,
                )
            )
        return self.current_memory_reads

    def _memory_is_quarantined(self, item: MemoryItem) -> bool:
        if item.usefulness_label == "harmful":
            return True
        if item.negative_transfer_count > 0 and item.usefulness < 0.25:
            return True
        return False

    def _final_success_signal(self, state: RuntimeState) -> str:
        if state.failure_signals:
            return "fail"
        if state.verifier_status == "fail":
            return "fail"
        if state.final_answer and "budget_exhausted" in (state.final_answer or ""):
            return "fail"
        return "pass"

    def should_write_memory(self, state: RuntimeState) -> tuple[bool, str]:
        if not self.memory_enabled or not self.memory_write_enabled:
            return False, "memory_write_disabled"
        if self.memory_write_policy == "none":
            return False, "memory_write_policy_none"
        if self.memory_write_policy == "success_only" and self._final_success_signal(state) != "pass":
            return False, "success_only_skip_failure"
        return True, "write_allowed"

    def compute_memory_bonus(self, item: MemoryItem, retrieval_score: float, route_match: float) -> float:
        raw = retrieval_score * item.usefulness * route_match - 0.22 * item.negative_transfer_count - 0.08 * item.failures
        return round(clamp(raw, MEMORY_BONUS_FLOOR, MEMORY_BONUS_CAP), 4)

    def apply_gates(self, state: RuntimeState) -> list[dict]:
        query_tokens = tokenize(state.goal)
        remaining = max(state.max_budget - state.budget_used, 0.0)
        search_terms = {"latest", "current", "citation", "citations", "evidence", "paper", "papers", "research", "source", "sources", "news", "price"}
        tool_terms = {"code", "edit", "fix", "python", "repo", "test", "tests", "run", "shell"}
        verifier_required = self.verifier_enabled and (
            state.confidence >= self.verifier_threshold or state.risk >= 0.45 or bool(state.failure_signals)
        )
        state.verifier_required = verifier_required
        return [
            {"gate": "ToolGate", "status": "open" if query_tokens & tool_terms else "closed", "reason": "tool_or_code_terms" if query_tokens & tool_terms else "no_tool_need"},
            {"gate": "SearchGate", "status": "open" if query_tokens & search_terms else "closed", "reason": "external_evidence_need" if query_tokens & search_terms else "no_external_evidence_need"},
            {"gate": "MemoryGate", "status": "open_read" if self.memory_enabled else "closed", "reason": "memory_enabled" if self.memory_enabled else "memory_disabled"},
            {"gate": "VerifierGate", "status": "require" if verifier_required else "closed", "reason": "threshold_or_failure" if verifier_required else "not_required_or_disabled"},
            {"gate": "HaltGate", "status": "evaluate", "reason": "checked_every_step"},
            {"gate": "BudgetGate", "status": "allow" if remaining > 0 else "block_high_cost", "reason": "remaining_budget_positive" if remaining > 0 else "budget_exhausted", "remaining_budget": round(remaining, 4)},
            {"gate": "SafetyGate", "status": "allow", "reason": "read_only_toy_runtime"},
        ]

    def route(self, state: RuntimeState, gate_decisions: list[dict]) -> list[RouteDecision]:
        query_tokens = tokenize(state.query_text())
        raw_decisions: list[RouteDecision] = []
        remaining_budget = max(state.max_budget - state.budget_used, 0.0)
        gate_status = {item["gate"]: item["status"] for item in gate_decisions}
        memory_bonus_by_module = self.memory_bonus_by_module()

        for module in self.modules.values():
            if module.module_id == "verifier":
                continue
            if module.module_id == "aggregator" and state.step == 1:
                continue
            semantic = 1.0 if self.router_strategy == "rule" and route_intent_bonus(query_tokens, module.module_id, state.failure_signals) > 0 else jaccard(query_tokens, module.key_tokens)
            if self.router_strategy == "learned" and self.learned_semantic_fn is not None:
                semantic = self.learned_semantic_fn(state, module, query_tokens)
            intent_bonus = route_intent_bonus(query_tokens, module.module_id, state.failure_signals)
            phase_bonus = 0.0
            if state.step > 1 and module.module_id in {"aggregator", "critic_agent"}:
                phase_bonus += 0.12
            if repeated_action_ratio(state.selected_modules) > 0.35 and module.module_id in {"aggregator", "critic_agent"}:
                phase_bonus += 0.18

            repetition = state.selected_modules.count(module.module_id)
            score_terms = {
                "semantic_match": round(semantic + intent_bonus + phase_bonus, 4),
                "reliability": round(module.reliability, 4),
                "historical_success": round(module.historical_success, 4),
                "cost": round(module.cost, 4),
                "latency": round(module.latency, 4),
                "risk": round(module.risk, 4),
                "repetition": round(repetition, 4),
                "memory_bonus": round(memory_bonus_by_module.get(module.module_id, 0.0), 4),
            }
            budget_valid = module.cost <= remaining_budget
            risk_valid = module.risk < 0.8
            gate_reason = self.module_gate_reject_reason(module, gate_status)
            budget_fraction_reason = self.strong_budget_reject_reason(module, state, remaining_budget)
            if budget_fraction_reason:
                gate_reason = budget_fraction_reason
                budget_valid = False
            score = sum(score_terms[key] * SCORE_WEIGHTS[key] for key in SCORE_WEIGHTS)
            raw_decisions.append(
                RouteDecision(
                    module_id=module.module_id,
                    score=round(score, 4),
                    score_terms=score_terms,
                    score_weights=SCORE_WEIGHTS.copy(),
                    selected=False,
                    budget_valid=budget_valid,
                    risk_valid=risk_valid,
                    reject_reason=(
                        budget_fraction_reason
                        if budget_fraction_reason
                        else ("budget_exceeded" if not budget_valid else ("risk_exceeded" if not risk_valid else gate_reason))
                    ),
                )
            )

        eligible = [decision for decision in raw_decisions if decision.reject_reason is None and decision.score > 0.0]
        eligible.sort(key=lambda decision: decision.score, reverse=True)

        if self.strong_budget_gate and self.cost_quality_epsilon > 0 and len(eligible) > 1:
            filtered: list[RouteDecision] = []
            for decision in eligible:
                module = self.modules[decision.module_id]
                dominated = False
                for other in eligible:
                    if other.module_id == decision.module_id:
                        continue
                    other_module = self.modules[other.module_id]
                    if other.score >= decision.score - self.cost_quality_epsilon:
                        if other_module.cost < module.cost and other_module.risk <= module.risk:
                            dominated = True
                            break
                if not dominated:
                    filtered.append(decision)
            eligible = filtered or eligible

        effective_k = self.effective_top_k(state, gate_decisions)
        self._last_effective_top_k = effective_k
        selected_ids = {decision.module_id for decision in eligible[:effective_k]}
        for decision in raw_decisions:
            if decision.module_id in selected_ids:
                decision.selected = True
            elif decision.reject_reason is None:
                decision.reject_reason = "below_top_k" if decision.score > 0 else "low_score"
        raw_decisions.sort(key=lambda decision: decision.score, reverse=True)
        return raw_decisions

    def module_gate_reject_reason(self, module: ModuleSpec, gate_status: dict[str, str]) -> str | None:
        if module.module_id == "memory" and not self.memory_enabled:
            return "gate_closed"
        if module.module_id == "search_agent" and gate_status.get("SearchGate") == "closed":
            return "gate_closed"
        return None

    def memory_bonus_by_module(self) -> dict[str, float]:
        bonuses = {module_id: 0.0 for module_id in self.modules}
        for read in self.current_memory_reads:
            tokens = tokenize(f"{read.key} {read.route_signature} {read.value_summary}")
            for module_id in bonuses:
                if module_id == "verifier":
                    continue
                aliases = {module_id, module_id.replace("_agent", ""), module_id.replace("_", " ")}
                route_match = 1.0 if tokens & tokenize(" ".join(aliases)) else 0.0
                if route_match <= 0.0:
                    continue
                bonuses[module_id] += read.memory_bonus
        return {module_id: round(clamp(value, MEMORY_BONUS_FLOOR, MEMORY_BONUS_CAP), 4) for module_id, value in bonuses.items()}

    def execute(self, state: RuntimeState, route: list[RouteDecision]) -> list[ModuleOutput]:
        outputs: list[ModuleOutput] = []
        for decision in route:
            module = self.modules[decision.module_id]
            if state.budget_used + module.cost > state.max_budget:
                output = ModuleOutput(
                    module_id=module.module_id,
                    content="Skipped because budget gate rejected activation.",
                    confidence=0.0,
                    failure_signal="budget_rejected",
                )
                self._log(
                    state,
                    "budget_gate",
                    {
                        "module_id": module.module_id,
                        "decision": "reject",
                        "reason": "activation_would_exceed_budget",
                        "module_cost": module.cost,
                        "budget_snapshot": self.budget_snapshot(state),
                    },
                )
            else:
                self._log(
                    state,
                    "budget_gate",
                    {
                        "module_id": module.module_id,
                        "decision": "allow",
                        "reason": "within_budget",
                        "module_cost": module.cost,
                        "budget_snapshot": self.budget_snapshot(state),
                    },
                )
                state.budget_used = round(state.budget_used + module.cost, 4)
                state.selected_modules.append(module.module_id)
                output = module.executor(state, module) if module.executor else default_executor(state, module)
            outputs.append(output)
        return outputs

    def aggregate(self, state: RuntimeState, outputs: list[ModuleOutput]) -> None:
        if not outputs:
            state.failure_signals.append("no_module_activated")
            return

        for output in outputs:
            state.observations.append(f"{output.module_id}: {output.content}")
            if output.failure_signal:
                state.failure_signals.append(output.failure_signal)
            else:
                state.active_hypotheses.append(output.content)

        confidences = [output.confidence for output in outputs]
        state.confidence = round(min(0.98, 0.55 * state.confidence + 0.45 * max(confidences)), 4)
        state.risk = round(max(0.02, state.risk * 0.8 - 0.1 * state.confidence), 4)

        if state.confidence >= 0.68 and not any(output.failure_signal for output in outputs):
            state.final_answer = self.compose_final_answer(state, "confidence_threshold_met")

    def maybe_verify(self, state: RuntimeState) -> dict:
        required = self.verifier_enabled and self.should_verify(state)
        state.verifier_required = required
        if not self.verifier_enabled:
            state.verifier_status = "skipped"
            return {"enabled": False, "required": False, "status": "skipped", "reason": "verifier_disabled", "budget_snapshot": self.budget_snapshot(state)}
        if not required:
            state.verifier_status = "skipped"
            return {"enabled": True, "required": False, "status": "skipped", "reason": "threshold_not_met", "budget_snapshot": self.budget_snapshot(state)}

        verifier = self.modules.get("verifier")
        if not verifier:
            state.verifier_status = "inconclusive"
            return {"enabled": True, "required": True, "status": "inconclusive", "reason": "verifier_missing", "budget_snapshot": self.budget_snapshot(state)}
        if state.budget_used + verifier.cost > state.max_budget:
            state.verifier_status = "skipped"
            state.failure_signals.append("verifier_budget_rejected")
            self._log(
                state,
                "budget_gate",
                {
                    "module_id": "verifier",
                    "decision": "reject",
                    "reason": "verifier_would_exceed_budget",
                    "module_cost": verifier.cost,
                    "budget_snapshot": self.budget_snapshot(state),
                },
            )
            return {"enabled": True, "required": True, "status": "skipped", "reason": "budget_rejected", "budget_snapshot": self.budget_snapshot(state)}

        self._log(
            state,
            "budget_gate",
            {
                "module_id": "verifier",
                "decision": "allow",
                "reason": "within_budget",
                "module_cost": verifier.cost,
                "budget_snapshot": self.budget_snapshot(state),
            },
        )
        state.budget_used = round(state.budget_used + verifier.cost, 4)
        state.selected_modules.append("verifier")
        output = verifier.executor(state, verifier) if verifier.executor else default_executor(state, verifier)
        self.aggregate(state, [output])
        state.verifier_status = "fail" if output.failure_signal else "pass"
        return {"enabled": True, "required": True, "status": state.verifier_status, "output": asdict(output), "budget_snapshot": self.budget_snapshot(state)}

    def should_verify(self, state: RuntimeState) -> bool:
        if state.confidence >= self.verifier_threshold:
            return True
        if state.risk >= 0.45:
            return True
        return bool(state.failure_signals and "verifier" not in state.selected_modules)

    def should_halt(self, state: RuntimeState) -> tuple[bool, str]:
        if state.final_answer and state.confidence >= 0.68 and state.verifier_status in {"pass", "skipped"}:
            return True, "answer_ready"
        if state.budget_used >= state.max_budget:
            state.final_answer = self.compose_final_answer(state, "budget_exhausted")
            return True, "budget_exhausted"
        repeated = repeated_action_ratio(state.selected_modules)
        if repeated > 0.6 and state.step >= 3:
            state.final_answer = self.compose_final_answer(state, "loop_stuck")
            return True, "loop_stuck"
        return False, "continue"

    def halt_payload(self, state: RuntimeState, halt: bool, reason: str) -> dict:
        return {
            "halt": halt,
            "reason": reason,
            "success_signal": "pass" if reason == "answer_ready" else ("fail" if reason in {"budget_exhausted", "loop_stuck"} else "unknown"),
            "verifier_status": state.verifier_status,
            "budget_snapshot": self.budget_snapshot(state),
        }

    def compose_final_answer(self, state: RuntimeState, reason: str) -> str:
        useful = [obs for obs in state.observations if not obs.startswith("Memory:")][-4:]
        return (
            f"Finalized because {reason}. "
            f"Selected modules: {', '.join(state.selected_modules) or 'none'}. "
            f"Latest evidence: {' | '.join(useful) or 'none'}."
        )

    def write_reflection(self, state: RuntimeState) -> None:
        route = " -> ".join(state.selected_modules) or "none"
        if state.failure_signals:
            reflection = (
                f"Task '{state.goal}' had failure signals {state.failure_signals}; "
                f"route was {route}; consider verifier or router update."
            )
            failures = 1
            usefulness = 0.35
            usefulness_label = "failure"
            write_reason = "failure"
        else:
            reflection = (
                f"Task '{state.goal}' reached confidence {state.confidence}; "
                f"route {route} was useful under budget {state.budget_used:.2f}."
            )
            failures = 0
            usefulness = 0.75
            usefulness_label = "useful"
            write_reason = "success"

        should_write, write_gate_reason = self.should_write_memory(state)
        if not should_write:
            self._log(
                state,
                "reflection",
                {
                    "value_summary": reflection[:240],
                    "write_reason": write_reason,
                    "memory_write_skipped": True,
                    "memory_write_skip_reason": write_gate_reason,
                },
            )
            return

        key = f"{state.goal} route {route}"
        item = MemoryItem(
            key=key,
            value=reflection,
            usefulness=usefulness,
            failures=failures,
            memory_type="behavior_kv",
            usefulness_label=usefulness_label,
            route_signature=route,
            evidence_refs=[f"event:{event.event_id}" for event in self.events[-4:]],
            negative_transfer_count=0,
        )
        self.memory.append(item)
        state.memory_writes.append(key)
        payload = asdict(item) | {"value_summary": item.value_summary, "write_reason": write_reason}
        self._log(state, "reflection", payload)
        self._log(state, "memory_write", payload)

    def budget_snapshot(self, state: RuntimeState) -> dict:
        return {
            "max_budget": round(state.max_budget, 4),
            "budget_used": round(state.budget_used, 4),
            "remaining_budget": round(max(state.max_budget - state.budget_used, 0.0), 4),
        }

    def state_snapshot(self, state: RuntimeState) -> dict:
        return {
            "goal": state.goal,
            "step": state.step,
            "confidence": state.confidence,
            "risk": state.risk,
            "budget_used": round(state.budget_used, 4),
            "max_budget": state.max_budget,
            "selected_modules": state.selected_modules,
            "failure_signals": state.failure_signals,
            "memory_reads": state.memory_reads,
            "memory_writes": state.memory_writes,
            "verifier_status": state.verifier_status,
            "final_answer": state.final_answer,
        }

    def save_trajectory(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps([asdict(event) for event in self.events], indent=2, ensure_ascii=False), encoding="utf-8")

    def _log(self, state: RuntimeState, kind: str, payload: dict) -> None:
        self.events.append(TrajectoryEvent(event_id=len(self.events) + 1, step=state.step, kind=kind, payload=payload))


def repeated_action_ratio(module_ids: list[str]) -> float:
    if not module_ids:
        return 0.0
    repeats = len(module_ids) - len(set(module_ids))
    return repeats / len(module_ids)


def route_intent_bonus(query_tokens: set[str], module_id: str, failure_signals: list[str]) -> float:
    code_terms = {"bug", "code", "edit", "fix", "python", "repo", "test", "tests", "unit"}
    search_terms = {"citation", "citations", "evidence", "paper", "papers", "research", "search", "source", "sources"}
    critique_terms = {"baseline", "ablation", "failure", "risk", "verify", "compare", "metric", "metrics"}

    if module_id == "code_agent" and query_tokens & code_terms:
        return 0.34
    if module_id == "search_agent" and query_tokens & search_terms:
        return 0.34
    if module_id == "critic_agent" and (query_tokens & critique_terms or failure_signals):
        return 0.22
    if module_id == "memory" and query_tokens & (code_terms | search_terms):
        return 0.08
    if module_id == "aggregator":
        return 0.06
    return 0.0


def default_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    return ModuleOutput(module_id=module.module_id, content=f"{module.kind} produced a generic result for: {state.goal}", confidence=0.55 * module.reliability)


def memory_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    if state.memory_reads:
        return ModuleOutput(module_id=module.module_id, content=f"Reused {len(state.memory_reads)} retrieved trajectory memories.", confidence=0.68, evidence=state.memory_reads[-2:])
    return ModuleOutput(module_id=module.module_id, content="No relevant memory found; proceed without transfer.", confidence=0.42)


def search_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    terms = sorted(tokenize(state.goal) & {"research", "paper", "evidence", "search", "source", "sources", "question"})
    if terms:
        return ModuleOutput(module_id=module.module_id, content=f"Identified external-evidence need around: {', '.join(terms)}.", confidence=0.72, evidence=["external_search_required"])
    return ModuleOutput(module_id=module.module_id, content="Search was low relevance for current task.", confidence=0.35, failure_signal="unnecessary_search")


def code_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    terms = tokenize(state.goal)
    if terms & {"code", "test", "tests", "bug", "fix", "python", "repo"}:
        return ModuleOutput(module_id=module.module_id, content="Proposed inspect-edit-test loop for code task.", confidence=0.76, evidence=["code_path_required", "test_verification_required"])
    return ModuleOutput(module_id=module.module_id, content="Code agent found no code-specific action.", confidence=0.32, failure_signal="wrong_module_for_task")


def critic_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    unresolved = " ".join(state.failure_signals[-3:]) or "no explicit failures"
    return ModuleOutput(module_id=module.module_id, content=f"Critiqued current trajectory; unresolved signals: {unresolved}.", confidence=0.66)


def verifier_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    if any(signal in {"wrong_module_for_task", "budget_rejected", "verifier_budget_rejected"} for signal in state.failure_signals):
        return ModuleOutput(module_id=module.module_id, content="Verifier rejected the current answer due to module or budget failure.", confidence=0.82, failure_signal="verification_failed")
    return ModuleOutput(module_id=module.module_id, content="Verifier found no blocking inconsistency in the trajectory.", confidence=0.84, evidence=["trajectory_consistent"])


def aggregator_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    return ModuleOutput(module_id=module.module_id, content="Aggregated active module outputs into a concise state update.", confidence=0.7)


def build_default_runtime(
    top_k: int = 2,
    max_steps: int = 5,
    memory_enabled: bool = True,
    verifier_enabled: bool = True,
    router_strategy: str = "lexical",
    adaptive_top_k_enabled: bool = False,
    max_top_k: int = 3,
    strong_budget_gate: bool = False,
    budget_cost_fraction: float = 0.30,
    cost_quality_epsilon: float = 0.05,
    memory_write_enabled: bool = True,
    memory_write_policy: str = "success_plus_failure",
    quarantine_aware: bool = False,
) -> AgentAttentionRuntime:
    modules = [
        ModuleSpec("memory", "memory", "retrieve and reuse prior successful workflows, failures, reflections, and routing traces", 0.15, 0.1, 0.15, 0.66, 0.62, memory_executor),
        ModuleSpec("search_agent", "agent", "search external sources, papers, evidence, citations, recency-sensitive facts, and cross-check claims", 0.7, 0.8, 0.35, 0.72, 0.6, search_executor),
        ModuleSpec("code_agent", "agent", "inspect repository code, fix bugs, edit files, run tests, and verify patches", 0.8, 0.9, 0.4, 0.75, 0.64, code_executor),
        ModuleSpec("critic_agent", "agent", "critique plans, detect missing evidence, find contradictions, and attribute failures", 0.45, 0.4, 0.2, 0.7, 0.58, critic_executor),
        ModuleSpec("aggregator", "aggregator", "combine module outputs, update state, compress trajectory, and preserve original goal", 0.25, 0.2, 0.1, 0.7, 0.61, aggregator_executor),
        ModuleSpec("verifier", "verifier", "check result consistency, required evidence, test status, and halt readiness", 0.35, 0.3, 0.15, 0.82, 0.66, verifier_executor),
    ]
    memory = [
        MemoryItem(
            key="python failing test inspect edit run tests code route",
            value="For code fixes, use inspect -> minimal edit -> test -> verifier; avoid broad refactors.",
            usefulness=0.8,
            memory_type="skill_memory",
            usefulness_label="useful",
            route_signature="memory -> code_agent -> verifier",
            evidence_refs=["seed:code_route"],
        ),
        MemoryItem(
            key="research paper evidence sources citations cross check route",
            value="For research answers, retrieve primary sources, cluster by method, then ask critic to find gaps.",
            usefulness=0.78,
            memory_type="behavior_kv",
            usefulness_label="useful",
            route_signature="memory -> search_agent -> critic_agent",
            evidence_refs=["seed:research_route"],
        ),
    ]
    return AgentAttentionRuntime(
        modules=modules,
        memory=memory,
        top_k=top_k,
        max_steps=max_steps,
        verifier_threshold=0.64,
        memory_enabled=memory_enabled,
        verifier_enabled=verifier_enabled,
        router_strategy=router_strategy,
        adaptive_top_k_enabled=adaptive_top_k_enabled,
        max_top_k=max_top_k,
        strong_budget_gate=strong_budget_gate,
        budget_cost_fraction=budget_cost_fraction,
        cost_quality_epsilon=cost_quality_epsilon,
        memory_write_enabled=memory_write_enabled,
        memory_write_policy=memory_write_policy,
        quarantine_aware=quarantine_aware,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the toy Agent-Attention runtime.")
    parser.add_argument("--task", required=True, help="Task to run through the runtime.")
    parser.add_argument("--output", default="experiments/trajectory.json", help="Where to save trajectory JSON.")
    parser.add_argument("--top-k", type=int, default=2, help="Number of modules to activate per step.")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum runtime steps.")
    parser.add_argument("--max-budget", type=float, default=4.0, help="Maximum activation budget.")
    parser.add_argument("--router-strategy", choices=["rule", "lexical"], default="lexical", help="Deterministic router strategy.")
    parser.add_argument("--disable-memory", action="store_true", help="Disable memory retrieval and memory module routing.")
    parser.add_argument("--disable-verifier", action="store_true", help="Disable verifier activation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = build_default_runtime(
        top_k=args.top_k,
        max_steps=args.max_steps,
        memory_enabled=not args.disable_memory,
        verifier_enabled=not args.disable_verifier,
        router_strategy=args.router_strategy,
    )
    state = runtime.run(args.task, max_budget=args.max_budget)
    runtime.save_trajectory(args.output)
    print(json.dumps(runtime.state_snapshot(state), indent=2, ensure_ascii=False))
    print(f"trajectory_saved={args.output}")


if __name__ == "__main__":
    main()
