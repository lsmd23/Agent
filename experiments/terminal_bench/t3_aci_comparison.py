#!/usr/bin/env python3
"""Compare T3 pilot before/after ACI patches from envelope directories."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_envelopes(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*__envelope.json")):
        env = json.loads(path.read_text(encoding="utf-8"))
        metrics = env.get("metrics_summary", {})
        run_dir = Path(metrics.get("raw_log_dir") or path.with_name(path.name.replace("__envelope.json", "")))
        steps_path = run_dir / "shell_steps.json"
        invalid_shell = 0
        empty_parse = 0
        total_steps = 0
        if steps_path.exists():
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
            }
        )
    return rows


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
    lines = [
        "# T3 ACI Rerun Comparison",
        "",
        "Compare original T3 pilot vs post-ACI-patch rerun (3 tasks × 5 baselines target).",
        "",
        "## Before (original T3)",
        "",
        f"- Total runs: {before.get('total_runs')}",
        f"- Pass rate: {before.get('baselines', {})}",
        f"- Failure categories: {before.get('failure_categories')}",
        "",
        "## After (ACI rerun)",
        "",
        f"- Total runs: {after.get('total_runs')}",
        f"- Invalid-shell step rate: {after.get('invalid_shell_step_rate')}",
        f"- Failure categories: {after.get('failure_categories')}",
        "",
        "### By baseline (after)",
        "",
        "| Baseline | Runs | Success | Mean steps | Invalid-shell steps |",
        "|----------|------|---------|------------|---------------------|",
    ]
    for bid, stats in sorted(after.get("baselines", {}).items()):
        lines.append(
            f"| `{bid}` | {stats['runs']} | {stats['success_rate']:.1%} | "
            f"{stats['mean_steps']:.1f} | {stats['invalid_shell_steps']} |"
        )

    before_pass = sum(b.get("correct", 0) for b in before.get("baselines", {}).values())
    after_pass = sum(b.get("correct", 0) for b in after.get("baselines", {}).values())
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Pass count: before **{before_pass}** → after **{after_pass}** (partial if after < 15).",
            "- Target from Brief F: invalid_shell_step_rate < 0.02, env failure rate < 0.10.",
            "",
        ]
    )
    if after.get("total_runs", 0) < 15:
        lines.append(
            f"- **Note:** After rerun incomplete ({after['total_runs']}/15). Re-run: "
            "`python3 experiments/terminal_bench/run_t3_matrix.py --limit-tasks 3 "
            "--summary-output experiments/metrics/t3_aci_rerun_pilot_summary.json`"
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
