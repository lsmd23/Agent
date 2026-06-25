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


def tokenize(text: str) -> set[str]:
    return {word.lower() for word in WORD_RE.findall(text)}


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


@dataclass
class ModuleSpec:
    module_id: str
    kind: str
    description: str
    cost: float
    latency: float
    risk: float
    reliability: float
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

    @property
    def key_tokens(self) -> set[str]:
        return tokenize(self.key)


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
    semantic_match: float
    reliability: float
    cost_penalty: float
    risk_penalty: float


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
    ) -> None:
        self.modules = {module.module_id: module for module in modules}
        self.memory = memory or []
        self.top_k = top_k
        self.max_steps = max_steps
        self.verifier_threshold = verifier_threshold
        self.events: list[TrajectoryEvent] = []

    def run(self, task: str, max_budget: float = 4.0) -> RuntimeState:
        state = RuntimeState(goal=task, max_budget=max_budget)
        self._log(state, "start", {"goal": task})

        while state.step < self.max_steps:
            state.step += 1
            memories = self.retrieve_memory(state)
            for memory in memories:
                state.memory_reads.append(memory.key)
                state.observations.append(f"Memory: {memory.value}")
            self._log(
                state,
                "memory_retrieval",
                {"items": [asdict(item) for item in memories]},
            )

            route = self.route(state)
            self._log(
                state,
                "route",
                {"decisions": [asdict(decision) for decision in route]},
            )

            outputs = self.execute(state, route)
            self._log(
                state,
                "execute",
                {"outputs": [asdict(output) for output in outputs]},
            )

            self.aggregate(state, outputs)
            self._log(state, "state_update", self.state_snapshot(state))

            if self.should_verify(state):
                verifier = self.modules.get("verifier")
                if verifier:
                    output = verifier.executor(state, verifier) if verifier.executor else default_executor(state, verifier)
                    self.aggregate(state, [output])
                    self._log(state, "verify", asdict(output))

            halt, reason = self.should_halt(state)
            self._log(state, "halt_gate", {"halt": halt, "reason": reason})
            if halt:
                break

        if state.final_answer is None:
            state.final_answer = self.compose_final_answer(state, "max_steps_reached")
        self.write_reflection(state)
        self._log(state, "finish", self.state_snapshot(state))
        return state

    def retrieve_memory(self, state: RuntimeState, limit: int = 2) -> list[MemoryItem]:
        query_tokens = tokenize(state.query_text())
        scored = []
        for item in self.memory:
            semantic = jaccard(query_tokens, item.key_tokens)
            if semantic <= 0.0:
                continue
            score = semantic + 0.2 * item.usefulness - 0.1 * item.failures
            scored.append((score, item))
        return [item for score, item in sorted(scored, reverse=True, key=lambda pair: pair[0])[:limit] if score > 0.14]

    def route(self, state: RuntimeState) -> list[RouteDecision]:
        query_tokens = tokenize(state.query_text())
        decisions: list[RouteDecision] = []
        remaining_budget = max(state.max_budget - state.budget_used, 0.0)

        for module in self.modules.values():
            if module.module_id == "verifier":
                continue
            if module.module_id == "aggregator" and state.step == 1:
                continue
            semantic = jaccard(query_tokens, module.key_tokens)
            intent_bonus = route_intent_bonus(query_tokens, module.module_id, state.failure_signals)
            budget_pressure = 0.2 if module.cost > remaining_budget else 0.0
            cost_penalty = 0.18 * module.cost + budget_pressure
            risk_penalty = 0.25 * module.risk
            repetition_penalty = 0.14 * state.selected_modules.count(module.module_id)
            phase_bonus = 0.0
            if state.step > 1 and module.module_id in {"aggregator", "critic_agent"}:
                phase_bonus += 0.12
            if repeated_action_ratio(state.selected_modules) > 0.35 and module.module_id in {"aggregator", "critic_agent"}:
                phase_bonus += 0.18
            score = (
                semantic
                + intent_bonus
                + phase_bonus
                + 0.45 * module.reliability
                - cost_penalty
                - risk_penalty
                - repetition_penalty
            )
            decisions.append(
                RouteDecision(
                    module_id=module.module_id,
                    score=round(score, 4),
                    semantic_match=round(semantic, 4),
                    reliability=module.reliability,
                    cost_penalty=round(cost_penalty, 4),
                    risk_penalty=round(risk_penalty, 4),
                )
            )

        decisions.sort(key=lambda decision: decision.score, reverse=True)
        return [decision for decision in decisions[: self.top_k] if decision.score > 0.0]

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
            else:
                state.budget_used += module.cost
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

    def should_verify(self, state: RuntimeState) -> bool:
        if state.confidence >= self.verifier_threshold:
            return True
        if state.risk >= 0.45:
            return True
        return bool(state.failure_signals and "verifier" not in state.selected_modules)

    def should_halt(self, state: RuntimeState) -> tuple[bool, str]:
        if state.final_answer and state.confidence >= 0.68:
            return True, "answer_ready"
        if state.budget_used >= state.max_budget:
            state.final_answer = self.compose_final_answer(state, "budget_exhausted")
            return True, "budget_exhausted"
        repeated = repeated_action_ratio(state.selected_modules)
        if repeated > 0.6 and state.step >= 3:
            state.final_answer = self.compose_final_answer(state, "loop_stuck")
            return True, "loop_stuck"
        return False, "continue"

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
        else:
            reflection = (
                f"Task '{state.goal}' reached confidence {state.confidence}; "
                f"route {route} was useful under budget {state.budget_used:.2f}."
            )
            failures = 0
            usefulness = 0.75

        key = f"{state.goal} route {route}"
        self.memory.append(MemoryItem(key=key, value=reflection, usefulness=usefulness, failures=failures))
        state.memory_writes.append(key)
        self._log(state, "reflection", {"key": key, "value": reflection})

    def state_snapshot(self, state: RuntimeState) -> dict:
        return {
            "goal": state.goal,
            "step": state.step,
            "confidence": state.confidence,
            "risk": state.risk,
            "budget_used": round(state.budget_used, 4),
            "selected_modules": state.selected_modules,
            "failure_signals": state.failure_signals,
            "memory_reads": state.memory_reads,
            "memory_writes": state.memory_writes,
            "final_answer": state.final_answer,
        }

    def save_trajectory(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps([asdict(event) for event in self.events], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _log(self, state: RuntimeState, kind: str, payload: dict) -> None:
        self.events.append(
            TrajectoryEvent(
                event_id=len(self.events) + 1,
                step=state.step,
                kind=kind,
                payload=payload,
            )
        )


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
    return ModuleOutput(
        module_id=module.module_id,
        content=f"{module.kind} produced a generic result for: {state.goal}",
        confidence=0.55 * module.reliability,
    )


def memory_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    if state.memory_reads:
        return ModuleOutput(
            module_id=module.module_id,
            content=f"Reused {len(state.memory_reads)} retrieved trajectory memories.",
            confidence=0.68,
            evidence=state.memory_reads[-2:],
        )
    return ModuleOutput(
        module_id=module.module_id,
        content="No relevant memory found; proceed without transfer.",
        confidence=0.42,
    )


def search_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    terms = sorted(tokenize(state.goal) & {"research", "paper", "evidence", "search", "source", "sources", "question"})
    if terms:
        return ModuleOutput(
            module_id=module.module_id,
            content=f"Identified external-evidence need around: {', '.join(terms)}.",
            confidence=0.72,
            evidence=["external_search_required"],
        )
    return ModuleOutput(
        module_id=module.module_id,
        content="Search was low relevance for current task.",
        confidence=0.35,
        failure_signal="unnecessary_search",
    )


def code_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    terms = tokenize(state.goal)
    if terms & {"code", "test", "tests", "bug", "fix", "python", "repo"}:
        return ModuleOutput(
            module_id=module.module_id,
            content="Proposed inspect-edit-test loop for code task.",
            confidence=0.76,
            evidence=["code_path_required", "test_verification_required"],
        )
    return ModuleOutput(
        module_id=module.module_id,
        content="Code agent found no code-specific action.",
        confidence=0.32,
        failure_signal="wrong_module_for_task",
    )


def critic_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    unresolved = " ".join(state.failure_signals[-3:]) or "no explicit failures"
    return ModuleOutput(
        module_id=module.module_id,
        content=f"Critiqued current trajectory; unresolved signals: {unresolved}.",
        confidence=0.66,
    )


def verifier_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    if any(signal in {"wrong_module_for_task", "budget_rejected"} for signal in state.failure_signals):
        return ModuleOutput(
            module_id=module.module_id,
            content="Verifier rejected the current answer due to module or budget failure.",
            confidence=0.82,
            failure_signal="verification_failed",
        )
    return ModuleOutput(
        module_id=module.module_id,
        content="Verifier found no blocking inconsistency in the trajectory.",
        confidence=0.84,
        evidence=["trajectory_consistent"],
    )


def aggregator_executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
    return ModuleOutput(
        module_id=module.module_id,
        content="Aggregated active module outputs into a concise state update.",
        confidence=0.7,
    )


def build_default_runtime(top_k: int = 2, max_steps: int = 5) -> AgentAttentionRuntime:
    modules = [
        ModuleSpec(
            module_id="memory",
            kind="memory",
            description="retrieve and reuse prior successful workflows, failures, reflections, and routing traces",
            cost=0.15,
            latency=0.1,
            risk=0.15,
            reliability=0.66,
            executor=memory_executor,
        ),
        ModuleSpec(
            module_id="search_agent",
            kind="agent",
            description="search external sources, papers, evidence, citations, recency-sensitive facts, and cross-check claims",
            cost=0.7,
            latency=0.8,
            risk=0.35,
            reliability=0.72,
            executor=search_executor,
        ),
        ModuleSpec(
            module_id="code_agent",
            kind="agent",
            description="inspect repository code, fix bugs, edit files, run tests, and verify patches",
            cost=0.8,
            latency=0.9,
            risk=0.4,
            reliability=0.75,
            executor=code_executor,
        ),
        ModuleSpec(
            module_id="critic_agent",
            kind="agent",
            description="critique plans, detect missing evidence, find contradictions, and attribute failures",
            cost=0.45,
            latency=0.4,
            risk=0.2,
            reliability=0.7,
            executor=critic_executor,
        ),
        ModuleSpec(
            module_id="aggregator",
            kind="aggregator",
            description="combine module outputs, update state, compress trajectory, and preserve original goal",
            cost=0.25,
            latency=0.2,
            risk=0.1,
            reliability=0.7,
            executor=aggregator_executor,
        ),
        ModuleSpec(
            module_id="verifier",
            kind="verifier",
            description="check result consistency, required evidence, test status, and halt readiness",
            cost=0.35,
            latency=0.3,
            risk=0.15,
            reliability=0.82,
            executor=verifier_executor,
        ),
    ]
    memory = [
        MemoryItem(
            key="python failing test inspect edit run tests code route",
            value="For code fixes, use inspect -> minimal edit -> test -> verifier; avoid broad refactors.",
            usefulness=0.8,
        ),
        MemoryItem(
            key="research paper evidence sources citations cross check route",
            value="For research answers, retrieve primary sources, cluster by method, then ask critic to find gaps.",
            usefulness=0.78,
        ),
    ]
    return AgentAttentionRuntime(modules=modules, memory=memory, top_k=top_k, max_steps=max_steps, verifier_threshold=0.64)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the toy Agent-Attention runtime.")
    parser.add_argument("--task", required=True, help="Task to run through the runtime.")
    parser.add_argument("--output", default="experiments/trajectory.json", help="Where to save trajectory JSON.")
    parser.add_argument("--top-k", type=int, default=2, help="Number of modules to activate per step.")
    parser.add_argument("--max-steps", type=int, default=5, help="Maximum runtime steps.")
    parser.add_argument("--max-budget", type=float, default=4.0, help="Maximum activation budget.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = build_default_runtime(top_k=args.top_k, max_steps=args.max_steps)
    state = runtime.run(args.task, max_budget=args.max_budget)
    runtime.save_trajectory(args.output)
    print(json.dumps(runtime.state_snapshot(state), indent=2, ensure_ascii=False))
    print(f"trajectory_saved={args.output}")


if __name__ == "__main__":
    main()
