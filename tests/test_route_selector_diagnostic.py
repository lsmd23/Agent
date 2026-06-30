"""Tests for route selector diagnostic (Brief E)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.analysis.route_selector_diagnostic import (
    build_examples,
    classify_outcome,
    extract_route_features,
    predict_lexical_route,
    route_metrics,
    run_diagnostic,
    split_examples,
    train_route_logistic,
)


def _matrix_row(task_id: str, label: str, *, success_routes: list[str]) -> dict:
    baselines = {}
    for route in (
        "agent_attention_llm_tuned",
        "fixed_workflow_llm_agent",
        "moa_style_llm_agent",
        "retrieval_memory_llm_agent",
        "single_react_llm_agent",
    ):
        success = route in success_routes
        baselines[route] = {
            "success": success,
            "model_calls": 1 if success else 2,
            "total_tokens": 400,
            "latency_ms": 800,
            "route_reward": 0.8 if success else 0.1,
            "cost_normalized_success": 1.0 if success else 0.0,
            "regret_vs_oracle_reward": 0.0 if route == label else 0.2,
        }
    return {
        "task_id": task_id,
        "any_route_success": bool(success_routes),
        "oracle_success": 1,
        "cheapest_successful_route": label,
        "cheapest_successful_model_calls": 1,
        "best_reward_route": label,
        "oracle_route_reward": 0.8,
        "oracle_cost_normalized_success": 1.0,
        "solo_success_baselines": [],
        "baselines": baselines,
    }


class RouteSelectorDiagnosticTests(unittest.TestCase):
    def test_split_field_is_deterministic(self) -> None:
        matrix = {
            "per_task": [
                _matrix_row("phase1_code_config_001", "single_react_llm_agent", success_routes=["single_react_llm_agent"]),
                _matrix_row("phase1_code_sanitize_001", "fixed_workflow_llm_agent", success_routes=["fixed_workflow_llm_agent"]),
            ]
        }
        tasks = {
            "phase1_code_config_001": {
                "task_id": "phase1_code_config_001",
                "split": "phase1",
                "prompt": "Fix config mismatch",
                "tags": ["config"],
            },
            "phase1_code_sanitize_001": {
                "task_id": "phase1_code_sanitize_001",
                "split": "phase1_expanded",
                "prompt": "escape_html must sanitize",
                "tags": ["security"],
            },
        }
        examples = build_examples(matrix, tasks)
        train, test = split_examples(examples, strategy="split_field")
        self.assertEqual([ex["task_id"] for ex in train], ["phase1_code_config_001"])
        self.assertEqual([ex["task_id"] for ex in test], ["phase1_code_sanitize_001"])

    def test_route_metrics_counts_accuracy_and_regret(self) -> None:
        row = _matrix_row("t1", "single_react_llm_agent", success_routes=["single_react_llm_agent"])
        metrics = route_metrics({"t1": "single_react_llm_agent"}, [row])
        self.assertEqual(metrics["route_accuracy"], 1.0)
        self.assertEqual(metrics["mean_regret_vs_oracle_reward"], 0.0)

    def test_lexical_route_prefers_memory_probe(self) -> None:
        task = {
            "prompt": "ignore stale memories and fix the test",
            "tags": ["memory", "negative_transfer"],
            "negative_transfer_probe": {"enabled": True},
        }
        features = extract_route_features(
            task,
            _matrix_row(
                "phase0_seed_negative_memory_001",
                "fixed_workflow_llm_agent",
                success_routes=["fixed_workflow_llm_agent"],
            ),
        )
        self.assertEqual(predict_lexical_route(features, task), "retrieval_memory_llm_agent")

    def test_train_logistic_reaches_high_accuracy_on_separable_rows(self) -> None:
        rows = [
            ({"tag_config": 1.0, "tag_memory": 0.0, "prompt_words": 10.0}, "single_react_llm_agent"),
            ({"tag_config": 0.0, "tag_memory": 1.0, "prompt_words": 20.0}, "retrieval_memory_llm_agent"),
            ({"tag_config": 1.0, "tag_memory": 0.0, "prompt_words": 11.0}, "single_react_llm_agent"),
            ({"tag_config": 0.0, "tag_memory": 1.0, "prompt_words": 21.0}, "retrieval_memory_llm_agent"),
        ]
        policy = train_route_logistic(rows, epochs=600, learning_rate=0.12)
        self.assertEqual(policy.training_accuracy, 1.0)

    def test_classify_outcome_supports_direction(self) -> None:
        learned = {"route_accuracy": 0.5, "mean_regret_vs_oracle_reward": 0.05}
        static = {"route_accuracy": 0.3, "mean_regret_vs_oracle_reward": 0.12}
        lexical = {"route_accuracy": 0.35, "mean_regret_vs_oracle_reward": 0.10}
        self.assertEqual(
            classify_outcome(learned=learned, static=static, lexical=lexical, held_out_tasks=20),
            "supports_direction",
        )

    def test_run_diagnostic_on_tiny_matrix(self) -> None:
        matrix = {
            "suite": "test",
            "per_task": [
                _matrix_row("phase1_code_config_001", "single_react_llm_agent", success_routes=["single_react_llm_agent"]),
                _matrix_row("phase1_code_doc_001", "fixed_workflow_llm_agent", success_routes=["fixed_workflow_llm_agent"]),
                _matrix_row("phase1_code_sanitize_001", "single_react_llm_agent", success_routes=["single_react_llm_agent"]),
                _matrix_row("phase1_code_parse_int_001", "fixed_workflow_llm_agent", success_routes=["fixed_workflow_llm_agent"]),
            ],
        }
        tasks = [
            {"task_id": "phase1_code_config_001", "split": "phase1", "prompt": "config version mismatch", "tags": ["config"]},
            {"task_id": "phase1_code_doc_001", "split": "phase1", "prompt": "documentation examples disagree", "tags": ["docs"]},
            {"task_id": "phase1_code_sanitize_001", "split": "phase1_expanded", "prompt": "escape_html sanitize", "tags": ["security"]},
            {"task_id": "phase1_code_parse_int_001", "split": "phase1_expanded", "prompt": "safe_int parse empty", "tags": ["parsing"]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oracle_path = root / "oracle.json"
            tasks_path = root / "tasks.jsonl"
            oracle_path.write_text(json.dumps(matrix), encoding="utf-8")
            tasks_path.write_text("\n".join(json.dumps(task) for task in tasks) + "\n", encoding="utf-8")
            result = run_diagnostic(
                oracle_path=oracle_path,
                tasks_path=tasks_path,
                split_strategy="split_field",
            )
        self.assertEqual(result["split"]["train_tasks"], 2)
        self.assertEqual(result["split"]["test_tasks"], 2)
        self.assertIn(result["evidence_outcome"], {"supports_direction", "weak_or_inconclusive", "falsified_or_blocked"})


if __name__ == "__main__":
    unittest.main()
