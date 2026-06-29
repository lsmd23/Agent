import json
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORER_PATH = ROOT / "docs/deliverables/07/scoring_script.py"
SPEC = importlib.util.spec_from_file_location("scoring_script", SCORER_PATH)
scoring_script = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(scoring_script)


class ScoringTests(unittest.TestCase):
    def test_target_envelope_preserves_known_deviations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
                        "task_id": "task",
                        "benchmark_id": "bench",
                        "baseline_id": "agent_attention_agent",
                        "final_success_label": "pass",
                        "known_deviations": ["toy_deviation"],
                        "events": [
                            {
                                "event_id": 1,
                                "step": 0,
                                "kind": "halt_gate",
                                "payload": {
                                    "halt": True,
                                    "reason": "answer_ready",
                                    "success_signal": "pass",
                                    "budget_snapshot": {"remaining_budget": 1.0},
                                },
                            },
                            {
                                "event_id": 2,
                                "step": 0,
                                "kind": "finish",
                                "payload": {"final_answer": "done", "selected_modules": []},
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            run = scoring_script.score_trajectory(path)

        self.assertEqual(run["task_id"], "task")
        self.assertTrue(run["final"]["task_success"])
        self.assertIn("toy_deviation", run["known_deviations"])

    def test_target_envelope_scores_proxy_route_regret(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
                        "task_id": "task",
                        "benchmark_id": "bench",
                        "baseline_id": "agent_attention_agent",
                        "final_success_label": "fail",
                        "events": [
                            {
                                "event_id": 1,
                                "step": 1,
                                "kind": "route",
                                "payload": {
                                    "selected_modules": ["search_agent"],
                                    "candidates": [
                                        {"module_id": "code_agent", "score": 0.8, "selected": False},
                                        {"module_id": "search_agent", "score": 0.4, "selected": True},
                                    ],
                                    "oracle": {"proxy_regret": 0.75},
                                },
                            },
                            {
                                "event_id": 2,
                                "step": 1,
                                "kind": "halt_gate",
                                "payload": {
                                    "halt": True,
                                    "reason": "budget_exhausted",
                                    "success_signal": "fail",
                                    "budget_snapshot": {"remaining_budget": 0.0},
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            run = scoring_script.score_trajectory(path)

        self.assertEqual(run["routing"]["proxy_route_regret_mean"], 0.75)
        self.assertNotIn("proxy_route_regret_unavailable", run["known_deviations"])


if __name__ == "__main__":
    unittest.main()
