#!/usr/bin/env python3
"""Compare T3 pilot before/after ACI patches from envelope directories."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def resolve_shell_steps_path(run_dir: Path) -> Path | None:
    """Locate shell_steps.json under a TB smoke run directory."""
    direct = run_dir / "shell_steps.json"
    if direct.exists():
        return direct
    agent_logs = sorted(run_dir.glob("**/agent-logs/shell_steps.json"))
    if agent_logs:
        return agent_logs[0]
    nested = sorted(run_dir.glob("**/shell_steps.json"))
    return nested[0] if nested else None


def load_envelopes(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*__envelope.json")):
        env = json.loads(path.read_text(encoding="utf-8"))
        metrics = env.get("metrics_summary", {})
        run_dir = Path(metrics.get("raw_log_dir") or path.with_name(path.name.replace("__envelope.json", "")))
        steps_path = resolve_shell_steps_path(run_dir)
        invalid_shell = 0
        empty_parse = 0
        total_steps = 0
        if steps_path and steps_path.exists():
            steps = json.loads(steps_path.read_text(encoding="utf-8"))
            total_steps = len(steps)
            for step in steps:
                if step.get("invalid_shell"):
                    invalid_shell += 1
                if step.get("parse_status") in {"empty", "truncated_json", "prose_only"}:
                    empty_parse += 1
        rows.append(
            {
                "baseline_id": env.get("baseline_id"),
                "task_id": env.get("task_id"),
                "success": env.get("final_success_label") == "pass",
                "final_success_label": env.get("final_success_label"),
                "failure_category": metrics.get("failure_category"),
                "end_task_success": metrics.get("end_task_success"),
                "total_steps": total_steps,
                "invalid_shell_steps": invalid_shell,
                "empty_parse_steps": empty_parse,
                "envelope_path": str(path),
                "shell_steps_path": str(steps_path) if steps_path else None,
            }
        )
    return rows


def _baseline_pass_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Baseline | Pass | Rate |",
        "|----------|------|------|",
    ]
    for bid, stats in sorted(summary.get("baselines", {}).items()):
        lines.append(f"| `{bid}` | {stats.get('correct', 0)}/{stats.get('runs', 0)} | {stats.get('success_rate', 0):.1%} |")
    return lines


def _env_failure_rate(summary: dict[str, Any]) -> float | None:
    total = summary.get("total_runs", 0)
    if not total:
        return None
    env = summary.get("failure_categories", {}).get("environment_failure", 0)
    return env / total


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_baseline[row["baseline_id"]].append(row)
    baselines = {}
    for bid, items in by_baseline.items():
        n = len(items)
        correct = sum(1 for i in items if i["success"])
        baselines[bid] = {
            "runs": n,
            "correct": correct,
            "success_rate": correct / n if n else 0,
            "mean_steps": round(sum(i["total_steps"] for i in items) / n, 2) if n else 0,
            "invalid_shell_steps": sum(i["invalid_shell_steps"] for i in items),
            "empty_parse_steps": sum(i["empty_parse_steps"] for i in items),
        }
    total_steps = sum(r["total_steps"] for r in rows)
    return {
        "total_runs": len(rows),
        "baselines": baselines,
        "failure_categories": dict(Counter(r.get("failure_category") or "unknown" for r in rows)),
        "invalid_shell_step_rate": round(
            sum(r["invalid_shell_steps"] for r in rows) / total_steps, 4
        )
        if total_steps
        else None,
        "per_task": rows,
    }


def render_markdown(before: dict[str, Any], after: dict[str, Any]) -> str:
    before_pass = sum(b.get("correct", 0) for b in before.get("baselines", {}).values())
    after_pass = sum(b.get("correct", 0) for b in after.get("baselines", {}).values())
    before_env = _env_failure_rate(before)
    after_env = _env_failure_rate(after)
    empty_parse_total = sum(r.get("empty_parse_steps", 0) for r in after.get("per_task", []))
    total_steps = sum(r.get("total_steps", 0) for r in after.get("per_task", []))

    lines = [
        "# T3 ACI Rerun Comparison",
        "",
        "Compare original T3 pilot vs post-ACI-patch rerun (3 tasks × 5 baselines).",
        "",
        "## Before (original T3)",
        "",
        f"- Total runs: {before.get('total_runs')}",
        f"- Total pass: {before_pass}/{before.get('total_runs')}",
        f"- Failure categories: {before.get('failure_categories')}",
        "",
        *_baseline_pass_table(before),
        "",
        "## After (ACI rerun)",
        "",
        f"- Total runs: {after.get('total_runs')}",
        f"- Total pass: {after_pass}/{after.get('total_runs')}",
        f"- Failure categories: {after.get('failure_categories')}",
        f"- Invalid-shell step rate: {after.get('invalid_shell_step_rate')}",
        f"- Empty/truncated parse steps: {empty_parse_total}/{total_steps}",
        "",
        *_baseline_pass_table(after),
        "",
        "### Step metrics (after)",
        "",
        "| Baseline | Mean steps | Invalid-shell | Empty-parse |",
        "|----------|------------|---------------|-------------|",
    ]
    for bid, stats in sorted(after.get("baselines", {}).items()):
        lines.append(
            f"| `{bid}` | {stats['mean_steps']:.1f} | {stats['invalid_shell_steps']} | "
            f"{stats['empty_parse_steps']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Pass count: before **{before_pass}** → after **{after_pass}**.",
        ]
    )
    if before_env is not None and after_env is not None:
        lines.append(
            f"- Environment failure rate: before **{before_env:.1%}** → after **{after_env:.1%}** "
            f"(Brief F target < 10%)."
        )
    lines.extend(
        [
            f"- Invalid-shell step rate after patch: **{after.get('invalid_shell_step_rate')}** "
            f"(Brief F target < 2%).",
            "- ACI patches reduced environment failures but did not raise total pass count; "
            "remaining failures are mostly agent-side on hard tasks (`fibonacci-server`, "
            "`configure-git-webserver`).",
            "- `agent_attention_llm_tuned` improved from 0/3 to 1/3 (pass on `fix-permissions`).",
            "- Defer ≥20-task TB matrix until agent failure drivers are understood; "
            "current bottleneck is task difficulty + step budget, not shell parsing.",
            "",
        ]
    )
    if after.get("total_runs", 0) < 15:
        lines.append(
            f"- **Note:** After rerun incomplete ({after['total_runs']}/15). Re-run: "
            "`bash experiments/terminal_bench/run_t3_pilot_async.sh`"
        )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare T3 ACI rerun vs original.")
    parser.add_argument("--before-summary", default="experiments/metrics/terminal_bench_matrix_summary.json")
    parser.add_argument("--after-dir", default="experiments/llm_runs/terminal_bench/t3_aci_rerun_pilot")
    parser.add_argument("--output-json", default="experiments/metrics/t3_aci_rerun_pilot_partial.json")
    parser.add_argument("--output-md", default="experiments/analysis/t3_aci_rerun_comparison.md")
    args = parser.parse_args()

    before = json.loads(Path(args.before_summary).read_text(encoding="utf-8"))
    after_rows = load_envelopes(Path(args.after_dir))
    after = aggregate(after_rows)
    after["scope"] = "T3 ACI rerun pilot (envelope scan)"
    after["source_dir"] = args.after_dir

    Path(args.output_json).write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.output_md).write_text(render_markdown(before, after), encoding="utf-8")
    print(json.dumps({"runs": after["total_runs"], "output_md": args.output_md}, indent=2))


if __name__ == "__main__":
    main()
