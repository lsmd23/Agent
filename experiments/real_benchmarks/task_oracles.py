"""Task success oracles for real LLM evaluation."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import success_label_for
from experiments.real_benchmarks.run_gsm8k_llm import exact_match, extract_model_answer


def evaluate_task_success(task: dict[str, Any], state: Any) -> tuple[str, dict[str, Any]]:
    oracle = task.get("success_oracle", {})
    oracle_type = oracle.get("oracle_type", "")
    final_text = state.final_answer or ""

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
                "prediction": prediction,
                "gold_answer": gold,
                "exact_match": passed,
            },
        )

    route_label = success_label_for(task, state)
    return route_label, {"oracle_type": oracle_type or "route_proxy", "route_oracle_label": route_label}
