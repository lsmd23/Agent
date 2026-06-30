#!/usr/bin/env python3
"""Bootstrap CIs and paired deltas from code-matrix summary JSON."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def bootstrap_accuracy(successes: list[bool], *, n_samples: int = 5000, seed: int = 0) -> dict[str, float]:
    if not successes:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    rng = random.Random(seed)
    n = len(successes)
    draws: list[float] = []
    for _ in range(n_samples):
        sample = [successes[rng.randrange(n)] for _ in range(n)]
        draws.append(sum(sample) / n)
    draws.sort()
    lo = draws[int(0.025 * n_samples)]
    hi = draws[int(0.975 * n_samples)]
    return {"mean": sum(successes) / n, "ci_low": lo, "ci_high": hi}


def paired_delta(
    rows: list[dict[str, Any]], baseline_a: str, baseline_b: str
) -> dict[str, Any]:
    by_task: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in rows:
        by_task[row["task_id"]][row["baseline_id"]] = bool(row["success"])
    shared = sorted(set(by_task) & {t for t, m in by_task.items() if baseline_a in m and baseline_b in m})
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


def analyze(summary: dict[str, Any]) -> dict[str, Any]:
    rows = summary.get("per_task", [])
    by_baseline: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        by_baseline[row["baseline_id"]].append(bool(row["success"]))

    out: dict[str, Any] = {
        "scope": "Bootstrap task-level accuracy CIs and paired deltas.",
        "tasks": summary.get("tasks"),
        "model": summary.get("model"),
        "provider": summary.get("provider"),
        "baselines": {},
        "paired_comparisons": [],
    }
    for baseline_id, successes in by_baseline.items():
        base = summary.get("baselines", {}).get(baseline_id, {})
        out["baselines"][baseline_id] = {
            **bootstrap_accuracy(successes),
            "mean_model_calls": base.get("mean_model_calls"),
            "mean_total_tokens": base.get("mean_total_tokens"),
            "mean_latency_ms": base.get("mean_latency_ms"),
            "cost_normalized_success": base.get("cost_normalized_success"),
        }

    baseline_ids = list(by_baseline)
    reference = "single_react_llm_agent"
    if reference in baseline_ids:
        for other in baseline_ids:
            if other != reference:
                out["paired_comparisons"].append(paired_delta(rows, other, reference))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute bootstrap CIs from matrix summary.")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--output", default="experiments/metrics/code_full_matrix_with_ci.json")
    args = parser.parse_args()

    summary = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = analyze(summary)
    result["source_summary"] = args.input
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out_path), "baselines": list(result["baselines"])}, indent=2))


if __name__ == "__main__":
    main()
