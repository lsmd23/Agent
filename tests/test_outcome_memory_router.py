"""Tests for outcome-memory router (Brief D)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.analysis.outcome_memory_router import (
    OutcomeMemoryEntry,
    OutcomeMemoryKey,
    OutcomeMemoryStore,
    RouteOutcomeStats,
    analyze,
    assert_no_leakage,
    error_signature_for_task,
    replay_leave_one_out,
    select_escalation_order,
    select_static_route,
    simulate_cascade,
)
from experiments.baselines.common import load_jsonl


class OutcomeMemoryRouterTests(unittest.TestCase):
    def test_leakage_guard_blocks_patch_body(self) -> None:
        with self.assertRaises(ValueError):
            assert_no_leakage({"patch_body": "def fix(): pass"})

    def test_leakage_guard_blocks_task_id_key(self) -> None:
        with self.assertRaises(ValueError):
            assert_no_leakage({"task_id": "phase1_code_csv_001"})

    def test_store_only_aggregates_stats(self) -> None:
        store = OutcomeMemoryStore()
        key = OutcomeMemoryKey(task_family="code_agent_task", error_signature="tag:parsing")
        row = {
            "success": True,
            "model_calls": 2,
            "total_tokens": 500,
            "latency_ms": 1000,
        }
        store.write_outcome(key, "moa_style_llm_agent", row, source_task_id="phase1_code_csv_001")
        entry = store.retrieve(key)
        assert entry is not None
        stats = entry.route_stats["moa_style_llm_agent"]
        self.assertEqual(stats.attempts, 1)
        self.assertEqual(stats.successes, 1)
        serialized = json.dumps(entry.to_dict())
        self.assertNotIn("def ", serialized)
        self.assertNotIn("phase1_code_csv_001", serialized)

    def test_error_signature_prefers_pytest_pattern(self) -> None:
        task = {"task_family": "code_agent_task", "tags": ["code", "parsing", "phase1"]}
        trajectory = {
            "metrics_summary": {
                "pytest_stderr": (
                    "FAIL: test_quoted_comma (test_parse_csv_row.TestCsv)\n"
                    "AssertionError: Lists differ\n"
                )
            }
        }
        sig = error_signature_for_task("phase1_code_csv_001", task, {"phase1_code_csv_001": trajectory})
        self.assertEqual(sig, "AssertionError|test_quoted_comma")

    def test_error_signature_falls_back_to_tag(self) -> None:
        task = {"task_family": "code_agent_task", "tags": ["code", "config", "phase1"]}
        sig = error_signature_for_task("phase1_code_config_001", task, {})
        self.assertEqual(sig, "tag:config")

    def test_select_static_route_defaults_without_memory(self) -> None:
        route, reason = select_static_route(None)
        self.assertEqual(route, "single_react_llm_agent")
        self.assertEqual(reason, "default_no_memory")

    def test_select_static_route_requires_min_attempts(self) -> None:
        key = OutcomeMemoryKey(task_family="code_agent_task", error_signature="tag:edge_case")
        entry = OutcomeMemoryStore().entries.setdefault(key.storage_key(), OutcomeMemoryEntry(key=key))
        stats = RouteOutcomeStats()
        stats.observe({"success": True, "model_calls": 1, "total_tokens": 100, "latency_ms": 500})
        entry.route_stats["moa_style_llm_agent"] = stats
        route, reason = select_static_route(entry, min_attempts=2)
        self.assertEqual(route, "single_react_llm_agent")
        self.assertEqual(reason, "default_insufficient_memory")

    def test_select_escalation_order_prefers_successful_route(self) -> None:
        key = OutcomeMemoryKey(task_family="code_agent_task", error_signature="tag:parsing")
        entry = OutcomeMemoryEntry(key=key)
        aa_stats = RouteOutcomeStats()
        aa_stats.observe({"success": True, "model_calls": 2, "total_tokens": 400, "latency_ms": 800})
        moa_stats = RouteOutcomeStats()
        moa_stats.observe({"success": False, "model_calls": 2, "total_tokens": 400, "latency_ms": 800})
        entry.route_stats["agent_attention_llm_tuned"] = aa_stats
        entry.route_stats["moa_style_llm_agent"] = moa_stats
        order, reason = select_escalation_order(entry)
        self.assertEqual(order[0], "agent_attention_llm_tuned")
        self.assertEqual(reason, "memory_escalation")

    def test_simulate_cascade_stops_on_success(self) -> None:
        by_task = {
            "t1": {
                "single_react_llm_agent": {
                    "baseline_id": "single_react_llm_agent",
                    "success": False,
                    "model_calls": 1,
                    "total_tokens": 100,
                    "latency_ms": 100,
                },
                "agent_attention_llm_tuned": {
                    "baseline_id": "agent_attention_llm_tuned",
                    "success": True,
                    "model_calls": 2,
                    "total_tokens": 200,
                    "latency_ms": 200,
                },
                "moa_style_llm_agent": {
                    "baseline_id": "moa_style_llm_agent",
                    "success": True,
                    "model_calls": 2,
                    "total_tokens": 300,
                    "latency_ms": 300,
                },
            }
        }
        result = simulate_cascade("t1", ["agent_attention_llm_tuned", "moa_style_llm_agent"], by_task)
        self.assertTrue(result["success"])
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual(result["stages_run"], 2)

    def test_replay_leave_one_out_runs(self) -> None:
        summary = json.loads(Path("experiments/metrics/code_full_matrix_summary.json").read_text(encoding="utf-8"))
        oracle = json.loads(Path("experiments/metrics/oracle_route_matrix.json").read_text(encoding="utf-8"))
        tasks_by_id = {row["task_id"]: row for row in load_jsonl(Path("experiments/tasks/phase1_code_all.jsonl"))}
        by_task: dict[str, dict[str, dict]] = {}
        for row in summary["per_task"]:
            by_task.setdefault(row["task_id"], {})[row["baseline_id"]] = row
        task_ids = sorted(by_task)
        oracle_by_task = {row["task_id"]: row["oracle_route_reward"] for row in oracle["per_task"]}
        replay = replay_leave_one_out(
            by_task=by_task,
            task_ids=task_ids,
            tasks_by_id=tasks_by_id,
            trajectory_lookup={},
            oracle_by_task=oracle_by_task,
            mode="cascade",
        )
        self.assertEqual(replay["tasks"], 26)
        self.assertGreaterEqual(replay["mean_regret_vs_oracle_reward"], 0.0)

    def test_analyze_produces_evidence_outcome(self) -> None:
        summary = json.loads(Path("experiments/metrics/code_full_matrix_summary.json").read_text(encoding="utf-8"))
        oracle = json.loads(Path("experiments/metrics/oracle_route_matrix.json").read_text(encoding="utf-8"))
        tasks_by_id = {row["task_id"]: row for row in load_jsonl(Path("experiments/tasks/phase1_code_all.jsonl"))}
        result = analyze(
            summary,
            tasks_by_id=tasks_by_id,
            trajectory_lookup={},
            oracle_matrix=oracle,
        )
        self.assertIn(
            result["aggregate"]["evidence_outcome"],
            {"supports_direction", "weak_or_inconclusive", "falsified_or_blocked"},
        )
        self.assertTrue(result["aggregate"]["leakage_audit"]["passed"])


if __name__ == "__main__":
    unittest.main()
