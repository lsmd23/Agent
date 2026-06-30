"""Tests for TB shell loop."""

from __future__ import annotations

import unittest

from experiments.terminal_bench.tb_shell_loop import build_step_prompt, parse_step_response


class TBShellLoopTests(unittest.TestCase):
    def test_parse_json_step_response(self) -> None:
        text = '{"commands": ["ls -la", "chmod +x foo.sh"], "is_task_complete": false}'
        parsed = parse_step_response(text)
        self.assertEqual(parsed.commands, ["ls -la", "chmod +x foo.sh"])
        self.assertFalse(parsed.is_task_complete)

    def test_parse_bash_codeblock(self) -> None:
        text = "```bash\npwd\nls\n```"
        parsed = parse_step_response(text)
        self.assertEqual(parsed.commands, ["pwd", "ls"])

    def test_rejects_prose_commands(self) -> None:
        text = '{"commands": ["If the script lacks permission, fix it"], "is_task_complete": false}'
        parsed = parse_step_response(text)
        self.assertEqual(parsed.commands, [])

    def test_build_step_prompt_includes_instruction(self) -> None:
        prompt = build_step_prompt(
            baseline_id="single_react_llm_agent",
            instruction="Fix process_data.sh",
            terminal_state="root@host:/app#",
            step=0,
            max_steps=8,
            history=[],
        )
        self.assertIn("Fix process_data.sh", prompt)
        self.assertIn("single-controller ReAct", prompt)


if __name__ == "__main__":
    unittest.main()
