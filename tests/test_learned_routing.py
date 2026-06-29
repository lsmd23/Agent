"""Tests for Phase 4 learned routing."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baselines.common import load_jsonl, success_label_for  # noqa: E402
from experiments.phase4.learned_router_policy import LearnedRouterPolicy, train_logistic_router  # noqa: E402
from experiments.phase4.oracle_matrix import build_oracle_matrix, oracle_label, oracle_regret_for_selection  # noqa: E402
from experiments.phase4.route_features import extract_features  # noqa: E402
from experiments.phase4.router_variants import build_router_variant_runtime  # noqa: E402
from experiments.phase4.train_learned_router import synthetic_oracle_rows as train_rows  # noqa: E402
from src.agent_attention_runtime import RuntimeState, build_default_runtime  # noqa: E402


class LearnedRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tasks = load_jsonl(ROOT / "experiments/tasks/phase1_tasks.jsonl")
        cls.code_task = next(task for task in cls.tasks if task["task_id"] == "phase1_code_config_001")

    def test_oracle_matrix_has_entries(self) -> None:
        matrix = build_oracle_matrix(self.tasks)
        self.assertEqual(matrix["task_count"], 12)
        entry = matrix["entries_by_task_id"]["phase1_code_config_001"]
        self.assertEqual(entry["oracle_best_module_id"], "code_agent")

    def test_oracle_label_prefers_required_modules(self) -> None:
        self.assertEqual(oracle_label(self.code_task, "code_agent"), 1)
        self.assertEqual(oracle_label(self.code_task, "search_agent"), 0)

    def test_train_logistic_router(self) -> None:
        rows = train_rows(self.tasks)
        policy = train_logistic_router(rows)
        self.assertGreater(policy.training_accuracy, 0.5)
        self.assertEqual(len(policy.weights), len(policy.feature_names) + 1)

    def test_learned_router_runtime_runs(self) -> None:
        rows = train_rows(self.tasks)
        policy = train_logistic_router(rows)
        runtime = build_router_variant_runtime(
            "aa_learned_router_replay",
            self.code_task,
            int(self.code_task["budget"]["max_steps"]),
            learned_policy=policy,
        )
        state = runtime.run(
            self.code_task["prompt"],
            max_budget=float(self.code_task["budget"]["max_activation_cost"]),
        )
        self.assertIn("code_agent", state.selected_modules)
        self.assertEqual(runtime.router_strategy, "learned")

    def test_oracle_router_reduces_regret_on_code_task(self) -> None:
        matrix = build_oracle_matrix([self.code_task])
        utilities = matrix["entries_by_task_id"][self.code_task["task_id"]]["module_utilities"]
        lexical = build_router_variant_runtime(
            "aa_lexical_router",
            self.code_task,
            int(self.code_task["budget"]["max_steps"]),
        )
        oracle = build_router_variant_runtime(
            "aa_oracle_router",
            self.code_task,
            int(self.code_task["budget"]["max_steps"]),
            oracle_utilities=utilities,
        )
        lexical_state = lexical.run(self.code_task["prompt"], max_budget=3.0)
        oracle_state = oracle.run(self.code_task["prompt"], max_budget=3.0)
        lexical_regret = oracle_regret_for_selection(self.code_task, lexical_state.selected_modules)
        oracle_regret = oracle_regret_for_selection(self.code_task, oracle_state.selected_modules)
        self.assertLessEqual(oracle_regret, lexical_regret)

    def test_policy_roundtrip_json(self) -> None:
        rows = train_rows(self.tasks[:4])
        policy = train_logistic_router(rows)
        path = ROOT / "experiments/phase4/_test_policy.json"
        policy.save(path)
        loaded = LearnedRouterPolicy.load(path)
        self.assertEqual(loaded.version, policy.version)
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
