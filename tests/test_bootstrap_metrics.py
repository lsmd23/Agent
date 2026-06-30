"""Tests for bootstrap metrics and T4 statistics."""

from __future__ import annotations

import unittest

from experiments.analysis.bootstrap_metrics import (
    bootstrap_accuracy,
    merge_summaries,
    paired_delta,
    pareto_frontier,
    task_cost_normalized,
    verdict_code_suite,
)


class BootstrapMetricsTests(unittest.TestCase):
    def test_task_cost_normalized(self) -> None:
        self.assertEqual(task_cost_normalized({"success": True, "model_calls": 2}), 0.5)
        self.assertEqual(task_cost_normalized({"success": False, "model_calls": 2}), 0.0)

    def test_bootstrap_accuracy_deterministic(self) -> None:
        values = [True, False, True, True]
        a = bootstrap_accuracy(values, n_samples=100, seed=42)
        b = bootstrap_accuracy(values, n_samples=100, seed=42)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a["mean"], 0.75)

    def test_pareto_frontier(self) -> None:
        baselines = {
            "cheap_ok": {"mean": 0.8, "mean_model_calls": 1.0},
            "expensive_best": {"mean": 1.0, "mean_model_calls": 3.0},
            "dominated": {"mean": 0.7, "mean_model_calls": 2.0},
        }
        frontier = pareto_frontier(baselines)
        self.assertIn("cheap_ok", frontier)
        self.assertIn("expensive_best", frontier)
        self.assertNotIn("dominated", frontier)

    def test_paired_delta(self) -> None:
        rows = [
            {"task_id": "t1", "baseline_id": "a", "success": True},
            {"task_id": "t1", "baseline_id": "b", "success": False},
            {"task_id": "t2", "baseline_id": "a", "success": True},
            {"task_id": "t2", "baseline_id": "b", "success": True},
        ]
        delta = paired_delta(rows, "a", "b")
        self.assertEqual(delta["wins_a"], 1)
        self.assertEqual(delta["wins_b"], 0)
        self.assertEqual(delta["ties"], 1)

    def test_merge_summaries(self) -> None:
        a = {"suite": "code", "tasks": 2, "model": "m", "provider": "p", "baselines": {"x": {}}, "per_task": [{"task_id": "t1"}]}
        b = {"baselines": {"y": {}}, "per_task": [{"task_id": "t2"}]}
        merged = merge_summaries([a, b], scope="test")
        self.assertEqual(merged["tasks"], 2)
        self.assertEqual(set(merged["baselines"]), {"x", "y"})

    def test_verdict_code_suite(self) -> None:
        analysis = {
            "baselines": {
                "single_react_llm_agent": {"mean": 0.88, "ci_low": 0.75, "ci_high": 0.95, "mean_model_calls": 1.2},
                "agent_attention_llm_tuned": {"mean": 0.84, "ci_low": 0.70, "ci_high": 0.92, "mean_model_calls": 2.0},
                "cascade_react_aa_lite_llm": {"mean": 1.0, "ci_low": 1.0, "ci_high": 1.0, "mean_model_calls": 1.5},
            },
            "pareto_frontier": ["cascade_react_aa_lite_llm", "single_react_llm_agent"],
        }
        v = verdict_code_suite(analysis)
        self.assertIn(v["cascade_aa_lite_vs_always_on_aa"], {"win", "inconclusive"})


if __name__ == "__main__":
    unittest.main()
