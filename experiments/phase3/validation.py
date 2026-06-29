"""Replay and held-out validation for textual updates."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import envelope_for, success_label_for
from experiments.baselines.memory_ablations import ablation_config_for, build_memory_ablation_runtime
from experiments.phase3.runtime_patches import PatchedTunedRuntime, RuntimePatch, build_patched_runtime

ACCEPT_CONFIDENCE_MIN = 0.70
REPLAY_DELTA_MIN = 0.01
QUARANTINE_CONFIDENCE_MIN = 0.45
REJECT_CONFIDENCE_BELOW = 0.45


def run_metrics_for_task(
    task: dict[str, Any],
    runtime: Any,
    *,
    run_prefix: str = "phase3_replay",
    ablation_id: str = "aa_tuned_control",
    patches: list[RuntimePatch] | None = None,
) -> dict[str, Any]:
    max_steps = int(task["budget"]["max_steps"])
    max_budget = float(task["budget"]["max_activation_cost"])
    state = runtime.run(task["prompt"], max_budget=max_budget)
    config = ablation_config_for(ablation_id)
    if patches:
        config = {**config, "applied_patches": [patch.patch_id for patch in patches]}
    envelope = envelope_for(
        task,
        config["baseline_id"],
        config,
        state,
        runtime.events,
        simulation=False,
        run_prefix=run_prefix,
        ablation_id=ablation_id,
    )
    success = 1.0 if success_label_for(task, state) == "pass" else 0.0
    activation_cost = float(state.budget_used)
    cost_norm = success / max(activation_cost, 0.01)
    return {
        "task_id": task["task_id"],
        "task_success": success,
        "success_label": envelope["final_success_label"],
        "activation_cost": round(activation_cost, 6),
        "cost_normalized_success": round(cost_norm, 6),
        "steps": int(state.step),
        "envelope": envelope,
        "state": state,
    }


def replay_validation(
    task: dict[str, Any],
    patches: list[RuntimePatch],
    *,
    validation_id: str,
    ablation_id: str = "aa_tuned_control",
) -> dict[str, Any]:
    max_steps = int(task["budget"]["max_steps"])
    before_runtime = build_memory_ablation_runtime(ablation_id, task, max_steps)
    after_runtime = build_patched_runtime(task, max_steps, patches, ablation_id=ablation_id)

    before = run_metrics_for_task(task, before_runtime, ablation_id=ablation_id)
    after = run_metrics_for_task(
        task,
        after_runtime,
        ablation_id=ablation_id,
        patches=patches,
    )

    primary_delta = after["task_success"] - before["task_success"]
    cost_delta = after["cost_normalized_success"] - before["cost_normalized_success"]
    replay_improved = primary_delta >= REPLAY_DELTA_MIN or (
        primary_delta >= 0 and cost_delta >= REPLAY_DELTA_MIN
    )

    regression_checks = [
        {
            "metric": "task_success",
            "status": "pass" if primary_delta >= 0 else "fail",
            "threshold": 0.0,
            "observed_delta": round(primary_delta, 6),
        },
        {
            "metric": "cost_normalized_success",
            "status": "pass" if cost_delta >= -REPLAY_DELTA_MIN else "warn",
            "threshold": -REPLAY_DELTA_MIN,
            "observed_delta": round(cost_delta, 6),
        },
    ]

    recommendation = "accept" if replay_improved else "reject"
    verification_status = "pass" if replay_improved else "fail"

    return {
        "validation_id": validation_id,
        "mode": "failure_replay",
        "task_ids": [task["task_id"]],
        "before_metrics": {
            "task_success": before["task_success"],
            "cost_normalized_success": before["cost_normalized_success"],
            "activation_cost": before["activation_cost"],
        },
        "after_metrics": {
            "task_success": after["task_success"],
            "cost_normalized_success": after["cost_normalized_success"],
            "activation_cost": after["activation_cost"],
        },
        "regression_checks": regression_checks,
        "verification_status_after": {"status": verification_status, "check_refs": [validation_id]},
        "decision_recommendation": recommendation,
        "before_envelope": before["envelope"],
        "after_envelope": after["envelope"],
        "replay_improved": replay_improved,
        "primary_delta": round(primary_delta, 6),
        "cost_delta": round(cost_delta, 6),
    }


def held_out_validation(
    held_out_task: dict[str, Any],
    patches: list[RuntimePatch],
    *,
    validation_id: str,
    ablation_id: str = "aa_tuned_control",
) -> dict[str, Any]:
    max_steps = int(held_out_task["budget"]["max_steps"])
    before_runtime = build_memory_ablation_runtime(ablation_id, held_out_task, max_steps)
    after_runtime = build_patched_runtime(held_out_task, max_steps, patches, ablation_id=ablation_id)

    before = run_metrics_for_task(held_out_task, before_runtime, ablation_id=ablation_id)
    after = run_metrics_for_task(
        held_out_task,
        after_runtime,
        ablation_id=ablation_id,
        patches=patches,
    )

    success_delta = after["task_success"] - before["task_success"]
    regression = success_delta < -REPLAY_DELTA_MIN
    recommendation = "reject" if regression else "accept"

    return {
        "validation_id": validation_id,
        "mode": "held_out",
        "task_ids": [held_out_task["task_id"]],
        "before_metrics": {
            "task_success": before["task_success"],
            "cost_normalized_success": before["cost_normalized_success"],
        },
        "after_metrics": {
            "task_success": after["task_success"],
            "cost_normalized_success": after["cost_normalized_success"],
        },
        "regression_checks": [
            {
                "metric": "task_success",
                "status": "fail" if regression else "pass",
                "threshold": -REPLAY_DELTA_MIN,
                "observed_delta": round(success_delta, 6),
            }
        ],
        "verification_status_after": {
            "status": "fail" if regression else "pass",
            "check_refs": [validation_id],
        },
        "decision_recommendation": recommendation,
        "held_out_regression": regression,
    }


def pick_held_out_task(tasks: list[dict[str, Any]], failed_task: dict[str, Any]) -> dict[str, Any] | None:
    family = failed_task.get("task_family")
    candidates = [
        task
        for task in tasks
        if task["task_id"] != failed_task["task_id"] and task.get("task_family") == family
    ]
    if not candidates:
        candidates = [task for task in tasks if task["task_id"] != failed_task["task_id"]]
    return candidates[0] if candidates else None


def decide_envelope(
    attribution: dict[str, Any],
    replay_run: dict[str, Any],
    held_out_run: dict[str, Any] | None,
) -> tuple[str, str, str]:
    confidence = float(attribution["confidence"])
    replay_improved = bool(replay_run.get("replay_improved"))

    if confidence < REJECT_CONFIDENCE_BELOW:
        return "reject", "confidence_below_threshold", "complete"
    if not replay_improved:
        return "reject", "replay_no_improvement", "complete"
    if confidence >= ACCEPT_CONFIDENCE_MIN and replay_improved:
        if held_out_run is None:
            return "quarantine", "replay_improved_missing_held_out", "missing_held_out"
        if held_out_run.get("held_out_regression"):
            return "quarantine", "held_out_regression_guard", "complete"
        return "accept", "replay_and_held_out_pass", "complete"
    if confidence >= QUARANTINE_CONFIDENCE_MIN and replay_improved:
        return "quarantine", "medium_confidence_replay_improved", "complete"
    return "reject", "insufficient_confidence_for_replay_gain", "complete"


def build_textual_update_envelope(
    attribution: dict[str, Any],
    update_record: dict[str, Any],
    replay_run: dict[str, Any],
    held_out_run: dict[str, Any] | None,
) -> dict[str, Any]:
    decision, decision_reason, audit_status = decide_envelope(attribution, replay_run, held_out_run)
    validation_runs = [replay_run]
    if held_out_run is not None:
        validation_runs.append(held_out_run)

    quarantine_reason = None
    if decision == "quarantine":
        quarantine_reason = decision_reason

    update_record = dict(update_record)
    update_record["applied"] = decision == "accept"

    return {
        "envelope_id": f"envelope__{attribution['case_id']}",
        "attribution_case": attribution,
        "update_record_patch": update_record,
        "validation_runs": validation_runs,
        "decision": decision,
        "decision_reason": decision_reason,
        "quarantine_reason": quarantine_reason,
        "audit_status": audit_status,
    }
