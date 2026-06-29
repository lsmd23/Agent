"""Auditable routing features for learned router training."""

from __future__ import annotations

from typing import Any

from src.agent_attention_runtime import ModuleSpec, RuntimeState, jaccard, route_intent_bonus, tokenize

FEATURE_NAMES = (
    "lexical_jaccard",
    "intent_bonus",
    "task_family_code",
    "task_family_search",
    "task_family_research",
    "module_is_code",
    "module_is_search",
    "module_is_critic",
    "module_is_memory",
    "module_is_aggregator",
    "step_fraction",
    "failure_signal_count",
    "remaining_budget_fraction",
    "repetition_count",
    "memory_bonus",
)


def task_family_flags(task_family: str) -> dict[str, float]:
    return {
        "task_family_code": 1.0 if task_family == "code_agent_task" else 0.0,
        "task_family_search": 1.0 if task_family == "search_agent_task" else 0.0,
        "task_family_research": 1.0 if task_family == "mini_research_task" else 0.0,
    }


def module_flags(module_id: str) -> dict[str, float]:
    return {
        "module_is_code": 1.0 if module_id == "code_agent" else 0.0,
        "module_is_search": 1.0 if module_id == "search_agent" else 0.0,
        "module_is_critic": 1.0 if module_id == "critic_agent" else 0.0,
        "module_is_memory": 1.0 if module_id == "memory" else 0.0,
        "module_is_aggregator": 1.0 if module_id == "aggregator" else 0.0,
    }


def extract_features(
    state: RuntimeState,
    module: ModuleSpec,
    *,
    task_family: str,
    memory_bonus: float = 0.0,
) -> dict[str, float]:
    query_tokens = tokenize(state.query_text())
    max_steps = max(state.max_budget, 1.0)
    remaining = max(state.max_budget - state.budget_used, 0.0)
    features = {
        "lexical_jaccard": round(jaccard(query_tokens, module.key_tokens), 6),
        "intent_bonus": round(route_intent_bonus(query_tokens, module.module_id, state.failure_signals), 6),
        "step_fraction": round(state.step / max(max_steps, 1.0), 6),
        "failure_signal_count": float(len(state.failure_signals)),
        "remaining_budget_fraction": round(remaining / max(state.max_budget, 0.01), 6),
        "repetition_count": float(state.selected_modules.count(module.module_id)),
        "memory_bonus": round(memory_bonus, 6),
    }
    features.update(task_family_flags(task_family))
    features.update(module_flags(module.module_id))
    return features


def feature_vector(features: dict[str, float]) -> list[float]:
    return [float(features.get(name, 0.0)) for name in FEATURE_NAMES]


def features_from_route_event(
    task: dict[str, Any],
    route_payload: dict[str, Any],
    *,
    step: int,
    goal: str,
    max_budget: float,
) -> list[tuple[dict[str, float], int, str]]:
    """Return (features, label, module_id) rows from a logged route event."""
    from experiments.phase4.oracle_matrix import oracle_label

    state = RuntimeState(goal=goal, max_budget=max_budget)
    state.step = step
    task_family = task.get("task_family", "")
    rows: list[tuple[dict[str, float], int, str]] = []
    for candidate in route_payload.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        module_id = str(candidate.get("module_id", ""))
        if module_id not in {"memory", "code_agent", "search_agent", "critic_agent", "aggregator"}:
            continue
        module = ModuleSpec(
            module_id=module_id,
            kind=module_id,
            description=module_id,
            cost=0.2,
            latency=0.1,
            risk=0.1,
            reliability=0.7,
        )
        memory_bonus = 0.0
        score_terms = candidate.get("score_terms", {})
        if isinstance(score_terms, dict):
            memory_bonus = float(score_terms.get("memory_bonus", 0.0))
        features = extract_features(state, module, task_family=task_family, memory_bonus=memory_bonus)
        label = oracle_label(task, module_id)
        if candidate.get("selected"):
            label = max(label, 1)
        rows.append((features, label, module_id))
    return rows
