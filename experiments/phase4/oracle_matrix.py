"""Offline oracle route matrix from task expected_route specs."""

from __future__ import annotations

from typing import Any


def oracle_entry_for_task(task: dict[str, Any]) -> dict[str, Any]:
    expected = task.get("expected_route", {})
    required = list(expected.get("required_modules", []))
    discouraged = list(expected.get("discouraged_modules", []))
    oracle_best = expected.get("oracle_best_module_id")
    utilities: dict[str, float] = {}
    for module_id in {
        "memory",
        "code_agent",
        "search_agent",
        "critic_agent",
        "aggregator",
        "verifier",
        "planner",
        "executor",
    }:
        score = 0.2
        if module_id in required:
            score = 1.0
        if module_id == oracle_best:
            score = 1.0
        if module_id in discouraged:
            score = 0.05
        utilities[module_id] = round(score, 4)

    return {
        "task_id": task["task_id"],
        "task_family": task.get("task_family", "unknown"),
        "oracle_available": bool(expected.get("oracle_available")),
        "oracle_best_module_id": oracle_best,
        "required_modules": required,
        "discouraged_modules": discouraged,
        "module_utilities": utilities,
        "rationale": expected.get("route_rationale"),
    }


def build_oracle_matrix(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [oracle_entry_for_task(task) for task in tasks]
    return {
        "schema_version": "agent_attention.oracle_matrix.v0.1",
        "task_count": len(entries),
        "entries": entries,
        "entries_by_task_id": {entry["task_id"]: entry for entry in entries},
    }


def oracle_label(task: dict[str, Any], module_id: str) -> int:
    entry = oracle_entry_for_task(task)
    if module_id in entry["discouraged_modules"]:
        return 0
    if module_id == entry["oracle_best_module_id"]:
        return 1
    if module_id in entry["required_modules"]:
        return 1
    return 0


def oracle_regret_for_selection(task: dict[str, Any], selected_modules: list[str]) -> float:
    entry = oracle_entry_for_task(task)
    utilities = entry["module_utilities"]
    selected = set(selected_modules)
    best = max(utilities.values()) if utilities else 1.0
    if not selected:
        return round(best, 6)
    selected_score = max(utilities.get(module_id, 0.0) for module_id in selected)
    missing_required = len(set(entry["required_modules"]) - selected)
    discouraged_hits = len(set(entry["discouraged_modules"]) & selected)
    return round(best - selected_score + 0.35 * missing_required + 0.25 * discouraged_hits, 6)
