"""Tests for unified real LLM faithful runners (mocked)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from experiments.real_benchmarks.faithful_llm_runners import (
    FAITHFUL_LLM_ID_MAP,
    run_faithful_llm,
    run_memory_ablation_llm,
)
from experiments.real_benchmarks.llm_client import LLMClient


GSM8K_TASK = {
    "task_id": "gsm8k_test_0000",
    "benchmark_id": "gsm8k_test",
    "task_family": "math_word_problem",
    "prompt": "Janet sells 9 eggs at $2 each. How much does she make?",
    "gold_answer": "18",
    "budget": {"max_steps": 4, "max_activation_cost": 5.0, "max_tokens": 128, "temperature": 0.0},
}

PHASE1_TASK = {
    "task_id": "phase1_code_config_001",
    "benchmark_id": "phase1_mixed",
    "task_family": "code_agent_task",
    "prompt": "Fix a failing Python test caused by a dependency version mismatch.",
    "budget": {"max_steps": 4, "max_activation_cost": 3.0},
    "expected_route": {
        "required_modules": ["code_agent"],
        "discouraged_modules": ["search_agent"],
        "oracle_best_module_id": "code_agent",
    },
    "memory_setup": {"injected_memory_ids": ["seed:code_route"], "quarantined_memory_ids": []},
    "negative_transfer_probe": {"enabled": False},
    "success_oracle": {"oracle_type": "pytest_passes", "fixture_id": "version_parse_001"},
}


def mock_complete(_self, prompt: str, *, module_id: str = "llm"):
    if "math" in prompt.lower() or "egg" in prompt.lower() or "####" in prompt:
        text = "Reasoning steps.\n#### 18"
    elif "Repository snapshot:" in prompt:
        text = (
            "```python\n"
            "# file: lib/version_util.py\n"
            "def parse_version(version: str) -> tuple[int, ...]:\n"
            "    return tuple(int(part) for part in version.split('.'))\n\n"
            "def is_compatible(required: str, installed: str) -> bool:\n"
            "    return parse_version(installed) >= parse_version(required)\n"
            "```"
        )
    else:
        text = (
            f"Module {module_id}: inspect repo, patch requirements.txt, run pytest. "
            "Plan uses code_agent workflow."
        )
    metadata = {"usage": {"total_tokens": 10}}
    record = {
        "module_id": module_id,
        "provider": _self.provider,
        "model": _self.model,
        "prompt": prompt,
        "output": text,
        "latency_ms": 3,
        "usage": metadata,
    }
    _self.calls.append(record)
    return text, metadata, 3


class FaithfulLLMRunnerTests(unittest.TestCase):
    def _client(self) -> LLMClient:
        return LLMClient(provider="openai", model="mock-model", max_tokens=64, temperature=0.0)

    @patch.object(LLMClient, "complete", mock_complete)
    def test_all_faithful_llm_baselines_run_gsm8k(self) -> None:
        for llm_id in FAITHFUL_LLM_ID_MAP.values():
            traj = run_faithful_llm(llm_id, GSM8K_TASK, self._client())
            self.assertEqual(traj["baseline_id"], llm_id)
            self.assertIn(traj["final_success_label"], {"pass", "fail", "partial"})
            self.assertGreaterEqual(traj["metrics_summary"]["model_calls"], 1)

    @patch.object(LLMClient, "complete", mock_complete)
    def test_single_react_llm_phase1_route_oracle(self) -> None:
        traj = run_faithful_llm("single_react_llm_agent", PHASE1_TASK, self._client())
        self.assertEqual(traj["baseline_id"], "single_react_llm_agent")
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertTrue(traj["metrics_summary"]["end_task_success"])

    @patch.object(LLMClient, "complete", mock_complete)
    def test_memory_ablation_llm_runs(self) -> None:
        traj = run_memory_ablation_llm("aa_no_memory", PHASE1_TASK, self._client())
        self.assertEqual(traj["ablation_id"], "aa_no_memory_llm")
        self.assertGreaterEqual(traj["metrics_summary"]["model_calls"], 1)


if __name__ == "__main__":
    unittest.main()
