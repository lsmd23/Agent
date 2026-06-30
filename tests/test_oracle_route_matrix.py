"""Tests for oracle route matrix analysis (Brief A)."""

from __future__ import annotations

import unittest

from experiments.analysis.oracle_route_matrix import analyze, classify_outcome, route_reward


class OracleRouteMatrixTests(unittest.TestCase):
    def test_route_reward_prefers_success_over_cost(self) -> None:
        cheap_fail = {"success": False, "model_calls": 1, "total_tokens": 100, "latency_ms": 100}
        costly_pass = {"success": True, "model_calls": 3, "total_tokens": 900, "latency_ms": 3000}
        self.assertGreater(route_reward(costly_pass), route_reward(cheap_fail))

    def test_analyze_finds_oracle_improvement(self) -> None:
        summary = {
            "suite": "test",
            "tasks": 2,
            "model": "mock",
            "provider": "mock",
            "baselines": {
                "cheap": {
                    "accuracy": 0.5,
                    "correct": 1,
                    "mean_model_calls": 1.0,
                    "cost_normalized_success": 0.5,
                },
                "strong": {
                    "accuracy": 0.5,
                    "correct": 1,
                    "mean_model_calls": 2.0,
                    "cost_normalized_success": 0.25,
                },
            },
            "per_task": [
                {
                    "baseline_id": "cheap",
                    "task_id": "t1",
                    "success": True,
                    "model_calls": 1,
                    "total_tokens": 100,
                    "latency_ms": 100,
                },
                {
                    "baseline_id": "strong",
                    "task_id": "t1",
                    "success": False,
                    "model_calls": 2,
                    "total_tokens": 200,
                    "latency_ms": 200,
                },
                {
                    "baseline_id": "cheap",
                    "task_id": "t2",
                    "success": False,
                    "model_calls": 1,
                    "total_tokens": 100,
                    "latency_ms": 100,
                },
                {
                    "baseline_id": "strong",
                    "task_id": "t2",
                    "success": True,
                    "model_calls": 2,
                    "total_tokens": 200,
                    "latency_ms": 200,
                },
            ],
        }
        result = analyze(summary)
        self.assertEqual(result["aggregate"]["oracle_success"], 1.0)
        self.assertEqual(result["aggregate"]["best_single_baseline_by_success"], "cheap")
        self.assertEqual(result["aggregate"]["oracle_vs_best_single_success_gap"], 0.5)
        self.assertIn(result["aggregate"]["evidence_outcome"], {"supports_direction", "weak_or_inconclusive"})

    def test_classify_outcome_dominance(self) -> None:
        label = classify_outcome(
            winner_entropy=0.2,
            max_entropy=2.32,
            success_gap=0.0,
            route_opportunity_gap=0.01,
            dominant_share=0.92,
            unique_rescue_total=0,
            n_tasks=26,
        )
        self.assertEqual(label, "falsified_or_blocked")


if __name__ == "__main__":
    unittest.main()
