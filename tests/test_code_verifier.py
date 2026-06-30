"""Tests for executable pytest code verifier."""

from __future__ import annotations

import unittest

from experiments.baselines.faithful_runners import build_faithful_runtime
from experiments.real_benchmarks.code_verifier import (
    broken_repo_fails,
    build_fixture_context,
    golden_repo_passes,
    list_fixture_dirs,
    load_manifest,
    select_code_patch,
    verify_code_task,
)
from experiments.real_benchmarks.task_oracles import evaluate_task_success


FIXTURES = [
    load_manifest(path).get("fixture_id", path.name)
    for path in list_fixture_dirs()
]


class CodeVerifierTests(unittest.TestCase):
    def test_broken_repo_fails_for_all_fixtures(self) -> None:
        for fixture_id in FIXTURES:
            with self.subTest(fixture_id=fixture_id):
                self.assertTrue(broken_repo_fails(fixture_id))

    def test_golden_marker_passes_for_all_fixtures(self) -> None:
        for fixture_id in FIXTURES:
            with self.subTest(fixture_id=fixture_id):
                self.assertTrue(golden_repo_passes(fixture_id))

    def test_add_fn_wrong_patch_fails(self) -> None:
        result = verify_code_task("phase0_seed_code_fix_001", "keep return a - b unchanged")
        self.assertFalse(result.passed)

    def test_add_fn_code_block_passes(self) -> None:
        output = "```python\ndef add(a, b):\n    return a + b\n```"
        result = verify_code_task("phase0_seed_code_fix_001", output)
        self.assertTrue(result.passed)
        self.assertIn(result.apply_mode, {"single_code_block", "golden_code_block", "marker_match"})

    def test_task_oracle_uses_pytest_for_code_task(self) -> None:
        task = {
            "task_id": "phase1_code_edge_001",
            "task_family": "code_agent_task",
            "expected_route": {"required_modules": ["code_agent"], "discouraged_modules": []},
            "negative_transfer_probe": {"enabled": False},
        }

        class FakeState:
            final_answer = "```python\ndef safe_divide(numerator, denominator):\n    if denominator == 0:\n        return 0.0\n    return numerator / denominator\n```"
            observations: list[str] = []
            selected_modules = ["code_agent", "verifier"]
            verifier_status = "pass"
            failure_signals: list[str] = []
            memory_reads: list[str] = []

        label, metrics = evaluate_task_success(task, FakeState())
        self.assertEqual(label, "pass")
        self.assertEqual(metrics["oracle_type"], "executable_pytest")
        self.assertTrue(metrics["end_task_success"])

    def test_build_fixture_context_includes_repo_and_failure(self) -> None:
        context = build_fixture_context("phase0_seed_code_fix_001")
        self.assertIsNotNone(context)
        assert context is not None
        self.assertIn("add_fn_001", context)
        self.assertIn("lib/calc.py", context)
        self.assertIn("unittest", context.lower())

    def test_select_code_patch_strips_file_hint_on_apply(self) -> None:
        patch = select_code_patch(
            "```python\n# file: lib/calc.py\ndef add(a, b):\n    return a + b\n```",
            ["lib/calc.py"],
        )
        self.assertIsNotNone(patch)
        result = verify_code_task("phase0_seed_code_fix_001", patch or "")
        self.assertTrue(result.passed)
        self.assertIn(result.apply_mode, {"hinted_code_block", "single_code_block", "golden_code_block", "marker_match"})

    def test_toy_runtime_envelope_can_score_code_end_task(self) -> None:
        task = {
            "task_id": "phase1_code_import_001",
            "benchmark_id": "phase1_mixed",
            "task_family": "code_agent_task",
            "prompt": "Repair import path",
            "budget": {"max_steps": 4, "max_activation_cost": 3.0},
            "expected_route": {
                "required_modules": ["code_agent"],
                "discouraged_modules": ["search_agent"],
            },
            "memory_setup": {"injected_memory_ids": [], "quarantined_memory_ids": []},
            "negative_transfer_probe": {"enabled": False},
        }
        runtime = build_faithful_runtime("single_react_agent", task, max_steps=2)
        state = runtime.run(task["prompt"], max_budget=3.0)
        state.final_answer = "```python\n# file: mypkg/core.py\ndef foo():\n    return 1\n```"
        label, metrics = evaluate_task_success(task, state)
        self.assertEqual(metrics["oracle_type"], "executable_pytest")
        self.assertTrue(metrics["end_task_success"])


if __name__ == "__main__":
    unittest.main()
