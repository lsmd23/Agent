"""Tests for real-task textual backprop diagnostic."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.analysis.real_task_backprop_diagnostic import (  # noqa: E402
    failed_matrix_rows,
    matrix_success_by_task,
    pick_held_out_success_task,
    resolve_trajectory_path,
    write_summary,
)
from experiments.baselines.common import load_jsonl  # noqa: E402


class RealTaskBackpropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix_path = ROOT / "experiments/metrics/code_full_matrix_summary.json"
        cls.summary = json.loads(cls.matrix_path.read_text(encoding="utf-8"))
        cls.tasks = load_jsonl(ROOT / "experiments/tasks/phase1_code_all.jsonl")
        cls.trajectory_root = ROOT / "experiments/llm_runs/code_full_matrix/code_all"

    def test_failed_rows_for_aa_tuned(self) -> None:
        rows = failed_matrix_rows(self.summary, baseline_id="agent_attention_llm_tuned")
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertFalse(row["success"])
            self.assertEqual(row["baseline_id"], "agent_attention_llm_tuned")

    def test_resolve_trajectory_path(self) -> None:
        rows = failed_matrix_rows(self.summary, baseline_id="agent_attention_llm_tuned")
        path = resolve_trajectory_path(
            rows[0],
            self.trajectory_root,
            baseline_id="agent_attention_llm_tuned",
        )
        self.assertTrue(path.exists())
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["task_id"], rows[0]["task_id"])

    def test_pick_held_out_prefers_success(self) -> None:
        success_map = matrix_success_by_task(self.summary, baseline_id="agent_attention_llm_tuned")
        failed_task = next(t for t in self.tasks if t["task_id"] == "phase1_code_config_001")
        held_out = pick_held_out_success_task(self.tasks, failed_task, success_map)
        self.assertIsNotNone(held_out)
        assert held_out is not None
        self.assertNotEqual(held_out["task_id"], failed_task["task_id"])
        self.assertTrue(success_map.get(held_out["task_id"], False))

    def test_write_summary_schema(self) -> None:
        out = ROOT / "experiments/metrics/_test_real_task_backprop_summary.json"
        try:
            summary = write_summary(
                [],
                out,
                baseline_id="agent_attention_llm_tuned",
                matrix_path="experiments/metrics/code_full_matrix_summary.json",
                task_count=26,
            )
            self.assertIn("decision_counts", summary)
            self.assertEqual(summary["llm_calls_during_diagnostic"], 0)
            self.assertEqual(summary["t7_deliverable"], "real_task_backprop_summary.json")
        finally:
            if out.exists():
                out.unlink()


if __name__ == "__main__":
    unittest.main()
