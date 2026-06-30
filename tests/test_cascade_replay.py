"""Tests for cascade replay (Brief B)."""

from __future__ import annotations

import unittest

from experiments.cascade.cascade_replay import analyze, replay_policy, simulate_task


MINI_SUMMARY = {
    "suite": "test",
    "tasks": 3,
    "baselines": {
        "single_react_llm_agent": {
            "accuracy": 0.667,
            "mean_model_calls": 1.0,
            "cost_normalized_success": 0.667,
        },
        "agent_attention_llm_tuned": {
            "accuracy": 0.667,
            "mean_model_calls": 2.0,
            "cost_normalized_success": 0.333,
        },
        "moa_style_llm_agent": {
            "accuracy": 1.0,
            "mean_model_calls": 2.0,
            "cost_normalized_success": 0.5,
        },
    },
    "per_task": [
        {"baseline_id": "single_react_llm_agent", "task_id": "t1", "success": True, "model_calls": 1, "total_tokens": 10, "latency_ms": 100},
        {"baseline_id": "agent_attention_llm_tuned", "task_id": "t1", "success": True, "model_calls": 2, "total_tokens": 20, "latency_ms": 200},
        {"baseline_id": "moa_style_llm_agent", "task_id": "t1", "success": True, "model_calls": 2, "total_tokens": 20, "latency_ms": 200},
        {"baseline_id": "single_react_llm_agent", "task_id": "t2", "success": False, "model_calls": 1, "total_tokens": 10, "latency_ms": 100},
        {"baseline_id": "agent_attention_llm_tuned", "task_id": "t2", "success": True, "model_calls": 2, "total_tokens": 20, "latency_ms": 200},
        {"baseline_id": "moa_style_llm_agent", "task_id": "t2", "success": True, "model_calls": 2, "total_tokens": 20, "latency_ms": 200},
        {"baseline_id": "single_react_llm_agent", "task_id": "t3", "success": False, "model_calls": 1, "total_tokens": 10, "latency_ms": 100},
        {"baseline_id": "agent_attention_llm_tuned", "task_id": "t3", "success": False, "model_calls": 2, "total_tokens": 20, "latency_ms": 200},
        {"baseline_id": "moa_style_llm_agent", "task_id": "t3", "success": True, "model_calls": 2, "total_tokens": 20, "latency_ms": 200},
    ],
}


class CascadeReplayTests(unittest.TestCase):
    def test_simulate_halts_on_first_success(self) -> None:
        by_baseline = {
            "single_react_llm_agent": {"success": True, "model_calls": 1, "total_tokens": 10, "latency_ms": 50},
            "agent_attention_llm_tuned": {"success": True, "model_calls": 2, "total_tokens": 20, "latency_ms": 100},
        }
        row = simulate_task("t1", ["single_react_llm_agent", "agent_attention_llm_tuned"], by_baseline)
        self.assertTrue(row["success"])
        self.assertEqual(row["halt_stage"], "single_react_llm_agent")
        self.assertEqual(row["model_calls"], 1)
        self.assertFalse(row["escalated"])

    def test_replay_rescues_through_stages(self) -> None:
        replay = replay_policy(MINI_SUMMARY, "react_aa_moa")
        self.assertEqual(replay["correct"], 3)
        self.assertEqual(replay["rescued_task_count"], 2)
        self.assertAlmostEqual(replay["mean_model_calls"], 3.0)

    def test_analyze_primary_outcome(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(MINI_SUMMARY, handle)
            path = handle.name
        try:
            result = analyze(path, policies=["react_aa_moa", "react_moa"])
            self.assertIn(result["evidence_outcome"], {"supports_direction", "weak_or_inconclusive"})
            self.assertLess(
                result["policies"]["react_moa"]["mean_model_calls"],
                result["policies"]["react_aa_moa"]["mean_model_calls"],
            )
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
