"""Tests for T3 ACI comparison helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.terminal_bench.t3_aci_comparison import (
    aggregate,
    load_envelopes,
    resolve_shell_steps_path,
)


class T3AciComparisonTests(unittest.TestCase):
    def test_resolve_shell_steps_path_nested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "task" / "task.1-of-1.run" / "agent-logs"
            nested.mkdir(parents=True)
            steps = nested / "shell_steps.json"
            steps.write_text('[{"step": 0, "commands": ["ls"], "parse_status": "ok"}]', encoding="utf-8")
            self.assertEqual(resolve_shell_steps_path(root), steps)

    def test_load_envelopes_reads_nested_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "tb_smoke__single_react__1"
            logs = run_dir / "fix-permissions" / "fix-permissions.1-of-1.run" / "agent-logs"
            logs.mkdir(parents=True)
            (logs / "shell_steps.json").write_text(
                json.dumps(
                    [
                        {"step": 0, "commands": ["ls"], "parse_status": "ok"},
                        {"step": 1, "commands": [], "parse_status": "empty", "invalid_shell": "empty"},
                    ]
                ),
                encoding="utf-8",
            )
            envelope = {
                "baseline_id": "single_react_llm_agent",
                "task_id": "fix-permissions",
                "final_success_label": "pass",
                "metrics_summary": {
                    "failure_category": "none",
                    "end_task_success": True,
                    "raw_log_dir": str(run_dir),
                },
            }
            env_path = root / "tb_smoke__single_react__1__envelope.json"
            env_path.write_text(json.dumps(envelope), encoding="utf-8")

            rows = load_envelopes(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["total_steps"], 2)
            self.assertEqual(rows[0]["invalid_shell_steps"], 1)
            self.assertEqual(rows[0]["empty_parse_steps"], 1)

            agg = aggregate(rows)
            self.assertEqual(agg["invalid_shell_step_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
