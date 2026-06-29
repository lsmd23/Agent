#!/usr/bin/env python3
"""Phase 3 textual backprop: attribute failures, validate patches, decide lifecycle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baselines.common import load_jsonl  # noqa: E402
from experiments.phase3.attribution import (  # noqa: E402
    blame_from_trajectory,
    compile_update_record,
    load_trajectory,
)
from experiments.phase3.runtime_patches import patches_from_attribution  # noqa: E402
from experiments.phase3.validation import (  # noqa: E402
    build_textual_update_envelope,
    held_out_validation,
    pick_held_out_task,
    replay_validation,
)


def score_trajectory(path: Path) -> dict[str, Any]:
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


def load_failed_runs(
    trajectory_dir: Path,
    *,
    ablation_id: str = "aa_tuned_control",
) -> list[Path]:
    pattern = f"phase2_memory__{ablation_id}__*.json"
    paths = sorted(
        path
        for path in trajectory_dir.glob(pattern)
        if not path.name.endswith(".metrics.json")
    )
    failed: list[Path] = []
    for path in paths:
        metrics = score_trajectory(path)
        if not metrics["final"]["task_success"]:
            failed.append(path)
    return failed


def process_failure(
    trajectory_path: Path,
    tasks_by_id: dict[str, dict[str, Any]],
    all_tasks: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    envelope = load_trajectory(trajectory_path)
    task_id = envelope["task_id"]
    task = tasks_by_id[task_id]
    metrics = score_trajectory(trajectory_path)
    events = envelope.get("events", [])

    attribution = blame_from_trajectory(envelope, events, task, metrics)
    update_record = compile_update_record(attribution)
    patches = patches_from_attribution(attribution)

    replay_run = replay_validation(
        task,
        patches,
        validation_id=f"replay__{attribution['case_id']}",
    )
    held_out_task = pick_held_out_task(all_tasks, task)
    held_out_run = None
    if held_out_task is not None:
        held_out_run = held_out_validation(
            held_out_task,
            patches,
            validation_id=f"held_out__{attribution['case_id']}",
        )

    textual_envelope = build_textual_update_envelope(
        attribution,
        update_record,
        replay_run,
        held_out_run,
    )

    case_dir = output_dir / "attributions"
    envelope_dir = output_dir / "envelopes"
    replay_dir = output_dir / "replay_trajectories"
    case_dir.mkdir(parents=True, exist_ok=True)
    envelope_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)

    attribution_path = case_dir / f"{attribution['case_id']}.json"
    envelope_path = envelope_dir / f"{textual_envelope['envelope_id']}.json"
    attribution_path.write_text(json.dumps(attribution, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    envelope_path.write_text(json.dumps(textual_envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    replay_before = replay_dir / f"{replay_run['validation_id']}__before.json"
    replay_after = replay_dir / f"{replay_run['validation_id']}__after.json"
    replay_before.write_text(
        json.dumps(replay_run["before_envelope"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    replay_after.write_text(
        json.dumps(replay_run["after_envelope"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "source_trajectory": str(trajectory_path.relative_to(ROOT)),
        "task_id": task_id,
        "attribution_path": str(attribution_path.relative_to(ROOT)),
        "envelope_path": str(envelope_path.relative_to(ROOT)),
        "decision": textual_envelope["decision"],
        "decision_reason": textual_envelope["decision_reason"],
        "confidence": attribution["confidence"],
        "blamed_component": attribution["blamed_component"],
        "update_target": update_record["update_target"],
        "replay_primary_delta": replay_run["primary_delta"],
        "replay_improved": replay_run["replay_improved"],
        "held_out_task_id": held_out_task["task_id"] if held_out_task else None,
        "held_out_regression": held_out_run.get("held_out_regression") if held_out_run else None,
    }


def write_summary(results: list[dict[str, Any]], summary_path: Path) -> dict[str, Any]:
    decisions = {"accept": 0, "reject": 0, "quarantine": 0, "rollback": 0}
    for row in results:
        decisions[row["decision"]] = decisions.get(row["decision"], 0) + 1

    summary = {
        "scope": "Phase 3 textual backprop on aa_tuned_control failures from Phase 2.",
        "control_id": "aa_tuned_control",
        "failure_count": len(results),
        "decision_counts": decisions,
        "accept_rate": round(decisions["accept"] / len(results), 4) if results else 0.0,
        "quarantine_rate": round(decisions["quarantine"] / len(results), 4) if results else 0.0,
        "reject_rate": round(decisions["reject"] / len(results), 4) if results else 0.0,
        "replay_improvement_rate": round(
            sum(1 for row in results if row["replay_improved"]) / len(results),
            4,
        )
        if results
        else 0.0,
        "rows": results,
        "interpretation_hint": (
            "Decisions follow Subtask 05 acceptance gates: accept requires confidence>=0.70 "
            "and replay improvement plus held-out stability; quarantine for medium confidence "
            "or held-out regression."
        ),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 3 textual backprop pipeline.")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_tasks.jsonl")
    parser.add_argument(
        "--trajectory-dir",
        default="experiments/trajectories/phase2_memory_ablation",
    )
    parser.add_argument("--ablation-id", default="aa_tuned_control")
    parser.add_argument("--output-dir", default="experiments/phase3")
    parser.add_argument("--summary-output", default="experiments/metrics/phase3_backprop_summary.json")
    parser.add_argument("--trajectory-filter", default=None, help="Process one source trajectory file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_jsonl(ROOT / args.tasks)
    tasks_by_id = {task["task_id"]: task for task in tasks}
    trajectory_dir = ROOT / args.trajectory_dir
    output_dir = ROOT / args.output_dir

    if args.trajectory_filter:
        failed_paths = [ROOT / args.trajectory_filter]
    else:
        failed_paths = load_failed_runs(trajectory_dir, ablation_id=args.ablation_id)

    results = [process_failure(path, tasks_by_id, tasks, output_dir) for path in failed_paths]
    summary = write_summary(results, ROOT / args.summary_output)
    print(
        json.dumps(
            {
                "failures_processed": len(results),
                "decision_counts": summary["decision_counts"],
                "summary": args.summary_output,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
