"""Task success oracles for real LLM evaluation."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import success_label_for
from experiments.real_benchmarks.code_verifier import (
    agent_text_from_state,
    fixture_id_for_task,
    verify_code_task,
)
from experiments.real_benchmarks.run_gsm8k_llm import exact_match, extract_model_answer


def evaluate_route_alignment(task: dict[str, Any], state: Any) -> tuple[str, dict[str, Any]]:
    route_label = success_label_for(task, state)
    aligned = route_label in {"pass", "partial"}
    return route_label, {
        "route_oracle_label": route_label,
        "route_aligned": aligned,
    }


def evaluate_task_success(task: dict[str, Any], state: Any) -> tuple[str, dict[str, Any]]:
    oracle = task.get("success_oracle", {})
    oracle_type = oracle.get("oracle_type", "")
    final_text = state.final_answer or ""

    if fixture_id_for_task(task["task_id"]) is not None or oracle_type in {"pytest_passes", "executable_pytest", "synthetic_runtime"}:
        if fixture_id_for_task(task["task_id"]) is not None:
            agent_text = agent_text_from_state(state)
            pytest_result = verify_code_task(task["task_id"], agent_text)
            route_label, route_metrics = evaluate_route_alignment(task, state)
            end_task_label = "pass" if pytest_result.passed else "fail"
            return end_task_label, {
                "oracle_type": "executable_pytest",
                "end_task_success": pytest_result.passed,
                "fixture_id": pytest_result.fixture_id,
                "pytest_returncode": pytest_result.returncode,
                "applied_files": pytest_result.applied_files,
                "patch_apply_mode": pytest_result.apply_mode,
                "pytest_stdout": pytest_result.stdout[-2000:] if pytest_result.stdout else "",
                "pytest_stderr": pytest_result.stderr[-2000:] if pytest_result.stderr else "",
                **route_metrics,
            }

    if oracle_type == "exact_numeric_match" or task.get("gold_answer") is not None:
        gold = str(task.get("gold_answer", ""))
        prediction = extract_model_answer(final_text)
        if prediction is None:
            for obs in reversed(state.observations):
                if isinstance(obs, str):
                    prediction = extract_model_answer(obs)
                    if prediction:
                        break
        passed = exact_match(prediction, gold)
        return (
            "pass" if passed else "fail",
            {
                "oracle_type": "exact_numeric_match",
                "end_task_success": passed,
                "prediction": prediction,
                "gold_answer": gold,
                "exact_match": passed,
            },
        )

    route_label, route_metrics = evaluate_route_alignment(task, state)
    return route_label, {"oracle_type": oracle_type or "route_proxy", **route_metrics}
