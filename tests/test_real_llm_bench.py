"""Tests for real LLM benchmark utilities (no live model calls)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.real_benchmarks.check_llm_environment import recommend_profile
from experiments.real_benchmarks.load_env import load_env_file, load_project_env
from experiments.real_benchmarks.run_gsm8k_llm import build_prompt, trajectory_for


class RealLLMBenchTests(unittest.TestCase):
    def test_load_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "# comment\nOPENAI_API_KEY=test-key\nexport LLM_MODEL='demo-model'\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                count = load_env_file(env_path)
                self.assertEqual(count, 2)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "test-key")
                self.assertEqual(os.environ["LLM_MODEL"], "demo-model")

    def test_load_env_does_not_override_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
            with patch.dict(os.environ, {"OPENAI_API_KEY": "from-shell"}, clear=False):
                load_env_file(env_path)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "from-shell")

    def test_load_project_env_finds_repo_dotenv(self) -> None:
        root = Path(__file__).resolve().parents[1]
        loaded = load_project_env(start=root / "experiments/real_benchmarks/run_gsm8k_llm.py")
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.name == ".env")
        self.assertTrue(os.environ.get("OPENAI_BASE_URL"))
    def test_recommend_profile_cpu_low_ram(self) -> None:
        rec = recommend_profile(["llama3.1:8b"], mem_gb=7.6, gpu={"available": False, "devices": []})
        self.assertEqual(rec["recommended_provider"], "ollama")
        self.assertEqual(rec["recommended_limit"], 5)
        self.assertTrue(any("CPU" in note for note in rec["notes"]))

    def test_trajectory_envelope_shape(self) -> None:
        task = {
            "task_id": "gsm8k_test_0000",
            "benchmark_id": "gsm8k_test",
            "task_family": "math_word_problem",
            "prompt": "1+1?",
            "gold_answer": "2",
            "budget": {"max_tokens": 64, "temperature": 0.0},
        }
        prompt = build_prompt(task["prompt"])
        traj = trajectory_for(task, "ollama", "test-model", prompt, "#### 2", {}, 100)
        self.assertEqual(traj["final_success_label"], "pass")
        self.assertEqual(traj["baseline_id"], "llm_direct_agent")

    @patch("experiments.real_benchmarks.check_llm_environment.requests.get")
    def test_ollama_unreachable(self, mock_get) -> None:
        from experiments.real_benchmarks.check_llm_environment import ollama_probe

        mock_get.side_effect = ConnectionError("connection refused")
        info = ollama_probe("http://localhost:11434")
        self.assertFalse(info["reachable"])


if __name__ == "__main__":
    unittest.main()
