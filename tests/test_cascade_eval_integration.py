"""Integration tests for cascade baselines in unified eval harness."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from experiments.cascade.cascade_policy import (
    CASCADE_LLM_BASELINE_IDS,
    cascade_baseline_id,
    cascade_config_for,
    policy_id_from_baseline_id,
)
from experiments.cascade.cascade_runner import run_cascade_baseline_llm
from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.run_real_llm_eval import (
    ALL_REAL_LLM_BASELINES,
    baselines_for_family,
    resolve_runner,
)

CODE_TASK = {
    "task_id": "phase1_code_config_001",
    "benchmark_id": "phase1_mixed",
    "task_family": "code_agent_task",
    "prompt": "Fix failing pytest in repo snapshot.",
    "budget": {"max_steps": 4, "max_activation_cost": 3.0},
    "success_oracle": {"oracle_type": "pytest_passes", "fixture_id": "version_parse_001"},
}


def mock_faithful_pass(_baseline_id: str, task: dict, client: LLMClient) -> dict:
    client.calls.append(
        {
            "module_id": "code_agent",
            "provider": client.provider,
            "model": client.model,
            "prompt": task["prompt"],
            "output": "ok",
            "latency_ms": 5,
            "usage": {"total_tokens": 12},
        }
    )
    return {
        "run_id": f"mock__{_baseline_id}__{task['task_id']}",
        "baseline_id": _baseline_id,
        "final_success_label": "pass",
        "final_answer": "patch",
        "known_deviations": [],
        "metrics_summary": {
            "model_calls": 1,
            "total_tokens": 12,
            "latency_ms": 5,
            "oracle_type": "executable_pytest",
        },
    }


def mock_faithful_fail(_baseline_id: str, task: dict, client: LLMClient) -> dict:
    client.calls.append(
        {
            "module_id": "code_agent",
            "provider": client.provider,
            "model": client.model,
            "prompt": task["prompt"],
            "output": "bad",
            "latency_ms": 5,
            "usage": {"total_tokens": 10},
        }
    )
    return {
        "run_id": f"mock__{_baseline_id}__{task['task_id']}",
        "baseline_id": _baseline_id,
        "final_success_label": "fail",
        "final_answer": "bad",
        "known_deviations": [],
        "metrics_summary": {
            "model_calls": 1,
            "total_tokens": 10,
            "latency_ms": 5,
            "oracle_type": "executable_pytest",
        },
    }


class CascadeEvalIntegrationTests(unittest.TestCase):
    def test_baseline_ids_registered(self) -> None:
        self.assertIn("cascade_react_moa_llm", CASCADE_LLM_BASELINE_IDS)
        self.assertIn("cascade_react_moa_llm", ALL_REAL_LLM_BASELINES)

    def test_family_cascade(self) -> None:
        baselines = baselines_for_family("cascade")
        self.assertEqual(set(baselines), set(CASCADE_LLM_BASELINE_IDS))

    def test_policy_mapping(self) -> None:
        self.assertEqual(policy_id_from_baseline_id("cascade_react_moa_llm"), "react_moa")
        cfg = cascade_config_for("react_moa")
        self.assertEqual(cfg["controller_policy"], "cascade")
        self.assertEqual(cfg["cascade_stages"], ["single_react_llm_agent", "moa_style_llm_agent"])

    def test_resolve_runner_cascade(self) -> None:
        runner = resolve_runner("cascade_react_moa_llm")
        self.assertTrue(callable(runner))

    @patch(
        "experiments.cascade.cascade_runner.run_faithful_llm",
        side_effect=lambda baseline_id, task, client: mock_faithful_pass(baseline_id, task, client),
    )
    def test_cascade_halts_on_first_pass(self, _mock: object) -> None:
        client = LLMClient(provider="openai", model="mock", max_tokens=64)
        traj = run_cascade_baseline_llm("cascade_react_moa_llm", CODE_TASK, client)
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertEqual(traj["baseline_id"], "cascade_react_moa_llm")
        self.assertEqual(traj["metrics_summary"]["model_calls"], 1)
        self.assertFalse(traj["cascade"]["escalated"])
        self.assertEqual(traj["runtime_config"]["baseline_config"]["cascade_policy_id"], "react_moa")

    @patch(
        "experiments.cascade.cascade_runner.run_faithful_llm",
        side_effect=lambda baseline_id, task, client: (
            mock_faithful_fail(baseline_id, task, client)
            if baseline_id == "single_react_llm_agent"
            else mock_faithful_pass(baseline_id, task, client)
        ),
    )
    def test_cascade_escalates_to_moa(self, _mock: object) -> None:
        client = LLMClient(provider="openai", model="mock", max_tokens=64)
        traj = run_cascade_baseline_llm("cascade_react_moa_llm", CODE_TASK, client)
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertEqual(traj["metrics_summary"]["model_calls"], 2)
        self.assertTrue(traj["cascade"]["escalated"])
        self.assertEqual(traj["cascade"]["rescued_by"], "moa_style_llm_agent")

    def test_cascade_baseline_id_helper(self) -> None:
        self.assertEqual(cascade_baseline_id("react_moa"), "cascade_react_moa_llm")
        self.assertEqual(cascade_baseline_id("react_aa_lite"), "cascade_react_aa_lite_llm")

    @patch(
        "experiments.cascade.cascade_runner.run_cascade_stage",
        side_effect=lambda stage_id, task, client: (
            mock_faithful_fail(stage_id, task, client)
            if stage_id == "single_react_llm_agent"
            else mock_faithful_pass(stage_id, task, client)
        ),
    )
    def test_cascade_aa_lite_registered(self, _mock: object) -> None:
        client = LLMClient(provider="openai", model="mock", max_tokens=64)
        traj = run_cascade_baseline_llm("cascade_react_aa_lite_llm", CODE_TASK, client)
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertEqual(traj["cascade"]["halt_stage"], "agent_attention_llm_lite")
        self.assertEqual(traj["runtime_config"]["baseline_config"]["aa_lite_ablation_id"], "aa_lite_escalation")


if __name__ == "__main__":
    unittest.main()
