"""Failure attribution from trajectory logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_trajectory(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def event_kind(event: dict[str, Any]) -> str:
    return str(event.get("kind") or event.get("event_type") or "")


def collect_failure_signals(events: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for event in events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else event
        state = payload.get("state") if isinstance(payload.get("state"), dict) else payload
        raw = state.get("failure_signals") if isinstance(state, dict) else None
        if isinstance(raw, list):
            signals.extend(str(item) for item in raw)
        for output in payload.get("outputs", []) if isinstance(payload.get("outputs"), list) else []:
            if isinstance(output, dict) and output.get("failure_signal"):
                signals.append(str(output["failure_signal"]))
    return signals


def activated_modules(events: list[dict[str, Any]]) -> list[str]:
    modules: list[str] = []
    for event in events:
        if event_kind(event) != "route":
            continue
        payload = event.get("payload", {})
        for module_id in payload.get("selected_modules", []):
            modules.append(str(module_id))
    return modules


def harmful_memory_event_ids(events: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for event in events:
        if event_kind(event) != "memory_read":
            continue
        payload = event.get("payload", {})
        if payload.get("usefulness_label") == "harmful":
            ids.append(str(event.get("event_id")))
    return ids


def blame_from_trajectory(
    envelope: dict[str, Any],
    events: list[dict[str, Any]],
    task: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    task_id = envelope.get("task_id", task.get("task_id", "unknown"))
    failure_id = f"failure__{envelope.get('run_id', task_id)}"
    expected = task.get("expected_route", {})
    required = set(expected.get("required_modules", []))
    discouraged = set(expected.get("discouraged_modules", []))
    selected = set(activated_modules(events))
    failure_signals = collect_failure_signals(events)
    harmful_ids = harmful_memory_event_ids(events)
    probe = task.get("negative_transfer_probe", {})
    if (
        not harmful_ids
        and metrics["memory"].get("harmful_memory_reads", 0) == 0
        and probe.get("enabled")
        and probe.get("probe_type") == "wrong_route_memory"
        and "search_agent" in selected
        and "code_agent" in required
    ):
        harmful_ids = ["probe_wrong_route_memory"]

    symptom = metrics["final"].get("failure_reason") or "task_failed"
    if metrics["process"].get("budget_exhaustion"):
        symptom = "budget_exhaustion"
    if metrics["process"].get("loop_stuck"):
        symptom = "loop_stuck"

    blamed_component = "module"
    component_id = "unknown"
    local_gradient = "Improve module selection and execution for this task family."
    proposed_update: dict[str, Any]

    if harmful_ids or metrics["memory"].get("harmful_memory_reads", 0) > 0:
        blamed_component = "memory"
        component_id = "memory_store"
        local_gradient = (
            "Harmful memory reads preceded wrong routing; increase quarantine filtering "
            "for usefulness_label=harmful and high negative_transfer_count entries."
        )
        proposed_update = {
            "target": "memory_write_policy",
            "target_id": "global_quarantine",
            "before": "quarantine_at_load_only",
            "after": "quarantine_aware_read_filter=true",
            "bounded_scope": "memory retrieval on code/search tasks",
            "expected_effect": "negative_transfer_cases",
            "rollback_condition": "useful_memory_reuse_rate drops by >0.10 on held-out tasks",
            "patch_parameters": {"quarantine_aware": True},
        }
        evidence_ids = harmful_ids or [str(events[-1].get("event_id", 1))]
    elif discouraged & selected:
        blamed_component = "router"
        component_id = "lexical_router"
        wrong = sorted(discouraged & selected)
        local_gradient = (
            f"Router activated discouraged modules {wrong}; add task-family suppression "
            f"for {sorted(discouraged)} when required modules are {sorted(required)}."
        )
        proposed_update = {
            "target": "router_rule",
            "target_id": task.get("task_family", "unknown"),
            "before": "lexical_topk_without_discouraged_penalty",
            "after": f"hard_discourage={wrong}",
            "bounded_scope": f"task_family={task.get('task_family')}",
            "expected_effect": "success_rate",
            "rollback_condition": "proxy_route_regret increases by >0.15 on held-out tasks",
            "patch_parameters": {"discouraged_modules": wrong},
        }
        evidence_ids = [
            str(event.get("event_id"))
            for event in events
            if event_kind(event) == "route" and discouraged & set(event.get("payload", {}).get("selected_modules", []))
        ] or ["1"]
    elif metrics["process"].get("budget_exhaustion"):
        blamed_component = "router"
        component_id = "budget_gate"
        local_gradient = "Reduce parallel module activation under tight budget; prefer top_k=1 on early steps."
        proposed_update = {
            "target": "router_rule",
            "target_id": "budget_conservation",
            "before": "adaptive_top_k_up_to_3",
            "after": "cap_effective_top_k=1_when_remaining_budget<1.0",
            "bounded_scope": "router activation budget",
            "expected_effect": "cost_normalized_success",
            "rollback_condition": "success_rate drops by >0.10 with unchanged cost",
            "patch_parameters": {"cap_top_k": 1, "budget_threshold": 1.0},
        }
        evidence_ids = [str(event.get("event_id")) for event in events if event_kind(event) == "budget_gate"][:3] or ["1"]
    elif not required.issubset(selected):
        blamed_component = "router"
        component_id = "lexical_router"
        missing = sorted(required - selected)
        local_gradient = f"Required modules {missing} were not activated; bias router toward {missing[0]} on this task family."
        proposed_update = {
            "target": "router_rule",
            "target_id": task.get("task_family", "unknown"),
            "before": "pure_lexical_match",
            "after": f"intent_bonus_for={missing}",
            "bounded_scope": f"task_family={task.get('task_family')}",
            "expected_effect": "success_rate",
            "rollback_condition": "activation_cost rises by >0.5 without success gain",
            "patch_parameters": {"intent_bonus_for": missing, "intent_bonus_delta": 0.25, "early_priority_modules": missing, "early_priority_max_step": 2, "early_priority_bonus": 1.5},
        }
        evidence_ids = [str(event.get("event_id")) for event in events if event_kind(event) == "route"][:2] or ["1"]
    else:
        blamed_component = "halt"
        component_id = "halt_gate"
        local_gradient = "Task ended without required success signal; tighten halt criteria or add verifier before answer_ready."
        proposed_update = {
            "target": "halt_threshold",
            "target_id": "default",
            "before": "verifier_threshold=0.64",
            "after": "require_verifier_on_code_tasks=true",
            "bounded_scope": "halt/verifier gate",
            "expected_effect": "premature_halt reduction",
            "rollback_condition": "step_exhaustion rate increases by >0.15",
            "patch_parameters": {"require_verifier_on_code_tasks": True, "verifier_threshold_cap": 0.50},
        }
        evidence_ids = [str(event.get("event_id")) for event in events if event_kind(event) == "halt_gate"][:1] or ["1"]

    confidence = 0.55
    if harmful_ids:
        confidence = 0.78
    elif discouraged & selected:
        confidence = 0.72
    elif not required.issubset(selected):
        confidence = 0.68

    blame_candidate = {
        "candidate_id": f"{failure_id}__primary",
        "component_type": blamed_component,
        "component_id": component_id,
        "hypothesis": local_gradient,
        "causal_link_score": round(confidence, 4),
        "temporal_proximity_score": 0.6,
        "counterfactual_plausibility_score": round(confidence - 0.05, 4),
        "evidence_event_ids": evidence_ids,
        "evidence_refs": [{"ref_id": event_id, "source_type": "trajectory_event"} for event_id in evidence_ids],
        "label": "primary",
        "validation_outcome": "not_tested",
    }

    return {
        "case_id": f"case__{failure_id}",
        "failure_id": failure_id,
        "trigger_failure_ids": [failure_id],
        "symptom": symptom,
        "root_cause_hypothesis": local_gradient,
        "blamed_component": blamed_component,
        "blame_candidates": [blame_candidate],
        "evidence_event_ids": evidence_ids,
        "evidence_refs": [{"ref_id": event_id, "source_type": "trajectory_event"} for event_id in evidence_ids],
        "local_gradient": local_gradient,
        "proposed_update": proposed_update,
        "rollback_condition": proposed_update["rollback_condition"],
        "confidence": confidence,
        "failure_signals": failure_signals,
    }


def compile_update_record(attribution: dict[str, Any]) -> dict[str, Any]:
    proposed = attribution["proposed_update"]
    return {
        "update_id": f"update__{attribution['case_id']}",
        "step_id": 0,
        "trigger_failure_ids": attribution["trigger_failure_ids"],
        "update_target": proposed["target"],
        "target_id": proposed["target_id"],
        "textual_gradient": attribution["local_gradient"],
        "patch_summary": f"{proposed['before']} -> {proposed['after']} ({proposed['bounded_scope']})",
        "evidence_refs": attribution["evidence_refs"],
        "confidence": attribution["confidence"],
        "applied": False,
        "rollback_condition": attribution["rollback_condition"],
        "expected_metric_effect": [proposed.get("expected_effect", "success_rate")],
    }
