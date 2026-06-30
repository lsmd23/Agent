#!/usr/bin/env python3
"""Bootstrap CIs, paired deltas, and Pareto helpers for matrix summaries."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def bootstrap_mean(values: list[float], *, n_samples: int = 5000, seed: int = 0) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    rng = random.Random(seed)
    n = len(values)
    draws: list[float] = []
    for _ in range(n_samples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        draws.append(sum(sample) / n)
    draws.sort()
    lo = draws[int(0.025 * n_samples)]
    hi = draws[int(0.975 * n_samples)]
    return {"mean": sum(values) / n, "ci_low": lo, "ci_high": hi}


def bootstrap_accuracy(successes: list[bool], *, n_samples: int = 5000, seed: int = 0) -> dict[str, float]:
    return bootstrap_mean([1.0 if s else 0.0 for s in successes], n_samples=n_samples, seed=seed)


def task_cost_normalized(row: dict[str, Any]) -> float:
    if not row.get("success"):
        return 0.0
    calls = row.get("model_calls") or 1
    return 1.0 / float(calls)


def merge_summaries(summaries: list[dict[str, Any]], *, scope: str) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "scope": scope,
        "suite": summaries[0].get("suite") if summaries else None,
        "tasks": summaries[0].get("tasks") if summaries else None,
        "model": summaries[0].get("model") if summaries else None,
        "provider": summaries[0].get("provider") if summaries else None,
        "baselines": {},
        "per_task": [],
    }
    for summary in summaries:
        merged["baselines"].update(summary.get("baselines", {}))
        merged["per_task"].extend(summary.get("per_task", []))
    task_ids = sorted({row["task_id"] for row in merged["per_task"]})
    merged["tasks"] = len(task_ids)
    merged["task_ids"] = task_ids
    return merged


def paired_delta(
    rows: list[dict[str, Any]], baseline_a: str, baseline_b: str
) -> dict[str, Any]:
    by_task: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in rows:
        by_task[row["task_id"]][row["baseline_id"]] = bool(row["success"])
    shared = sorted(t for t, m in by_task.items() if baseline_a in m and baseline_b in m)
    deltas = [int(by_task[t][baseline_a]) - int(by_task[t][baseline_b]) for t in shared]
    wins_a = sum(1 for d in deltas if d > 0)
    wins_b = sum(1 for d in deltas if d < 0)
    ties = sum(1 for d in deltas if d == 0)
    return {
        "baseline_a": baseline_a,
        "baseline_b": baseline_b,
        "paired_tasks": len(shared),
        "wins_a": wins_a,
        "wins_b": wins_b,
        "ties": ties,
        "mean_delta_success": (sum(deltas) / len(deltas)) if deltas else None,
    }


def paired_task_table(rows: list[dict[str, Any]], baseline_ids: list[str]) -> list[dict[str, Any]]:
    by_task: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["baseline_id"] in baseline_ids:
            by_task[row["task_id"]][row["baseline_id"]] = row
    table: list[dict[str, Any]] = []
    for task_id in sorted(by_task):
        entry: dict[str, Any] = {"task_id": task_id}
        for bid in baseline_ids:
            row = by_task[task_id].get(bid)
            entry[bid] = bool(row.get("success")) if row else None
            if row:
                entry[f"{bid}_calls"] = row.get("model_calls")
        table.append(entry)
    return table


def pareto_frontier(baselines: dict[str, dict[str, Any]]) -> list[str]:
    """Non-dominated baselines: maximize success, minimize mean_model_calls."""
    points = []
    for bid, stats in baselines.items():
        success = stats.get("mean") if "mean" in stats else stats.get("accuracy")
        calls = stats.get("mean_model_calls")
        if success is None or calls is None:
            continue
        points.append({"baseline_id": bid, "success_rate": float(success), "mean_model_calls": float(calls)})

    dominated: set[str] = set()
    for p in points:
        for q in points:
            if p["baseline_id"] == q["baseline_id"]:
                continue
            if (
                q["success_rate"] >= p["success_rate"]
                and q["mean_model_calls"] <= p["mean_model_calls"]
                and (
                    q["success_rate"] > p["success_rate"]
                    or q["mean_model_calls"] < p["mean_model_calls"]
                )
            ):
                dominated.add(p["baseline_id"])
                break
    return sorted(p["baseline_id"] for p in points if p["baseline_id"] not in dominated)


def analyze(
    summary: dict[str, Any],
    *,
    reference: str = "single_react_llm_agent",
    compare_to: list[str] | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    rows = summary.get("per_task", [])
    by_baseline_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_baseline_rows[row["baseline_id"]].append(row)

    out: dict[str, Any] = {
        "scope": "Bootstrap task-level CIs, paired deltas, and Pareto inputs.",
        "tasks": summary.get("tasks"),
        "task_ids": summary.get("task_ids"),
        "model": summary.get("model"),
        "provider": summary.get("provider"),
        "baselines": {},
        "paired_comparisons": [],
        "pareto_frontier": [],
    }

    for baseline_id, baseline_rows in by_baseline_rows.items():
        successes = [bool(r["success"]) for r in baseline_rows]
        cost_norm_values = [task_cost_normalized(r) for r in baseline_rows]
        base = summary.get("baselines", {}).get(baseline_id, {})
        acc = bootstrap_accuracy(successes, seed=seed)
        cn = bootstrap_mean(cost_norm_values, seed=seed)
        out["baselines"][baseline_id] = {
            **acc,
            "cost_norm_mean": cn["mean"],
            "cost_norm_ci_low": cn["ci_low"],
            "cost_norm_ci_high": cn["ci_high"],
            "mean_model_calls": base.get("mean_model_calls"),
            "mean_total_tokens": base.get("mean_total_tokens"),
            "mean_latency_ms": base.get("mean_latency_ms"),
            "cost_normalized_success": base.get("cost_normalized_success"),
        }

    baseline_ids = list(by_baseline_rows)
    targets = compare_to or [b for b in baseline_ids if b != reference]
    if reference in baseline_ids:
        for other in targets:
            if other in baseline_ids and other != reference:
                out["paired_comparisons"].append(paired_delta(rows, other, reference))

    out["pareto_frontier"] = pareto_frontier(out["baselines"])
    return out


def tb_failure_breakdown(summary: dict[str, Any]) -> dict[str, Any]:
    rows = summary.get("per_task", [])
    total = len(rows) or 1
    categories = defaultdict(int)
    for row in rows:
        categories[row.get("failure_category") or "unknown"] += 1
    return {
        "total_runs": len(rows),
        "failure_categories": dict(categories),
        "environment_failure_rate": categories.get("environment_failure", 0) / total,
        "agent_failure_rate": categories.get("agent_failure", 0) / total,
        "pass_rate": categories.get("none", 0) / total,
    }


def verdict_code_suite(analysis: dict[str, Any]) -> dict[str, str]:
    """Headline verdicts for paper drafting."""
    baselines = analysis.get("baselines", {})
    frontier = set(analysis.get("pareto_frontier", []))
    verdicts: dict[str, str] = {}

    aa = "agent_attention_llm_tuned"
    react = "single_react_llm_agent"
    moa = "moa_style_llm_agent"
    cascade = "cascade_react_aa_lite_llm"

    def _cmp(a: str, b: str, *, metric: str = "mean") -> str:
        if a not in baselines or b not in baselines:
            return "inconclusive"
        sa, sb = baselines[a], baselines[b]
        ma, mb = sa.get(metric, 0), sb.get(metric, 0)
        la, ha = sa.get("ci_low", ma), sa.get("ci_high", ma)
        lb, hb = sb.get("ci_low", mb), sb.get("ci_high", mb)
        if ha < lb:
            return "loss"
        if hb < la:
            return "win"
        return "inconclusive"

    verdicts["always_on_aa_vs_react"] = _cmp(aa, react)
    verdicts["always_on_aa_vs_moa"] = _cmp(aa, moa)
    if cascade in baselines:
        verdicts["cascade_aa_lite_vs_always_on_aa"] = _cmp(cascade, aa)
        verdicts["cascade_aa_lite_vs_react"] = _cmp(cascade, react)
        verdicts["cascade_aa_lite_vs_moa"] = _cmp(cascade, moa)
        verdicts["cascade_aa_lite_on_pareto_frontier"] = (
            "yes" if cascade in frontier else "no"
        )
    verdicts["note"] = (
        "Task-bootstrap CIs on N=26 local fixtures; not publication-grade alone."
    )
    return verdicts


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute bootstrap CIs from matrix summary.")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--output", default="experiments/metrics/code_full_matrix_with_ci.json")
    parser.add_argument("--reference", default="single_react_llm_agent")
    args = parser.parse_args()

    summary = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = analyze(summary, reference=args.reference)
    result["source_summary"] = args.input
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out_path), "baselines": list(result["baselines"])}, indent=2))


if __name__ == "__main__":
    main()
