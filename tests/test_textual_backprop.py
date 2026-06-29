"""Tests for Phase 3 textual backprop."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataclasses import asdict

from experiments.baselines.common import load_jsonl  # noqa: E402
from experiments.baselines.memory_ablations import build_memory_ablation_runtime  # noqa: E402
from experiments.phase3.attribution import blame_from_trajectory, compile_update_record  # noqa: E402
from experiments.phase3.runtime_patches import PatchedTunedRuntime, RuntimePatch, patches_from_attribution  # noqa: E402
from experiments.phase3.validation import (  # noqa: E402
    decide_envelope,
    held_out_validation,
    replay_validation,
)


def score_trajectory(path: Path) -> dict:
    metrics_path = path.with_suffix(".metrics.json")
    cmd = [
        sys.executable,
        str(ROOT / "docs/deliverables/07/scoring_script.py"),
        str(path),
        "--output",
        str(metrics_path),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    return payload["runs"][0]


class TextualBackpropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tasks = load_jsonl(ROOT / "experiments/tasks/phase1_tasks.jsonl")
        cls.tasks_by_id = {task["task_id"]: task for task in cls.tasks}
        cls.negative_task = cls.tasks_by_id["phase0_seed_negative_memory_001"]

    def test_attribution_has_required_fields(self) -> None:
        task = self.negative_task
        runtime = build_memory_ablation_runtime("aa_unfiltered_memory", task, int(task["budget"]["max_steps"]))
        state = runtime.run(task["prompt"], max_budget=float(task["budget"]["max_activation_cost"]))
        envelope = {
            "task_id": task["task_id"],
            "run_id": "test_run",
            "events": [asdict(event) for event in runtime.events],
        }
        metrics = {
            "final": {"task_success": False, "failure_reason": "route_or_oracle_mismatch"},
            "process": {"budget_exhaustion": False, "loop_stuck": False},
            "memory": {"harmful_memory_reads": 1},
        }
        attribution = blame_from_trajectory(envelope, envelope["events"], task, metrics)
        self.assertIn("case_id", attribution)
        self.assertGreaterEqual(len(attribution["evidence_event_ids"]), 1)
        self.assertIn("proposed_update", attribution)
        self.assertEqual(attribution["blamed_component"], "memory")

    def test_update_record_roundtrip(self) -> None:
        task = self.tasks_by_id["phase1_code_config_001"]
        runtime = build_memory_ablation_runtime("aa_tuned_control", task, int(task["budget"]["max_steps"]))
        state = runtime.run(task["prompt"], max_budget=float(task["budget"]["max_activation_cost"]))
        envelope = {
            "task_id": task["task_id"],
            "run_id": "test_run",
            "events": [asdict(event) for event in runtime.events],
        }
        metrics = {
            "final": {"task_success": False},
            "process": {"budget_exhaustion": True, "loop_stuck": False},
            "memory": {"harmful_memory_reads": 0},
        }
        attribution = blame_from_trajectory(envelope, envelope["events"], task, metrics)
        update = compile_update_record(attribution)
        self.assertFalse(update["applied"])
        self.assertGreaterEqual(len(update["evidence_refs"]), 1)
        self.assertIn(update["update_target"], {"router_rule", "halt_threshold", "memory_write_policy"})

    def test_router_discourage_patch_improves_replay(self) -> None:
        task = self.negative_task
        patches = [
            RuntimePatch(
                patch_id="test_discourage_search",
                update_target="router_rule",
                target_id=task["task_family"],
                parameters={"discouraged_modules": ["search_agent"]},
            )
        ]
        replay = replay_validation(task, patches, validation_id="test_replay")
        self.assertGreaterEqual(replay["after_metrics"]["task_success"], replay["before_metrics"]["task_success"])

    def test_quarantine_patch_blocks_harmful_memory_reads(self) -> None:
        task = self.negative_task
        patches = [
            RuntimePatch(
                patch_id="test_quarantine",
                update_target="memory_write_policy",
                target_id="global_quarantine",
                parameters={"quarantine_aware": True},
            )
        ]
        runtime = PatchedTunedRuntime(
            modules=list(build_memory_ablation_runtime("aa_unfiltered_memory", task, 8).modules.values()),
            memory=__import__(
                "experiments.baselines.common",
                fromlist=["memory_for_task"],
            ).memory_for_task(task, quarantine_at_load=False),
            max_steps=8,
            memory_enabled=True,
            quarantine_aware=False,
            patches=patches,
            task_family=task["task_family"],
        )
        state = runtime.run(task["prompt"], max_budget=float(task["budget"]["max_activation_cost"]))
        harmful_reads = [
            read
            for read in runtime.current_memory_reads
            if getattr(read, "usefulness_label", None) == "harmful"
        ]
        self.assertEqual(len(harmful_reads), 0)

    def test_decision_gates(self) -> None:
        attribution = {"confidence": 0.75}
        replay = {"replay_improved": True}
        held_out = {"held_out_regression": False}
        decision, reason, audit = decide_envelope(attribution, replay, held_out)
        self.assertEqual(decision, "accept")
        self.assertEqual(audit, "complete")
        self.assertIn(reason, {"replay_and_held_out_pass"})

        low_conf = {"confidence": 0.40}
        decision, reason, _ = decide_envelope(low_conf, replay, held_out)
        self.assertEqual(decision, "reject")

        replay_fail = {"replay_improved": False}
        decision, reason, _ = decide_envelope(attribution, replay_fail, held_out)
        self.assertEqual(decision, "reject")

    def test_patches_from_attribution(self) -> None:
        attribution = {
            "case_id": "case__x",
            "proposed_update": {
                "target": "memory_write_policy",
                "target_id": "global",
                "patch_parameters": {"quarantine_aware": True},
            },
        }
        patches = patches_from_attribution(attribution)
        self.assertEqual(len(patches), 1)
        self.assertTrue(patches[0].parameters["quarantine_aware"])


if __name__ == "__main__":
    unittest.main()
