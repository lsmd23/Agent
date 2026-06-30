#!/usr/bin/env python3
"""Oracle route matrix and route-opportunity metrics (Brief A / Objective 1–2)."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# Matches docs/next_iteration/research_directions/03_objectives_and_metrics.md
REWARD_WEIGHTS = {
    "success": 1.0,
    "model_calls": 0.08,
    "total_tokens": 0.00005,
    "latency_ms": 0.00002,
}


def route_reward(row: dict[str, Any]) -> float:
    success = 1.0 if row.get("success") else 0.0
    return (
        REWARD_WEIGHTS["success"] * success
        - REWARD_WEIGHTS["model_calls"] * float(row.get("model_calls") or 0)
        - REWARD_WEIGHTS["total_tokens"] * float(row.get("total_tokens") or 0)
        - REWARD_WEIGHTS["latency_ms"] * float(row.get("latency_ms") or 0)
    )


def per_task_cost_normalized(row: dict[str, Any]) -> float:
    if not row.get("success"):
        return 0.0
    calls = float(row.get("model_calls") or 0)
    return (1.0 / calls) if calls > 0 else 0.0


def entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    ent = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        p = count / total
        ent -= p * math.log2(p)
    return ent


def _cheapest_successful(routes: list[dict[str, Any]]) -> dict[str, Any] | None:
    winners = [r for r in routes if r.get("success")]
    if not winners:
        return None
    return min(
        winners,
        key=lambda r: (
            float(r.get("model_calls") or 0),
            float(r.get("total_tokens") or 0),
            float(r.get("latency_ms") or 0),
            r.get("baseline_id", ""),
        ),
    )


def _best_reward_route(routes: list[dict[str, Any]]) -> dict[str, Any]:
    return max(routes, key=lambda r: (route_reward(r), r.get("baseline_id", "")))


def analyze(summary: dict[str, Any]) -> dict[str, Any]:
    rows = summary.get("per_task", [])
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)

    task_ids = sorted(by_task)
    baseline_ids = sorted({r["baseline_id"] for r in rows})

    per_task_out: list[dict[str, Any]] = []
    cheapest_winner_counts: Counter[str] = Counter()
    reward_winner_counts: Counter[str] = Counter()
    unique_rescue_baselines: Counter[str] = Counter()

    for task_id in task_ids:
        routes = by_task[task_id]
        route_by_baseline = {r["baseline_id"]: r for r in routes}
        any_success = any(r.get("success") for r in routes)
        cheapest = _cheapest_successful(routes)
        best_reward = _best_reward_route(routes)
        oracle_reward = route_reward(best_reward)

        if cheapest:
            cheapest_winner_counts[cheapest["baseline_id"]] += 1
        reward_winner_counts[best_reward["baseline_id"]] += 1

        solo_winners = [
            bid
            for bid, row in route_by_baseline.items()
            if row.get("success") and not any(
                other.get("success")
                for obid, other in route_by_baseline.items()
                if obid != bid
            )
        ]
        for bid in solo_winners:
            unique_rescue_baselines[bid] += 1

        per_baseline = {}
        for bid in baseline_ids:
            row = route_by_baseline.get(bid)
            if row is None:
                continue
            selected_reward = route_reward(row)
            per_baseline[bid] = {
                "success": bool(row.get("success")),
                "model_calls": row.get("model_calls"),
                "total_tokens": row.get("total_tokens"),
                "latency_ms": row.get("latency_ms"),
                "route_reward": round(selected_reward, 6),
                "cost_normalized_success": round(per_task_cost_normalized(row), 6),
                "regret_vs_oracle_reward": round(oracle_reward - selected_reward, 6),
            }

        per_task_out.append(
            {
                "task_id": task_id,
                "any_route_success": any_success,
                "oracle_success": int(any_success),
                "cheapest_successful_route": cheapest["baseline_id"] if cheapest else None,
                "cheapest_successful_model_calls": cheapest.get("model_calls") if cheapest else None,
                "best_reward_route": best_reward["baseline_id"],
                "oracle_route_reward": round(oracle_reward, 6),
                "oracle_cost_normalized_success": round(
                    per_task_cost_normalized(cheapest) if cheapest else 0.0, 6
                ),
                "solo_success_baselines": solo_winners,
                "baselines": per_baseline,
            }
        )

    n_tasks = len(task_ids) or 1
    oracle_success = sum(t["oracle_success"] for t in per_task_out) / n_tasks
    oracle_cost_norm = sum(t["oracle_cost_normalized_success"] for t in per_task_out) / n_tasks

    single_policies: dict[str, dict[str, Any]] = {}
    for bid in baseline_ids:
        base = summary.get("baselines", {}).get(bid, {})
        single_policies[bid] = {
            "accuracy": base.get("accuracy"),
            "correct": base.get("correct"),
            "mean_model_calls": base.get("mean_model_calls"),
            "cost_normalized_success": base.get("cost_normalized_success"),
        }

    best_single_by_success = max(
        baseline_ids,
        key=lambda bid: (
            single_policies[bid].get("accuracy") or 0,
            single_policies[bid].get("cost_normalized_success") or 0,
            bid,
        ),
    )
    best_single_by_cost_norm = max(
        baseline_ids,
        key=lambda bid: (single_policies[bid].get("cost_normalized_success") or 0, bid),
    )

    mean_regret_by_baseline: dict[str, float] = {}
    for bid in baseline_ids:
        regrets = [t["baselines"][bid]["regret_vs_oracle_reward"] for t in per_task_out if bid in t["baselines"]]
        mean_regret_by_baseline[bid] = round(sum(regrets) / len(regrets), 6) if regrets else 0.0

    winner_entropy_cheapest = entropy(cheapest_winner_counts)
    winner_entropy_reward = entropy(reward_winner_counts)
    max_entropy = math.log2(len(baseline_ids)) if baseline_ids else 0.0

    best_single_success_rate = single_policies[best_single_by_success].get("accuracy") or 0
    success_gap = oracle_success - best_single_success_rate
    route_opportunity_gap = oracle_cost_norm - (
        single_policies[best_single_by_cost_norm].get("cost_normalized_success") or 0
    )

    dominant_cheapest = (
        cheapest_winner_counts.most_common(1)[0] if cheapest_winner_counts else (None, 0)
    )
    dominant_share = dominant_cheapest[1] / n_tasks if dominant_cheapest[0] else 1.0

    outcome = classify_outcome(
        winner_entropy= winner_entropy_cheapest,
        max_entropy=max_entropy,
        success_gap=success_gap,
        route_opportunity_gap=route_opportunity_gap,
        dominant_share=dominant_share,
        unique_rescue_total=sum(unique_rescue_baselines.values()),
        n_tasks=n_tasks,
    )

    return {
        "scope": "Oracle route matrix and route-opportunity audit (Brief A).",
        "source_summary": None,
        "suite": summary.get("suite"),
        "tasks": summary.get("tasks"),
        "model": summary.get("model"),
        "provider": summary.get("provider"),
        "baselines": baseline_ids,
        "aggregate": {
            "oracle_success": round(oracle_success, 6),
            "oracle_cost_normalized_success": round(oracle_cost_norm, 6),
            "oracle_mean_model_calls_at_success": round(
                sum(
                    (t["cheapest_successful_model_calls"] or 0)
                    for t in per_task_out
                    if t["cheapest_successful_model_calls"] is not None
                )
                / max(1, sum(1 for t in per_task_out if t["cheapest_successful_model_calls"] is not None)),
                4,
            ),
            "winner_entropy_cheapest_successful": round(winner_entropy_cheapest, 6),
            "winner_entropy_best_reward": round(winner_entropy_reward, 6),
            "max_entropy_baselines": round(max_entropy, 6),
            "cheapest_successful_winner_counts": dict(sorted(cheapest_winner_counts.items())),
            "best_reward_winner_counts": dict(sorted(reward_winner_counts.items())),
            "unique_solo_success_counts": dict(sorted(unique_rescue_baselines.items())),
            "best_single_baseline_by_success": best_single_by_success,
            "best_single_success_rate": round(best_single_success_rate, 6),
            "best_single_baseline_by_cost_norm": best_single_by_cost_norm,
            "best_single_cost_normalized_success": single_policies[best_single_by_cost_norm].get(
                "cost_normalized_success"
            ),
            "oracle_vs_best_single_success_gap": round(success_gap, 6),
            "route_opportunity_gap": round(route_opportunity_gap, 6),
            "dominant_cheapest_baseline": dominant_cheapest[0],
            "dominant_cheapest_share": round(dominant_share, 6),
            "mean_regret_vs_oracle_reward": mean_regret_by_baseline,
            "single_policy_summary": single_policies,
            "evidence_outcome": outcome,
        },
        "per_task": per_task_out,
    }


def classify_outcome(
    *,
    winner_entropy: float,
    max_entropy: float,
    success_gap: float,
    route_opportunity_gap: float,
    dominant_share: float,
    unique_rescue_total: int,
    n_tasks: int,
) -> str:
    """Map metrics to Brief A outcome labels."""
    normalized_entropy = winner_entropy / max_entropy if max_entropy > 0 else 0.0

    # Strong single-policy dominance: one baseline wins cheapest route on most tasks.
    if dominant_share >= 0.85 and success_gap <= 0.04:
        return "falsified_or_blocked"

    # Clear multi-route opportunity: varied winners and oracle beats best fixed policy.
    if (
        normalized_entropy >= 0.45
        and (success_gap >= 0.02 or route_opportunity_gap >= 0.05 or unique_rescue_total >= 2)
    ):
        return "supports_direction"

    if normalized_entropy >= 0.25 or success_gap >= 0.02 or unique_rescue_total >= 1:
        return "weak_or_inconclusive"

    return "falsified_or_blocked"


def render_audit_markdown(result: dict[str, Any]) -> str:
    agg = result["aggregate"]
    lines = [
        "# Oracle Route Audit (Brief A)",
        "",
        "## Scope",
        "",
        "Route Opportunity Auditor on the 26-task code suite matrix (5 baselines, no new LLM calls).",
        "",
        "## Inputs Read",
        "",
        f"- `{result.get('source_summary')}`",
        "- `docs/next_iteration/research_directions/03_objectives_and_metrics.md` (Objective 1–2)",
        "- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief A)",
        "",
        "## Method",
        "",
        "- Per task: cheapest successful baseline = oracle cost route; max route_reward = oracle reward route.",
        "- `route_reward = success - 0.08*calls - 5e-5*tokens - 2e-5*latency_ms`.",
        "- Per-task cost-normalized success = `1/model_calls` if pass else `0`.",
        "",
        "## Commands Run",
        "",
        "```bash",
        "python3 experiments/analysis/oracle_route_matrix.py",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/metrics/oracle_route_matrix.json`",
        "- `experiments/analysis/oracle_route_audit.md`",
        "",
        "## Results",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Oracle success | {agg['oracle_success']:.1%} ({int(agg['oracle_success'] * result['tasks'])}/{result['tasks']}) |",
        f"| Best single baseline (success) | {agg['best_single_baseline_by_success']} @ {agg['best_single_success_rate']:.1%} |",
        f"| Success gap (oracle − best single) | {agg['oracle_vs_best_single_success_gap']:+.1%} |",
        f"| Oracle cost-normalized success | {agg['oracle_cost_normalized_success']:.4f} |",
        f"| Best single cost-normalized | {agg['best_single_baseline_by_cost_norm']} @ {agg['best_single_cost_normalized_success']:.4f} |",
        f"| Route opportunity gap | {agg['route_opportunity_gap']:+.4f} |",
        f"| Winner entropy (cheapest successful) | {agg['winner_entropy_cheapest_successful']:.3f} / max {agg['max_entropy_baselines']:.3f} |",
        f"| Dominant cheapest baseline | {agg['dominant_cheapest_baseline']} ({agg['dominant_cheapest_share']:.1%} of tasks) |",
        "",
        "### Cheapest-successful winner counts",
        "",
    ]
    for bid, count in agg["cheapest_successful_winner_counts"].items():
        lines.append(f"- `{bid}`: {count}/{result['tasks']}")
    lines.extend(
        [
            "",
            "### Unique solo success (only baseline to pass task)",
            "",
        ]
    )
    solo = agg["unique_solo_success_counts"]
    if solo:
        for bid, count in solo.items():
            lines.append(f"- `{bid}`: {count} task(s)")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "### Mean regret vs oracle reward",
            "",
        ]
    )
    for bid, regret in sorted(agg["mean_regret_vs_oracle_reward"].items(), key=lambda x: x[1]):
        lines.append(f"- `{bid}`: {regret:.4f}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ]
    )
    outcome = agg["evidence_outcome"]
    if outcome == "supports_direction":
        lines.append(
            "The suite shows meaningful per-task route variation. Oracle routing beats the best "
            "fixed baseline on success and/or cost-normalized success enough to justify cascade "
            "and router pilots (Brief B/E)."
        )
    elif outcome == "weak_or_inconclusive":
        lines.append(
            "Some route variation exists, but a single baseline may still dominate many tasks. "
            "Treat router learning as diagnostic only; prioritize cascade (Brief B) and harder tasks."
        )
    else:
        lines.append(
            "One fixed policy covers most tasks; oracle routing adds little over the best single "
            "baseline. Do not invest in learned routers on this suite alone."
        )
    lines.extend(
        [
            "",
            f"**Evidence outcome:** `{outcome}`",
            "",
            "## Next Questions",
            "",
        ]
    )
    if outcome == "supports_direction":
        lines.extend(
            [
                "- Implement Brief B cascade (direct → AA → MoA) on failure sets from this matrix.",
                "- Brief E: can cheap features predict `cheapest_successful_route`?",
                "- Brief C: ablate AA components on tasks where AA is cheapest-successful.",
            ]
        )
    elif outcome == "weak_or_inconclusive":
        lines.extend(
            [
                "- Brief B pilot only; measure cost per rescued task on oracle-failure tasks.",
                "- Harder task variants (drop fixture hints) and re-run Brief A.",
                "- Brief H: check whether module specialization explains non-dominant winners.",
            ]
        )
    else:
        lines.extend(
            [
                "- Pivot to cascade-as-rescue (MoA only on ReAct failures) without learned router.",
                "- Expand benchmark difficulty or switch primary eval to Terminal-Bench after Brief F.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute oracle route matrix from eval summary.")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--output-json", default="experiments/metrics/oracle_route_matrix.json")
    parser.add_argument("--output-md", default="experiments/analysis/oracle_route_audit.md")
    args = parser.parse_args()

    summary = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = analyze(summary)
    result["source_summary"] = args.input

    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_path = Path(args.output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_audit_markdown(result), encoding="utf-8")

    print(
        json.dumps(
            {
                "output_json": str(json_path),
                "output_md": str(md_path),
                "evidence_outcome": result["aggregate"]["evidence_outcome"],
                "oracle_success": result["aggregate"]["oracle_success"],
                "route_opportunity_gap": result["aggregate"]["route_opportunity_gap"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
