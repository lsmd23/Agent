"""Replay cascade policies on existing per-baseline matrix rows (zero LLM cost)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.cascade.cascade_policy import CASCADE_POLICIES, cascade_baseline_id, policy_for


def _index_per_task(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        out[row["task_id"]][row["baseline_id"]] = row
    return out


def simulate_task(
    task_id: str,
    stages: list[str],
    by_baseline: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    stage_rows: list[dict[str, Any]] = []
    rescued_by: str | None = None
    success = False
    halt_stage: str | None = None

    for stage_id in stages:
        row = by_baseline.get(stage_id)
        if row is None:
            raise KeyError(f"Missing baseline={stage_id!r} for task={task_id!r}")
        stage_rows.append(
            {
                "baseline_id": stage_id,
                "success": bool(row.get("success")),
                "model_calls": int(row.get("model_calls") or 0),
                "total_tokens": int(row.get("total_tokens") or 0),
                "latency_ms": int(row.get("latency_ms") or 0),
            }
        )
        if row.get("success"):
            success = True
            halt_stage = stage_id
            if stage_id != stages[0]:
                rescued_by = stage_id
            break

    if not success:
        halt_stage = stages[-1]

    total_calls = sum(s["model_calls"] for s in stage_rows)
    total_tokens = sum(s["total_tokens"] for s in stage_rows)
    total_latency = sum(s["latency_ms"] for s in stage_rows)
    stages_run = len(stage_rows)

    return {
        "task_id": task_id,
        "success": success,
        "final_success_label": "pass" if success else "fail",
        "halt_stage": halt_stage,
        "stages_run": stages_run,
        "escalated": stages_run > 1,
        "rescued_by": rescued_by,
        "model_calls": total_calls,
        "total_tokens": total_tokens,
        "latency_ms": total_latency,
        "cost_normalized_success": round((1.0 / total_calls), 6) if success and total_calls else 0.0,
        "stage_details": stage_rows,
    }


def replay_policy(summary: dict[str, Any], policy_id: str) -> dict[str, Any]:
    policy = policy_for(policy_id)
    stages: list[str] = policy["stages"]
    indexed = _index_per_task(summary.get("per_task", []))
    task_ids = sorted(indexed)

    per_task = [simulate_task(task_id, stages, indexed[task_id]) for task_id in task_ids]
    n = len(per_task) or 1
    correct = sum(1 for row in per_task if row["success"])
    escalated = [row for row in per_task if row["escalated"]]
    rescued = [row for row in per_task if row["rescued_by"]]

    mean_calls = sum(row["model_calls"] for row in per_task) / n
    cost_norm = (correct / n) / mean_calls if mean_calls > 0 else 0.0

    extra_cost_rescues = 0
    for row in rescued:
        first_calls = row["stage_details"][0]["model_calls"] if row["stage_details"] else 0
        extra_cost_rescues += row["model_calls"] - first_calls

    return {
        "policy_id": policy_id,
        "policy_label": policy["label"],
        "stages": stages,
        "baseline_id": cascade_baseline_id(policy_id),
        "tasks": n,
        "correct": correct,
        "accuracy": correct / n,
        "mean_model_calls": round(mean_calls, 4),
        "mean_total_tokens": round(sum(row["total_tokens"] for row in per_task) / n, 2),
        "mean_latency_ms": round(sum(row["latency_ms"] for row in per_task) / n, 2),
        "cost_normalized_success": round(cost_norm, 4),
        "escalation_rate": round(len(escalated) / n, 4),
        "escalation_success_gain": round(len(rescued) / n, 4),
        "rescued_task_count": len(rescued),
        "cost_per_rescued_task": round(extra_cost_rescues / len(rescued), 4) if rescued else None,
        "mean_extra_calls_on_escalated": round(
            sum(row["model_calls"] - row["stage_details"][0]["model_calls"] for row in escalated) / len(escalated),
            4,
        )
        if escalated
        else None,
        "per_task": per_task,
    }


def compare_to_baselines(replay: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    baselines = summary.get("baselines", {})
    refs = {
        "single_react_llm_agent": baselines.get("single_react_llm_agent", {}),
        "agent_attention_llm_tuned": baselines.get("agent_attention_llm_tuned", {}),
        "moa_style_llm_agent": baselines.get("moa_style_llm_agent", {}),
    }
    return {
        "accuracy_delta_vs_react": round(replay["accuracy"] - (refs["single_react_llm_agent"].get("accuracy") or 0), 4),
        "accuracy_delta_vs_moa": round(replay["accuracy"] - (refs["moa_style_llm_agent"].get("accuracy") or 0), 4),
        "accuracy_delta_vs_aa": round(replay["accuracy"] - (refs["agent_attention_llm_tuned"].get("accuracy") or 0), 4),
        "calls_delta_vs_react": round(replay["mean_model_calls"] - (refs["single_react_llm_agent"].get("mean_model_calls") or 0), 4),
        "calls_delta_vs_moa": round(replay["mean_model_calls"] - (refs["moa_style_llm_agent"].get("mean_model_calls") or 0), 4),
        "calls_delta_vs_aa": round(replay["mean_model_calls"] - (refs["agent_attention_llm_tuned"].get("mean_model_calls") or 0), 4),
        "cost_norm_delta_vs_aa": round(
            replay["cost_normalized_success"] - (refs["agent_attention_llm_tuned"].get("cost_normalized_success") or 0),
            4,
        ),
    }


def classify_cascade_outcome(replay: dict[str, Any], comparison: dict[str, Any]) -> str:
    acc_moa_gap = comparison["accuracy_delta_vs_moa"]
    calls_moa_delta = comparison["calls_delta_vs_moa"]
    cost_aa_delta = comparison["cost_norm_delta_vs_aa"]

    if acc_moa_gap >= -0.02 and calls_moa_delta <= -0.15 and cost_aa_delta > 0:
        return "supports_direction"
    if replay["accuracy"] >= 0.95 and calls_moa_delta < 0:
        return "supports_direction"
    if replay["accuracy"] > 0.88 and cost_aa_delta > 0:
        return "weak_or_inconclusive"
    return "falsified_or_blocked"


def analyze(summary_path: str | Path, *, policies: list[str] | None = None) -> dict[str, Any]:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    policy_ids = policies or list(CASCADE_POLICIES)
    replays = {pid: replay_policy(summary, pid) for pid in policy_ids}
    primary = replays.get("react_aa_moa") or next(iter(replays.values()))
    comparison = compare_to_baselines(primary, summary)
    outcome = classify_cascade_outcome(primary, comparison)

    return {
        "scope": "Cascade replay on existing matrix (Brief B pilot, zero new LLM calls).",
        "source_summary": str(summary_path),
        "suite": summary.get("suite"),
        "tasks": summary.get("tasks"),
        "model": summary.get("model"),
        "provider": summary.get("provider"),
        "policies": replays,
        "primary_policy_id": primary["policy_id"],
        "comparison_vs_baselines": comparison,
        "evidence_outcome": outcome,
    }


def render_audit_markdown(result: dict[str, Any]) -> str:
    primary = result["policies"][result["primary_policy_id"]]
    cmp_ = result["comparison_vs_baselines"]
    lines = [
        "# Cascade Pilot Audit (Brief B)",
        "",
        "## Scope",
        "",
        "Direct-first cascade replay on the 26-task code matrix (no new LLM calls).",
        "",
        "## Inputs Read",
        "",
        f"- `{result['source_summary']}`",
        f"- `experiments/metrics/oracle_route_matrix.json` (failure context from Brief A)",
        "- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief B)",
        "",
        "## Method",
        "",
        "Replay per-task stage outcomes from the full matrix:",
        "",
        "```text",
        "single_react → fail → agent_attention_llm_tuned → fail → moa_style",
        "```",
        "",
        "Aggregate escalation rate, rescue count, cost per rescued task, and cost-normalized success.",
        "",
        "## Commands Run",
        "",
        "```bash",
        "python3 experiments/cascade/run_cascade_pilot.py --mode replay",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/metrics/cascade_pilot_summary.json`",
        "- `experiments/analysis/cascade_pilot_audit.md`",
        "",
        "## Results",
        "",
        "### Primary policy: react → AA → MoA",
        "",
        "| Metric | Cascade | ReAct | AA tuned | MoA |",
        "|--------|---------|-------|----------|-----|",
    ]

    baselines = json.loads(Path(result["source_summary"]).read_text())["baselines"]
    react = baselines["single_react_llm_agent"]
    aa = baselines["agent_attention_llm_tuned"]
    moa = baselines["moa_style_llm_agent"]

    lines.extend(
        [
            f"| Accuracy | {primary['accuracy']:.1%} | {react['accuracy']:.1%} | {aa['accuracy']:.1%} | {moa['accuracy']:.1%} |",
            f"| Mean model calls | {primary['mean_model_calls']:.2f} | {react['mean_model_calls']:.2f} | {aa['mean_model_calls']:.2f} | {moa['mean_model_calls']:.2f} |",
            f"| Cost-norm success | {primary['cost_normalized_success']:.4f} | {react['cost_normalized_success']:.4f} | {aa['cost_normalized_success']:.4f} | {moa['cost_normalized_success']:.4f} |",
            "",
            f"- Escalation rate: **{primary['escalation_rate']:.1%}** ({primary['rescued_task_count']} rescued)",
            f"- Cost per rescued task (extra calls): **{primary['cost_per_rescued_task']}**",
            "",
            "### Escalation trigger table",
            "",
            "| Stage | Trigger |",
            "|-------|---------|",
            "| ReAct → AA | pytest fail after direct attempt |",
            "| AA → MoA | pytest fail after AA attempt |",
            "",
            "### Rescued tasks",
            "",
        ]
    )
    for row in primary["per_task"]:
        if row["rescued_by"]:
            stages = " → ".join(s["baseline_id"].replace("_llm_agent", "") for s in row["stage_details"])
            lines.append(
                f"- `{row['task_id']}`: rescued by **{row['rescued_by']}** ({stages}, {row['model_calls']} calls)"
            )
    if primary["rescued_task_count"] == 0:
        lines.append("- None")

    lines.extend(["", "### Alternate policy: react → MoA (skip AA)", ""])
    alt = result["policies"].get("react_moa")
    if alt:
        lines.extend(
            [
                f"- Accuracy: {alt['accuracy']:.1%}",
                f"- Mean calls: {alt['mean_model_calls']:.2f}",
                f"- Cost-norm: {alt['cost_normalized_success']:.4f}",
                f"- Escalation rate: {alt['escalation_rate']:.1%}",
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ]
    )
    outcome = result["evidence_outcome"]
    if outcome == "supports_direction":
        lines.append(
            "Cascade replay matches MoA-level success with materially lower mean calls than always-MoA "
            "and better cost-normalized success than always-AA. Direct-first escalation is viable; "
            "live validation should confirm replay assumptions."
        )
    elif outcome == "weak_or_inconclusive":
        lines.append(
            "Cascade improves over AA on cost-normalized success but savings vs MoA or accuracy vs ReAct "
            "need live confirmation."
        )
    else:
        lines.append("Replayed cascade does not beat fixed baselines on the primary metrics.")

    lines.extend(
        [
            "",
            f"**Evidence outcome:** `{outcome}`",
            "",
            "## Next Questions",
            "",
            "- Run live cascade pilot (`--mode live`) to confirm replay on fresh trajectories.",
            "- Compare react→MoA vs react→AA→MoA: is AA middle stage worth its cost on failures?",
            "- Brief C: ablate AA components used only in escalation slot.",
        ]
    )
    lines.append("")
    return "\n".join(lines)
