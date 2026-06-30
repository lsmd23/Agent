#!/usr/bin/env python3
"""Real-task textual backprop diagnostic (Brief G / T7 partial).

Collect failed code-suite tasks from code_full_matrix_summary.json, attribute
failures from stored real-LLM trajectories, propose bounded local updates,
validate via simulation replay (zero new LLM calls), and guard held-out regressions.
"""

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

DEFAULT_BASELINE = "agent_attention_llm_tuned"
DEFAULT_ABLATION = "aa_tuned_control"
TRAJECTORY_ROOT = Path("experiments/llm_runs/code_full_matrix/code_all")


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


def load_matrix_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def failed_matrix_rows(
    summary: dict[str, Any],
    *,
    baseline_id: str = DEFAULT_BASELINE,
) -> list[dict[str, Any]]:
    return [
        row
        for row in summary.get("per_task", [])
        if row.get("baseline_id") == baseline_id and not row.get("success")
    ]


def matrix_success_by_task(
    summary: dict[str, Any],
    *,
    baseline_id: str = DEFAULT_BASELINE,
) -> dict[str, bool]:
    return {
        row["task_id"]: bool(row.get("success"))
        for row in summary.get("per_task", [])
        if row.get("baseline_id") == baseline_id
    }


def resolve_trajectory_path(
    row: dict[str, Any],
    trajectory_root: Path,
    *,
    baseline_id: str = DEFAULT_BASELINE,
) -> Path:
    run_id = row.get("run_id")
    if run_id:
        candidate = trajectory_root / baseline_id / f"{run_id}.json"
        if candidate.exists():
            return candidate
    task_id = row["task_id"]
    baseline_dir = trajectory_root / baseline_id
    matches = sorted(baseline_dir.glob(f"*{task_id}.json"))
    if not matches:
        raise FileNotFoundError(
            f"No trajectory for baseline={baseline_id} task={task_id} under {baseline_dir}"
        )
    return matches[0]


def pick_held_out_success_task(
    tasks: list[dict[str, Any]],
    failed_task: dict[str, Any],
    success_by_task: dict[str, bool],
) -> dict[str, Any] | None:
    """Prefer same-family tasks that passed on real LLM for regression guard."""
    family = failed_task.get("task_family")
    candidates = [
        task
        for task in tasks
        if task["task_id"] != failed_task["task_id"]
        and task.get("task_family") == family
        and success_by_task.get(task["task_id"], False)
    ]
    if not candidates:
        candidates = [
            task
            for task in tasks
            if task["task_id"] != failed_task["task_id"]
            and success_by_task.get(task["task_id"], False)
        ]
    if candidates:
        return candidates[0]
    return pick_held_out_task(tasks, failed_task)


def process_failure(
    matrix_row: dict[str, Any],
    trajectory_path: Path,
    tasks_by_id: dict[str, dict[str, Any]],
    all_tasks: list[dict[str, Any]],
    success_by_task: dict[str, bool],
    output_dir: Path,
    *,
    ablation_id: str = DEFAULT_ABLATION,
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
        validation_id=f"real_task_replay__{attribution['case_id']}",
        ablation_id=ablation_id,
    )
    held_out_task = pick_held_out_success_task(all_tasks, task, success_by_task)
    held_out_run = None
    if held_out_task is not None:
        held_out_run = held_out_validation(
            held_out_task,
            patches,
            validation_id=f"real_task_held_out__{attribution['case_id']}",
            ablation_id=ablation_id,
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
    attribution_path.write_text(
        json.dumps(attribution, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    envelope_path.write_text(
        json.dumps(textual_envelope, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

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
        "matrix_row": {
            "task_id": task_id,
            "baseline_id": matrix_row.get("baseline_id"),
            "final_success_label": matrix_row.get("final_success_label"),
            "model_calls": matrix_row.get("model_calls"),
            "oracle_type": matrix_row.get("oracle_type"),
        },
        "real_failure_reason": metrics["final"].get("failure_reason"),
        "task_id": task_id,
        "attribution_path": str(attribution_path.relative_to(ROOT)),
        "envelope_path": str(envelope_path.relative_to(ROOT)),
        "decision": textual_envelope["decision"],
        "decision_reason": textual_envelope["decision_reason"],
        "confidence": attribution["confidence"],
        "blamed_component": attribution["blamed_component"],
        "update_target": update_record["update_target"],
        "local_gradient": attribution["local_gradient"],
        "replay_primary_delta": replay_run["primary_delta"],
        "replay_improved": replay_run["replay_improved"],
        "held_out_task_id": held_out_task["task_id"] if held_out_task else None,
        "held_out_regression": held_out_run.get("held_out_regression") if held_out_run else None,
        "evidence_tier": "real_llm_trajectory_simulation_replay",
    }


def write_summary(
    results: list[dict[str, Any]],
    summary_path: Path,
    *,
    baseline_id: str,
    matrix_path: str,
    task_count: int,
) -> dict[str, Any]:
    decisions = {"accept": 0, "reject": 0, "quarantine": 0, "rollback": 0}
    for row in results:
        decisions[row["decision"]] = decisions.get(row["decision"], 0) + 1

    n = len(results)
    summary = {
        "scope": "T7 partial: real-task textual backprop on code_full_matrix failures (Brief G).",
        "brief": "G",
        "t7_deliverable": "real_task_backprop_summary.json",
        "baseline_id": baseline_id,
        "source_matrix": matrix_path,
        "suite_task_count": task_count,
        "failure_count": n,
        "llm_calls_during_diagnostic": 0,
        "replay_mode": "simulation_harness_aa_tuned_control",
        "decision_counts": decisions,
        "accept_rate": round(decisions["accept"] / n, 4) if n else 0.0,
        "quarantine_rate": round(decisions["quarantine"] / n, 4) if n else 0.0,
        "reject_rate": round(decisions["reject"] / n, 4) if n else 0.0,
        "replay_improvement_rate": round(
            sum(1 for row in results if row["replay_improved"]) / n,
            4,
        )
        if n
        else 0.0,
        "held_out_regression_count": sum(1 for row in results if row.get("held_out_regression")),
        "rows": results,
        "interpretation_hint": (
            "Attribution from real LLM trajectories; replay/held-out via Phase 3 simulation "
            "(zero new LLM). Accept requires confidence>=0.70, replay improvement, and no "
            "held-out regression on matrix-passing tasks."
        ),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def classify_outcome(summary: dict[str, Any]) -> str:
    if summary["failure_count"] == 0:
        return "weak_or_inconclusive"
    if summary["decision_counts"].get("accept", 0) > 0:
        return "supports_direction"
    if summary["replay_improvement_rate"] >= 0.5 and summary["held_out_regression_count"] == 0:
        return "weak_or_inconclusive"
    return "falsified_or_blocked"


def write_audit_md(summary: dict[str, Any], audit_path: Path) -> None:
    outcome = classify_outcome(summary)
    decisions = summary["decision_counts"]
    lines = [
        "# Real-Task Textual Backprop Audit (Brief G / T7 Partial)",
        "",
        "## Scope",
        "",
        "Executable textual-backprop diagnostic on real LLM code-suite failures.",
        "",
        "## Inputs Read",
        "",
        f"- `{summary['source_matrix']}`",
        f"- `{TRAJECTORY_ROOT}/{summary['baseline_id']}/` (stored trajectories)",
        "- `experiments/tasks/phase1_code_all.jsonl`",
        "- `experiments/phase3/` (attribution, patches, validation)",
        "- `docs/deliverables/05/textual_gradient_policy.md`",
        "",
        "## Method",
        "",
        "1. Select failed rows for `agent_attention_llm_tuned` from code matrix summary.",
        "2. Load matching real-LLM trajectory envelopes (no new model calls).",
        "3. Attribute failure component and compile bounded `RuntimePatch` proposals.",
        "4. Replay before/after on source task via `aa_tuned_control` simulation harness.",
        "5. Held-out regression guard on same-family tasks that passed on real LLM.",
        "6. Apply Subtask 05 lifecycle gates (accept / quarantine / reject).",
        "",
        "## Commands Run",
        "",
        "```bash",
        "python3 experiments/analysis/real_task_backprop_diagnostic.py",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/metrics/real_task_backprop_summary.json`",
        "- `experiments/analysis/real_task_backprop_audit.md`",
        "- `experiments/phase3/real_task/attributions/`",
        "- `experiments/phase3/real_task/envelopes/`",
        "- `experiments/phase3/real_task/replay_trajectories/`",
        "",
        "## Results",
        "",
        "### Decision counts",
        "",
        "| Decision | Count |",
        "|----------|-------|",
        f"| Accept | {decisions.get('accept', 0)} |",
        f"| Quarantine | {decisions.get('quarantine', 0)} |",
        f"| Reject | {decisions.get('reject', 0)} |",
        "",
        "### Aggregate",
        "",
        f"- Failures processed: **{summary['failure_count']}** / {summary['suite_task_count']} suite tasks",
        f"- Replay improvement rate: **{summary['replay_improvement_rate']:.0%}**",
        f"- Held-out regressions: **{summary['held_out_regression_count']}**",
        f"- New LLM calls: **{summary['llm_calls_during_diagnostic']}**",
        "",
        "### Per-failure",
        "",
        "| Task | Real failure | Blamed | Update | Replay Δ | Held-out | Decision |",
        "|------|--------------|--------|--------|----------|----------|----------|",
    ]
    for row in summary["rows"]:
        held_out = row.get("held_out_task_id") or "—"
        reg = row.get("held_out_regression")
        reg_str = "—" if reg is None else ("yes" if reg else "no")
        lines.append(
            f"| `{row['task_id']}` | {row.get('real_failure_reason', '—')} "
            f"| {row['blamed_component']} | {row['update_target']} "
            f"| {row['replay_primary_delta']:+.1f} | `{held_out}` ({reg_str}) "
            f"| **{row['decision']}** |"
        )

    lines.extend(
        [
            "",
            f"**Evidence outcome:** `{outcome}`",
            "",
            "## Interpretation",
            "",
            summary["interpretation_hint"],
            "",
            "- Real LLM failures may reflect patch quality or step budget, not only routing.",
            "- Simulation replay tests whether bounded router/memory/halt patches would fix the",
            "  toy-runtime analogue; it does not re-run the LLM on the failed task.",
            "- Zero accepted updates means no auto-apply; quarantined patches need live validation.",
            "",
            "## Next Questions",
            "",
        ]
    )
    if outcome == "supports_direction":
        lines.append("- Live A/B: apply accepted patches on held-out real LLM failures.")
    elif outcome == "weak_or_inconclusive":
        lines.extend(
            [
                "- Raise attribution confidence with richer real-trajectory signals (verifier catch, patch diff).",
                "- Brief G+: replay with cached LLM module outputs instead of simulation-only.",
                "- Compare backprop fixes vs cascade direct-first on overlapping failure set.",
            ]
        )
    else:
        lines.extend(
            [
                "- Inspect failures where replay did not improve (likely execution/patch, not router).",
                "- Add halt/budget patches tuned to max_steps_reached real failures.",
            ]
        )
    lines.append("")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-task textual backprop diagnostic.")
    parser.add_argument(
        "--matrix",
        default="experiments/metrics/code_full_matrix_summary.json",
    )
    parser.add_argument(
        "--tasks",
        default="experiments/tasks/phase1_code_all.jsonl",
    )
    parser.add_argument(
        "--baseline-id",
        default=DEFAULT_BASELINE,
        help="Baseline whose failures to diagnose.",
    )
    parser.add_argument(
        "--trajectory-root",
        default=str(TRAJECTORY_ROOT),
    )
    parser.add_argument(
        "--ablation-id",
        default=DEFAULT_ABLATION,
        help="Simulation harness for replay/held-out (zero LLM).",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/phase3/real_task",
    )
    parser.add_argument(
        "--summary-output",
        default="experiments/metrics/real_task_backprop_summary.json",
    )
    parser.add_argument(
        "--audit-output",
        default="experiments/analysis/real_task_backprop_audit.md",
    )
    parser.add_argument(
        "--task-filter",
        default=None,
        help="Process one task_id only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    matrix_path = ROOT / args.matrix
    summary_data = load_matrix_summary(matrix_path)
    tasks = load_jsonl(ROOT / args.tasks)
    tasks_by_id = {task["task_id"]: task for task in tasks}
    success_by_task = matrix_success_by_task(summary_data, baseline_id=args.baseline_id)

    failed_rows = failed_matrix_rows(summary_data, baseline_id=args.baseline_id)
    if args.task_filter:
        failed_rows = [row for row in failed_rows if row["task_id"] == args.task_filter]

    trajectory_root = ROOT / args.trajectory_root
    output_dir = ROOT / args.output_dir

    results: list[dict[str, Any]] = []
    for row in failed_rows:
        traj_path = resolve_trajectory_path(row, trajectory_root, baseline_id=args.baseline_id)
        results.append(
            process_failure(
                row,
                traj_path,
                tasks_by_id,
                tasks,
                success_by_task,
                output_dir,
                ablation_id=args.ablation_id,
            )
        )

    summary_path = ROOT / args.summary_output
    summary = write_summary(
        results,
        summary_path,
        baseline_id=args.baseline_id,
        matrix_path=args.matrix,
        task_count=len(tasks),
    )
    write_audit_md(summary, ROOT / args.audit_output)

    print(
        json.dumps(
            {
                "failures_processed": len(results),
                "decision_counts": summary["decision_counts"],
                "replay_improvement_rate": summary["replay_improvement_rate"],
                "held_out_regression_count": summary["held_out_regression_count"],
                "summary": args.summary_output,
                "audit": args.audit_output,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
