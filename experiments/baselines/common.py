"""Shared utilities for faithful baseline runners."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agent_attention_runtime import MemoryItem


MEMORY_CORPUS: dict[str, MemoryItem] = {
    "seed:code_route": MemoryItem(
        key="python failing test inspect edit run tests code route",
        value="For code fixes, use inspect -> minimal edit -> test -> verifier; avoid broad refactors.",
        usefulness=0.8,
        memory_type="skill_memory",
        usefulness_label="useful",
        route_signature="memory -> code_agent -> verifier",
        evidence_refs=["seed:code_route"],
    ),
    "seed:research_route": MemoryItem(
        key="research paper evidence sources citations cross check route",
        value="For research answers, retrieve primary sources, cluster by method, then ask critic to find gaps.",
        usefulness=0.78,
        memory_type="behavior_kv",
        usefulness_label="useful",
        route_signature="memory -> search_agent -> critic_agent",
        evidence_refs=["seed:research_route"],
    ),
    "seed:harmful_search_for_code": MemoryItem(
        key="python unit test fix failing code route search evidence sources only stale",
        value="For any failing test, prefer search-only evidence gathering instead of inspecting repository code.",
        usefulness=0.2,
        failures=2,
        memory_type="behavior_kv",
        usefulness_label="harmful",
        route_signature="search_agent -> search_agent",
        evidence_refs=["seed:harmful_search_for_code"],
        negative_transfer_count=2,
    ),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def memory_for_task(task: dict[str, Any], *, quarantine_at_load: bool = True) -> list[MemoryItem]:
    setup = task.get("memory_setup", {})
    injected_ids = setup.get("injected_memory_ids", [])
    quarantined = set(setup.get("quarantined_memory_ids", []))
    items: list[MemoryItem] = []
    for memory_id in injected_ids:
        if quarantine_at_load and memory_id in quarantined:
            continue
        template = MEMORY_CORPUS.get(memory_id)
        if template is not None:
            items.append(
                MemoryItem(
                    key=template.key,
                    value=template.value,
                    usefulness=template.usefulness,
                    failures=template.failures,
                    memory_type=template.memory_type,
                    usefulness_label=template.usefulness_label,
                    route_signature=template.route_signature,
                    evidence_refs=list(template.evidence_refs),
                    negative_transfer_count=template.negative_transfer_count,
                )
            )
    return items


def primary_executor_for_task(task: dict[str, Any]) -> str:
    family = task.get("task_family", "")
    if family == "code_agent_task":
        return "code_agent"
    if family in {"search_agent_task", "mini_research_task"}:
        return "search_agent"
    return "critic_agent"


def final_failure_reason(final_answer: str | None, success_label: str) -> str | None:
    if success_label == "pass":
        return None
    if not final_answer:
        return "no_final_answer"
    marker = "Finalized because "
    if marker in final_answer:
        return final_answer.split(marker, 1)[1].split(".", 1)[0].strip()
    return "route_or_oracle_mismatch"


def route_proxy_oracle(task: dict[str, Any], route_payload: dict[str, Any]) -> dict[str, Any]:
    expected = task.get("expected_route", {})
    required = set(expected.get("required_modules", []))
    discouraged = set(expected.get("discouraged_modules", []))
    oracle_best_module_id = expected.get("oracle_best_module_id")
    selected = set(str(module) for module in route_payload.get("selected_modules", []))
    candidates = route_payload.get("candidates", [])

    candidate_scores = {
        candidate.get("module_id"): candidate.get("score")
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("score"), (int, float))
    }
    selected_scores = [float(candidate_scores[module]) for module in selected if module in candidate_scores]
    selected_score = max(selected_scores) if selected_scores else None
    oracle_best_score = candidate_scores.get(oracle_best_module_id)

    missing_required = sorted(required - selected)
    selected_discouraged = sorted(discouraged & selected)
    if oracle_best_score is not None and selected_score is not None:
        score_gap = max(0.0, float(oracle_best_score) - float(selected_score))
    else:
        score_gap = 0.0 if not missing_required else 1.0
    proxy_penalty = 0.35 * len(missing_required) + 0.25 * len(selected_discouraged)
    proxy_regret = round(score_gap + proxy_penalty, 6)

    return {
        "oracle_available": bool(expected.get("oracle_available")),
        "proxy_available": True,
        "oracle_best_module_id": oracle_best_module_id,
        "selected_score": selected_score,
        "oracle_best_score": oracle_best_score,
        "oracle_regret": None,
        "proxy_regret": proxy_regret,
        "missing_required_modules": missing_required,
        "selected_discouraged_modules": selected_discouraged,
        "rationale": expected.get("route_rationale"),
    }


def add_route_proxy_oracles(task: dict[str, Any], events: list[dict[str, Any]]) -> None:
    for event in events:
        if event.get("kind") == "route" and isinstance(event.get("payload"), dict):
            event["payload"]["oracle"] = route_proxy_oracle(task, event["payload"])


def success_label_for(task: dict[str, Any], state: Any) -> str:
    selected = set(state.selected_modules)
    expected = task.get("expected_route", {})
    required = set(expected.get("required_modules", []))
    discouraged = set(expected.get("discouraged_modules", []))
    probe = task.get("negative_transfer_probe", {})
    harmful_ids = set(probe.get("harmful_memory_ids", []))
    required_ok = required.issubset(selected)
    discouraged_ok = not (discouraged & selected)
    verifier_ok = state.verifier_status in {"pass", "skipped"}
    budget_ok = not any("budget" in signal for signal in state.failure_signals)

    harmful_memory_read = False
    if probe.get("enabled") and harmful_ids:
        for read_key in state.memory_reads:
            for harmful_id in harmful_ids:
                template = MEMORY_CORPUS.get(harmful_id)
                if template and template.key.split()[0] in read_key.lower():
                    harmful_memory_read = True
        if "search_agent" in selected and "code_agent" in required and probe.get("probe_type") == "wrong_route_memory":
            if any("search" in obs.lower() for obs in state.observations if isinstance(obs, str)):
                harmful_memory_read = True

    if harmful_memory_read and probe.get("enabled"):
        if required_ok and verifier_ok:
            return "partial"
        return "fail"

    if required_ok and discouraged_ok and verifier_ok and budget_ok:
        return "pass"
    if required_ok and verifier_ok:
        return "partial"
    return "fail"


def envelope_for(
    task: dict[str, Any],
    baseline_id: str,
    baseline_config: dict[str, Any],
    state: Any,
    events: list[Any],
    *,
    simulation: bool = False,
    run_prefix: str = "phase1_faithful",
    ablation_id: str | None = None,
) -> dict[str, Any]:
    success_label = success_label_for(task, state)
    run_id = f"{run_prefix}__{baseline_id}__{task['task_id']}"
    if ablation_id:
        run_id = f"{run_prefix}__{ablation_id}__{task['task_id']}"
    known_deviations = [
        "faithful_toy_runtime_not_real_llm",
        "toy_route_oracle_success_label",
        "toy_scalar_activation_cost_not_full_cost_delta",
        "oracle_route_regret_unavailable",
    ]
    if simulation:
        known_deviations.append("phase1_toy_baseline_simulation")

    serialized_events = [asdict(event) for event in events]
    add_route_proxy_oracles(task, serialized_events)
    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": run_id,
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": baseline_id,
        "ablation_id": ablation_id,
        "runtime_config": {
            "baseline_config": baseline_config,
            "budget": task["budget"],
            "simulation": simulation,
            "faithful_baseline": not simulation,
        },
        "task_family": task["task_family"],
        "module_registry_snapshot": [],
        "events": serialized_events,
        "final_answer": state.final_answer,
        "final_success_label": success_label,
        "failure_reason": final_failure_reason(state.final_answer, success_label),
        "known_deviations": known_deviations,
        "metrics_summary": {},
    }
