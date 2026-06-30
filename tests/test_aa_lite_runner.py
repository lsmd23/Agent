"""Tests for AA lite escalation runner."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from experiments.ablations.aa_ablation_specs import ABLATION_SPECS
from experiments.cascade.aa_lite_runner import AA_LITE_ABLATION_ID, STAGE_AA_LITE, run_aa_lite_llm
from experiments.cascade.cascade_policy import cascade_baseline_id
from experiments.real_benchmarks.llm_client import LLMClient

CODE_TASK = {
    "task_id": "phase1_code_csv_001",
    "benchmark_id": "phase1_mixed",
    "task_family": "code_agent_task",
    "prompt": "Fix csv parser.",
    "budget": {"max_steps": 4, "max_activation_cost": 3.0},
    "success_oracle": {"oracle_type": "pytest_passes", "fixture_id": "parse_csv_row_001"},
}


class AALiteRunnerTests(unittest.TestCase):
    def test_spec_overrides(self) -> None:
        spec = ABLATION_SPECS[AA_LITE_ABLATION_ID]
        overrides = spec["overrides"]
        self.assertFalse(overrides["verifier_enabled"])
        self.assertFalse(overrides["memory_enabled"])
        self.assertFalse(overrides["adaptive_top_k_enabled"])

    def test_cascade_baseline_id(self) -> None:
        self.assertEqual(cascade_baseline_id("react_aa_lite"), "cascade_react_aa_lite_llm")

    @patch("experiments.cascade.aa_lite_runner.run_aa_ablation_llm")
    def test_run_aa_lite_reports_stage_id(self, mock_run) -> None:
        mock_run.return_value = {"baseline_id": STAGE_AA_LITE, "final_success_label": "pass"}
        client = LLMClient(provider="openai", model="mock")
        out = run_aa_lite_llm(CODE_TASK, client)
        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.kwargs["report_baseline_id"], STAGE_AA_LITE)
        self.assertEqual(out["baseline_id"], STAGE_AA_LITE)


if __name__ == "__main__":
    unittest.main()
