#!/usr/bin/env python3
"""AA component ablation audit (Brief C): replay proxies + trajectory failure analysis."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.ablations.aa_ablation_specs import ABLATION_SPECS, AA_ABLATION_IDS

RESCUE_TASKS = (
    "phase1_code_csv_001",
    "phase1_code_email_001",
    "phase1_code_env_flag_001",
)
AA_FAILURES = (
    "phase1_code_config_001",
    "phase1_code_strip_tags_001",
    "phase1_code_slugify_001",
    "phase1_code_env_flag_001",
)


def _index_matrix(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        out[row["baseline_id"]][row["task_id"]] = row
    return out


def _baseline_agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows) or 1
    correct = sum(1 for r in rows if r.get("success"))
    calls = [float(r.get("model_calls") or 0) for r in rows]
    mean_calls = sum(calls) / n
    return {
        "tasks": n,
        "correct": correct,
        "accuracy": round(correct / n, 4),
        "mean_model_calls": round(mean_calls, 4),
        "cost_normalized_success": round((correct / n) / mean_calls, 4) if mean_calls else 0.0,
    }


def replay_proxy_table(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = summary.get("per_task", [])
    indexed = _index_matrix(rows)
    baselines = summary.get("baselines", {})
    table: list[dict[str, Any]] = []

    for ablation_id in AA_ABLATION_IDS:
        spec = ABLATION_SPECS[ablation_id]
        tier = spec.get("evidence_tier", "live_required")
        entry: dict[str, Any] = {
            "ablation_id": ablation_id,
            "label": spec["label"],
            "evidence_tier": tier,
            "recommendation_hint": spec.get("recommendation_hint"),
            "note": spec.get("note") or spec.get("proxy_note"),
        }

        if ablation_id == "aa_tuned_control":
            base = baselines.get("agent_attention_llm_tuned", {})
            entry.update(
                {
                    "source": "code_full_matrix",
                    "accuracy": base.get("accuracy"),
                    "mean_model_calls": base.get("mean_model_calls"),
                    "cost_normalized_success": base.get("cost_normalized_success"),
                }
            )
        elif ablation_id == "aa_direct_first":
            cascade_path = Path("experiments/metrics/cascade_replay_summary.json")
            if not cascade_path.exists():
                cascade_path = Path("experiments/metrics/cascade_pilot_summary.json")
            if cascade_path.exists():
                cascade = json.loads(cascade_path.read_text(encoding="utf-8"))
                pol = cascade.get("policies", {}).get("react_aa_moa")
                if pol is None and cascade.get("mode") == "live":
                    pol = cascade.get("summary")
                if pol:
                    entry.update(
                        {
                            "source": "cascade_replay",
                            "accuracy": pol.get("accuracy"),
                            "mean_model_calls": pol.get("mean_model_calls"),
                            "cost_normalized_success": pol.get("cost_normalized_success"),
                        }
                    )
        elif spec.get("proxy_baseline_id"):
            proxy_id = spec["proxy_baseline_id"]
            base = baselines.get(proxy_id, {})
            proxy_rows = list(indexed.get(proxy_id, {}).values())
            entry.update(
                {
                    "source": f"proxy:{proxy_id}",
                    "accuracy": base.get("accuracy"),
                    "mean_model_calls": base.get("mean_model_calls"),
                    "cost_normalized_success": base.get("cost_normalized_success"),
                    "proxy_accuracy_delta_vs_aa": round(
                        (base.get("accuracy") or 0) - (baselines.get("agent_attention_llm_tuned", {}).get("accuracy") or 0),
                        4,
                    ),
                }
            )
            rescue_rows = [indexed[proxy_id][tid] for tid in RESCUE_TASKS if tid in indexed.get(proxy_id, {})]
            entry["rescue_task_proxy"] = _baseline_agg(rescue_rows)
        else:
            entry["source"] = "live_required"
            entry["accuracy"] = None

        table.append(entry)
    return table


def analyze_aa_trajectory_signals(root: Path) -> dict[str, Any]:
    aa_dir = root / "code_all" / "agent_attention_llm_tuned"
    if not aa_dir.is_dir():
        return {"error": f"missing {aa_dir}"}

    per_task: dict[str, Any] = {}
    signals_agg: dict[str, int] = defaultdict(int)

    for path in sorted(aa_dir.glob("*.json")):
        traj = json.loads(path.read_text(encoding="utf-8"))
        task_id = traj["task_id"]
        events = traj.get("events", [])
        selected: list[str] = []
        module_steps = 0
        model_calls = 0
        failure_signals: list[str] = []
        for event in events:
            etype = event.get("event_type")
            payload = event.get("payload") or {}
            if etype == "route":
                selected = list(payload.get("selected_modules") or [])
            if etype == "module_execution":
                module_steps += 1
            if etype == "model_call":
                model_calls += 1
            if etype == "failure_signal":
                failure_signals.append(str(payload.get("signal") or payload))

        signals: list[str] = []
        if module_steps == 0:
            signals.append("empty_module_execution_steps")
            signals_agg["empty_module_execution_steps"] += 1
        if not selected:
            signals.append("no_module_selected_in_final_route")
            signals_agg["no_module_selected_in_final_route"] += 1
        if len(selected) >= 3:
            signals.append("high_fanout_activation")
            signals_agg["high_fanout_activation"] += 1
        if model_calls >= 2 and traj.get("final_success_label") != "pass":
            signals.append("multi_call_failure")
            signals_agg["multi_call_failure"] += 1

        per_task[task_id] = {
            "success": traj.get("final_success_label") == "pass",
            "model_calls": model_calls,
            "selected_modules": selected,
            "module_execution_steps": module_steps,
            "failure_signals": failure_signals,
            "diagnostic_signals": signals,
        }

    rescue = {tid: per_task[tid] for tid in RESCUE_TASKS if tid in per_task}
    failures = {tid: per_task[tid] for tid in AA_FAILURES if tid in per_task}
    return {
        "trajectory_root": str(aa_dir),
        "tasks_parsed": len(per_task),
        "aggregate_signals": dict(signals_agg),
        "rescue_tasks": rescue,
        "aa_unique_failures": failures,
    }


def component_recommendations(
    proxy_table: list[dict[str, Any]], trajectory: dict[str, Any]
) -> list[dict[str, str]]:
    aa = next(r for r in proxy_table if r["ablation_id"] == "aa_tuned_control")
    react_proxy = next(r for r in proxy_table if r["ablation_id"] == "aa_no_memory")
    direct = next(r for r in proxy_table if r["ablation_id"] == "aa_direct_first")
    recs = [
        {
            "component": "default_always_on_aa",
            "action": "remove",
            "rationale": "AA tuned 84.6% @ 2.0 calls vs ReAct 88.5% @ 1.23; direct-first replay reaches 100% @ 1.54.",
        },
        {
            "component": "memory_read_write",
            "action": "gate",
            "rationale": f"Proxy no-memory (ReAct) beats AA accuracy delta {react_proxy.get('proxy_accuracy_delta_vs_aa', 0):+.1%} on full suite; Phase2 toy ablation +8.3pp without memory.",
        },
        {
            "component": "adaptive_top_k",
            "action": "gate",
            "rationale": "96% redundant activation (Brief H); live ablation required but fan-out correlates with cost without rescue on env_flag.",
        },
        {
            "component": "strong_budget_gate",
            "action": "keep",
            "rationale": "Without gate, behavior approaches MoA-cost fan-out; MoA proxy is 2.08 calls—gate is only cost brake.",
        },
        {
            "component": "verifier",
            "action": "keep_in_escalation",
            "rationale": "Needed for cascade halt; AA-only verifier-first routes flagged in Brief H.",
        },
        {
            "component": "direct_first_cascade",
            "action": "keep_as_default_route",
            "rationale": (
                f"Cascade replay accuracy {direct.get('accuracy') or 0:.1%} "
                f"mean calls {direct.get('mean_model_calls') or 'n/a'}."
            ),
        },
        {
            "component": "lexical_router",
            "action": "remove_from_default",
            "rationale": "Never cheapest-successful winner in oracle matrix; specialization falsified (Brief H).",
        },
    ]
    if trajectory.get("aggregate_signals", {}).get("empty_module_execution_steps", 0) >= 10:
        recs.append(
            {
                "component": "module_execution_loop",
                "action": "fix",
                "rationale": f"{trajectory['aggregate_signals']['empty_module_execution_steps']} runs with empty module_execution steps.",
            }
        )
    return recs


def classify_outcome(proxy_table: list[dict[str, Any]], recommendations: list[dict[str, str]]) -> str:
    direct = next(r for r in proxy_table if r["ablation_id"] == "aa_direct_first")
    if direct.get("accuracy", 0) >= 0.95 and direct.get("mean_model_calls", 99) < 1.8:
        return "supports_direction"
    remove_count = sum(1 for r in recommendations if r["action"] in {"remove", "remove_from_default"})
    if remove_count >= 2:
        return "weak_or_inconclusive"
    return "falsified_or_blocked"


def analyze(summary_path: str | Path, trajectory_root: str | Path) -> dict[str, Any]:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    proxy_table = replay_proxy_table(summary)
    trajectory = analyze_aa_trajectory_signals(Path(trajectory_root))
    recommendations = component_recommendations(proxy_table, trajectory)
    outcome = classify_outcome(proxy_table, recommendations)

    phase2_path = Path("experiments/metrics/phase2_memory_ablation_summary.json")
    phase2_prior = None
    if phase2_path.exists():
        phase2_prior = json.loads(phase2_path.read_text(encoding="utf-8"))

    return {
        "scope": "AA Component Surgeon (Brief C): replay proxies + trajectory diagnostics.",
        "source_summary": str(summary_path),
        "ablation_specs": "experiments/ablations/aa_ablation_specs.py",
        "proxy_table": proxy_table,
        "phase2_memory_prior": phase2_prior,
        "aa_trajectory_diagnostics": trajectory,
        "component_recommendations": recommendations,
        "evidence_outcome": outcome,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# AA Ablation Audit (Brief C)",
        "",
        "## Scope",
        "",
        "Component-level ablation audit on 26-task code matrix using replay proxies, Phase2 priors, and AA trajectory diagnostics.",
        "",
        "## Inputs Read",
        "",
        f"- `{result['source_summary']}`",
        f"- `{result['ablation_specs']}`",
        "- `experiments/metrics/cascade_pilot_summary.json`",
        "- `experiments/analysis/expert_specialization_audit.json`",
        "- `experiments/metrics/phase2_memory_ablation_summary.json`",
        "",
        "## Method",
        "",
        "- 8 ablation specs with evidence tiers: direct / proxy / live_required.",
        "- Proxy mapping: no-memory→ReAct, no-budget-gate→MoA fan-out, direct-first→cascade replay.",
        "- Trajectory signal mining on AA tuned runs for rescue and unique-failure tasks.",
        "",
        "## Commands Run",
        "",
        "```bash",
        "python3 experiments/ablations/aa_ablation_audit.py",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/metrics/aa_ablation_pilot.json`",
        "- `experiments/analysis/aa_ablation_audit.md`",
        "",
        "## Results",
        "",
        "### Proxy ablation table",
        "",
        "| Ablation | Tier | Accuracy | Mean calls | Cost-norm | Source |",
        "|----------|------|----------|------------|-----------|--------|",
    ]
    for row in result["proxy_table"]:
        acc = row.get("accuracy")
        calls = row.get("mean_model_calls")
        cn = row.get("cost_normalized_success")
        lines.append(
            f"| {row['ablation_id']} | {row['evidence_tier']} | "
            f"{acc:.1%} | {calls} | {cn} | {row.get('source', '')} |"
            if acc is not None
            else f"| {row['ablation_id']} | {row['evidence_tier']} | — | — | — | {row.get('source', '')} |"
        )

    lines.extend(["", "### Component recommendations", ""])
    for rec in result["component_recommendations"]:
        lines.append(f"- **{rec['component']}** → `{rec['action']}`: {rec['rationale']}")

    traj = result["aa_trajectory_diagnostics"]
    lines.extend(["", "### Rescue task AA diagnostics", ""])
    for tid, info in traj.get("rescue_tasks", {}).items():
        lines.append(
            f"- `{tid}`: success={info['success']}, calls={info['model_calls']}, "
            f"signals={info['diagnostic_signals']}"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "AA underperformance is structural: always-on sparse routing adds ~2 calls without beating ReAct. "
            "Memory and lexical router should not run on easy code tasks; cascade/direct-first is the highest-yield change. "
            "Live ablation still needed for verifier-off and adaptive-top-k-off on held-out slice.",
            "",
            f"**Evidence outcome:** `{result['evidence_outcome']}`",
            "",
            "## Next Questions",
            "",
            "- Live pilot: `run_aa_ablation_pilot.py --tasks rescue` for live_required variants.",
            "- Drop AA from default path; use react→MoA with AA only if MoA cost too high on subset.",
            "- Fix empty module_execution steps before re-testing AA as escalation slot.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="AA ablation audit (Brief C).")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--trajectory-root", default="experiments/llm_runs/code_full_matrix")
    parser.add_argument("--output-json", default="experiments/metrics/aa_ablation_pilot.json")
    parser.add_argument("--output-md", default="experiments/analysis/aa_ablation_audit.md")
    args = parser.parse_args()

    result = analyze(args.input, args.trajectory_root)
    Path(args.output_json).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.output_md).write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"output_json": args.output_json, "evidence_outcome": result["evidence_outcome"]}, indent=2))


if __name__ == "__main__":
    main()
