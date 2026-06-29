"""Tests for real-LLM Agent-Attention and ReAct baselines (mocked, no live calls)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from experiments.real_benchmarks.agent_attention_llm_runtime import run_agent_attention_llm
from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.llm_react_agent import run_llm_react
from experiments.real_benchmarks.run_gsm8k_llm import run_llm_direct


SAMPLE_TASK = {
    "task_id": "gsm8k_test_0000",
    "benchmark_id": "gsm8k_test",
    "task_family": "math_word_problem",
    "prompt": "Janet sells 9 eggs at $2 each. How much does she make?",
    "gold_answer": "18",
    "budget": {"max_tokens": 128, "temperature": 0.0, "max_model_calls": 1},
}


def mock_complete(_self, prompt: str, *, module_id: str = "llm"):
    text = "Step by step reasoning.\n#### 18"
    metadata = {"usage": {"total_tokens": 10}}
    latency_ms = 5
    record = {
        "module_id": module_id,
        "provider": _self.provider,
        "model": _self.model,
        "prompt": prompt,
        "output": text,
        "latency_ms": latency_ms,
        "usage": metadata,
    }
    _self.calls.append(record)
    return text, metadata, latency_ms


class AgentAttentionLLMTests(unittest.TestCase):
    def _client(self) -> LLMClient:
        return LLMClient(provider="openai", model="mock-model", max_tokens=64, temperature=0.0)

    @patch.object(LLMClient, "complete", mock_complete)
    def test_run_llm_direct_passes(self) -> None:
        traj = run_llm_direct(SAMPLE_TASK, self._client())
        self.assertEqual(traj["baseline_id"], "llm_direct_agent")
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertEqual(traj["metrics_summary"]["prediction"], "18")

    @patch.object(LLMClient, "complete", mock_complete)
    def test_run_llm_react_passes(self) -> None:
        traj = run_llm_react(SAMPLE_TASK, self._client(), max_steps=2)
        self.assertEqual(traj["baseline_id"], "llm_react_agent")
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertEqual(traj["metrics_summary"]["model_calls"], 1)

    @patch.object(LLMClient, "complete", mock_complete)
    def test_run_agent_attention_llm_passes(self) -> None:
        traj = run_agent_attention_llm(SAMPLE_TASK, self._client())
        self.assertEqual(traj["baseline_id"], "agent_attention_llm_tuned")
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertGreaterEqual(traj["metrics_summary"]["model_calls"], 1)
        self.assertTrue(traj["events"])
        self.assertIn("selected_modules", traj["metrics_summary"])


if __name__ == "__main__":
    unittest.main()
