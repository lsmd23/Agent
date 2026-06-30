"""Tests for Terminal-Bench adapter."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from experiments.terminal_bench.adapter import (
    build_faithful_agent_import_path,
    build_tb_run_command,
    docker_available,
    envelope_from_tb_run,
    extract_shell_commands,
    list_task_ids,
    run_adapter_smoke,
    TBRunSpec,
)


class TerminalBenchAdapterTests(unittest.TestCase):
    def test_build_faithful_agent_import_path(self) -> None:
        self.assertIn("FaithfulTBAgent", build_faithful_agent_import_path())

    def test_build_tb_run_command_includes_baseline(self) -> None:
        spec = TBRunSpec(
            baseline_id="agent_attention_llm_tuned",
            task_id="hello-world",
            n_tasks=1,
            dataset_path=Path("external/terminal-bench-core"),
            output_path=Path("experiments/llm_runs/terminal_bench/smoke"),
            run_id="test_run",
            model="openai/gpt-4o-mini",
            provider="openai",
        )
        cmd = build_tb_run_command(spec)
        joined = " ".join(cmd)
        self.assertIn("--agent-import-path", joined)
        self.assertIn("baseline_id=agent_attention_llm_tuned", joined)
        self.assertIn("--task-id hello-world", joined)

    def test_extract_shell_commands_from_codeblock(self) -> None:
        text = "```bash\necho hello\nls -la\n```"
        self.assertEqual(extract_shell_commands(text), ["echo hello", "ls -la"])

    def test_envelope_from_tb_run_marks_failure(self) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="error")
        envelope = envelope_from_tb_run(
            baseline_id="single_react_llm_agent",
            task_id="demo",
            run_dir=Path("/tmp/demo_run"),
            provider="openai",
            model="demo-model",
            proc=proc,
        )
        self.assertEqual(envelope["benchmark_id"], "terminal_bench")
        self.assertEqual(envelope["final_success_label"], "fail")
        self.assertEqual(envelope["metrics_summary"]["failure_type"], "tb_process_error")

    @patch("experiments.terminal_bench.adapter.run_local_code_fallback")
    @patch("experiments.terminal_bench.adapter.run_tb_smoke")
    def test_run_adapter_smoke_falls_back_when_blocked(self, mock_tb, mock_local) -> None:
        mock_tb.return_value = {"mode": "blocked", "blocker": "dataset_missing"}
        mock_local.return_value = {"mode": "local_code_fallback", "tasks": 1}
        result = run_adapter_smoke(prefer_tb=True, fallback_limit=1)
        self.assertEqual(result["mode"], "blocked")
        self.assertIn("fallback", result)
        mock_local.assert_called_once()

    def test_list_task_ids_on_missing_dataset(self) -> None:
        self.assertEqual(list_task_ids(Path("/nonexistent/dataset"), limit=3), [])

    def test_docker_available_with_mock(self) -> None:
        with patch("experiments.terminal_bench.adapter.shutil.which", return_value="/usr/bin/docker"):
            with patch("experiments.terminal_bench.adapter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                self.assertTrue(docker_available())


class FaithfulTBAgentTests(unittest.TestCase):
    def test_supported_baselines(self) -> None:
        try:
            from experiments.terminal_bench.faithful_tb_agent import FaithfulTBAgent
        except ImportError:
            self.skipTest("terminal-bench not installed")
        agent = FaithfulTBAgent(baseline_id="retrieval_memory_llm_agent", max_shell_steps=6)
        self.assertEqual(agent.baseline_id, "retrieval_memory_llm_agent")
        self.assertEqual(agent.max_shell_steps, 6)

    def test_unsupported_baseline_raises(self) -> None:
        try:
            from experiments.terminal_bench.faithful_tb_agent import FaithfulTBAgent
        except ImportError:
            self.skipTest("terminal-bench not installed")
        with self.assertRaises(ValueError):
            FaithfulTBAgent(baseline_id="unknown_baseline")


if __name__ == "__main__":
    unittest.main()
