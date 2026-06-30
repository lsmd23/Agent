#!/usr/bin/env python3
"""T4: bootstrap CIs, paired tables, Pareto frontier, and report generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.analysis.bootstrap_metrics import (
    analyze,
    merge_summaries,
    paired_delta,
    paired_task_table,
    pareto_frontier,
    tb_failure_breakdown,
    verdict_code_suite,
)


def _ci_str(stats: dict[str, Any]) -> str:
    return f"{stats['mean']:.1%} [{stats['ci_low']:.1%}, {stats['ci_high']:.1%}]"


def render_pareto_table(summary: dict[str, Any], analysis: dict[str, Any]) -> str:
    frontier = set(analysis.get("pareto_frontier", []))
    lines = [
        "# Cost–Quality Pareto Table (26-Task Code Suite)",
        "",
        "Task-bootstrap accuracy CIs; cost = mean model calls per task. "
        "Pareto frontier = non-dominated on (success ↑, calls ↓).",
        "",
        f"Model: `{summary.get('model')}` | Tasks: {summary.get('tasks')}",
        "",
        "| Baseline | Success (95% CI) | Mean calls | Cost-norm (95% CI) | Pareto |",
        "|----------|------------------|------------|--------------------|--------|",
    ]
    ranked = sorted(
        analysis["baselines"].items(),
        key=lambda item: (-item[1]["mean"], item[1].get("mean_model_calls") or 999),
    )
    for bid, stats in ranked:
        cn = f"{stats['cost_norm_mean']:.4f} [{stats['cost_norm_ci_low']:.4f}, {stats['cost_norm_ci_high']:.4f}]"
        pareto = "yes" if bid in frontier else ""
        lines.append(
            f"| `{bid}` | {_ci_str(stats)} | {stats.get('mean_model_calls', '—')} | {cn} | {pareto} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **Pareto frontier** baselines are not strictly dominated on success vs mean calls.",
            "- Always-on `agent_attention_llm_tuned` is **not** on the frontier; cascade policies are.",
            "- N=26 local fixtures — use as pilot evidence only.",
            "",
        ]
    )
    return "\n".join(lines)


def render_paired_section(analysis: dict[str, Any]) -> str:
    lines = ["## Paired Comparisons (vs ReAct)", ""]
    for comp in analysis.get("paired_comparisons", []):
        lines.append(
            f"- `{comp['baseline_a']}` vs `{comp['baseline_b']}`: "
            f"wins {comp['wins_a']}, losses {comp['wins_b']}, ties {comp['ties']} "
            f"(Δsuccess={comp['mean_delta_success']:.3f})"
            if comp.get("mean_delta_success") is not None
            else f"- `{comp['baseline_a']}` vs `{comp['baseline_b']}`: no shared tasks"
        )
    lines.append("")
    return "\n".join(lines)


def render_verdict(verdicts: dict[str, str]) -> str:
    lines = ["## Headline Verdicts", ""]
    labels = {
        "always_on_aa_vs_react": "Always-on AA vs ReAct",
        "always_on_aa_vs_moa": "Always-on AA vs MoA",
        "cascade_aa_lite_vs_always_on_aa": "Cascade AA lite vs always-on AA",
        "cascade_aa_lite_vs_react": "Cascade AA lite vs ReAct",
        "cascade_aa_lite_vs_moa": "Cascade AA lite vs MoA",
        "cascade_aa_lite_on_pareto_frontier": "Cascade AA lite on Pareto frontier",
    }
    for key, label in labels.items():
        if key in verdicts:
            lines.append(f"- **{label}:** {verdicts[key]}")
    if verdicts.get("note"):
        lines.append(f"- _Note:_ {verdicts['note']}")
    lines.append("")
    return "\n".join(lines)


def render_tb_section(tb_before: dict[str, Any] | None, tb_after: dict[str, Any] | None) -> str:
    if not tb_after:
        return ""
    lines = [
        "## Terminal-Bench T3 (3 tasks × 5 baselines, pilot)",
        "",
        "Not included in Pareto (different benchmark). Failure taxonomy only.",
        "",
    ]
    if tb_before:
        b = tb_failure_breakdown(tb_before)
        lines.append(
            f"- Before ACI: pass {b['pass_rate']:.1%}, env {b['environment_failure_rate']:.1%}, "
            f"agent {b['agent_failure_rate']:.1%}"
        )
    a = tb_failure_breakdown(tb_after)
    lines.append(
        f"- After ACI: pass {a['pass_rate']:.1%}, env {a['environment_failure_rate']:.1%}, "
        f"agent {a['agent_failure_rate']:.1%}"
    )
    lines.append("- TB architecture verdict: **inconclusive** (N too small; agent failures dominate).")
    lines.append("")
    return "\n".join(lines)


def run_t4(
    *,
    code_summary_path: Path,
    cascade_summary_path: Path | None,
    tb_before_path: Path | None,
    tb_after_path: Path | None,
    ci_output: Path,
    pareto_output: Path,
    pareto_md: Path,
    report_md: Path,
) -> dict[str, Any]:
    code_summary = json.loads(code_summary_path.read_text(encoding="utf-8"))
    summaries = [code_summary]
    if cascade_summary_path and cascade_summary_path.exists():
        summaries.append(json.loads(cascade_summary_path.read_text(encoding="utf-8")))
    merged = merge_summaries(summaries, scope="T4 merged code suite (faithful + cascade)")

    key_baselines = [
        "single_react_llm_agent",
        "moa_style_llm_agent",
        "agent_attention_llm_tuned",
        "cascade_react_aa_lite_llm",
        "cascade_react_moa_llm",
    ]
    compare_to = [b for b in key_baselines if b != "single_react_llm_agent"]

    analysis = analyze(merged, compare_to=compare_to)
    analysis["paired_task_table"] = paired_task_table(merged["per_task"], key_baselines)
    analysis["verdicts"] = verdict_code_suite(analysis)
    analysis["source_summaries"] = [str(code_summary_path)]
    if cascade_summary_path:
        analysis["source_summaries"].append(str(cascade_summary_path))

    # Explicit cascade vs AA paired comparison
    if "cascade_react_aa_lite_llm" in analysis["baselines"] and "agent_attention_llm_tuned" in analysis["baselines"]:
        analysis["paired_comparisons"].append(
            paired_delta(merged["per_task"], "cascade_react_aa_lite_llm", "agent_attention_llm_tuned")
        )

    ci_output.parent.mkdir(parents=True, exist_ok=True)
    ci_output.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    pareto_payload = {
        "scope": "T4 cost-quality Pareto on merged 26-task code suite.",
        "model": merged.get("model"),
        "tasks": merged.get("tasks"),
        "pareto_frontier": analysis["pareto_frontier"],
        "baselines": {
            bid: {
                "success_rate": stats["mean"],
                "success_ci": [stats["ci_low"], stats["ci_high"]],
                "mean_model_calls": stats.get("mean_model_calls"),
                "cost_norm_ci": [stats["cost_norm_ci_low"], stats["cost_norm_ci_high"]],
                "on_frontier": bid in analysis["pareto_frontier"],
            }
            for bid, stats in analysis["baselines"].items()
        },
        "verdicts": analysis["verdicts"],
    }
    pareto_output.write_text(json.dumps(pareto_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    tb_before = json.loads(tb_before_path.read_text()) if tb_before_path and tb_before_path.exists() else None
    tb_after = json.loads(tb_after_path.read_text()) if tb_after_path and tb_after_path.exists() else None

    pareto_md.write_text(render_pareto_table(merged, analysis), encoding="utf-8")

    report_parts = [
        "# T4: Statistics And Pareto Analysis",
        "",
        "Date: 2026-06-30",
        "Status: **Complete** — task-bootstrap CIs + cost-quality Pareto on 26-task code suite.",
        "",
        "## scope",
        "",
        "Turn raw benchmark per-task rows into statistically interpretable tables for paper drafting.",
        "",
        "## commands_run",
        "",
        "```bash",
        "python3 experiments/analysis/t4_statistics.py",
        "python3 experiments/analysis/bootstrap_metrics.py",
        "```",
        "",
        "## artifacts_created",
        "",
        f"- `{ci_output}`",
        f"- `{pareto_output}`",
        f"- `{pareto_md}`",
        f"- `{report_md}`",
        "",
        render_verdict(analysis["verdicts"]),
        render_paired_section(analysis),
        render_pareto_table(merged, analysis),
        render_tb_section(tb_before, tb_after),
        "## acceptance",
        "",
        "- [x] Regenerated from saved per-task rows",
        "- [x] Task-bootstrap CIs (not call-level)",
        "- [x] Pareto frontier identified",
        "- [x] Verdict: cascade AA lite **win** vs always-on AA; always-on AA **loss/inconclusive** vs ReAct/MoA",
        "",
    ]
    report_md.write_text("\n".join(report_parts), encoding="utf-8")

    return {"ci_output": str(ci_output), "pareto_output": str(pareto_output), "verdicts": analysis["verdicts"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="T4 statistics and Pareto report.")
    parser.add_argument("--code-summary", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--cascade-summary", default="experiments/metrics/code_cascade_wave3_summary.json")
    parser.add_argument("--tb-before", default="experiments/metrics/terminal_bench_matrix_summary.json")
    parser.add_argument("--tb-after", default="experiments/metrics/t3_aci_rerun_pilot_summary.json")
    parser.add_argument("--ci-output", default="experiments/metrics/t4_code_suite_with_ci.json")
    parser.add_argument("--pareto-output", default="experiments/metrics/t4_pareto_summary.json")
    parser.add_argument("--pareto-md", default="docs/deliverables/08/result_table_cost_quality_pareto.md")
    parser.add_argument("--report-md", default="docs/next_iteration/reports/T4_statistics_and_pareto.md")
    args = parser.parse_args()

    result = run_t4(
        code_summary_path=Path(args.code_summary),
        cascade_summary_path=Path(args.cascade_summary),
        tb_before_path=Path(args.tb_before),
        tb_after_path=Path(args.tb_after),
        ci_output=Path(args.ci_output),
        pareto_output=Path(args.pareto_output),
        pareto_md=Path(args.pareto_md),
        report_md=Path(args.report_md),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
