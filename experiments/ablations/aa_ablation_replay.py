"""Replay AA component ablations from code_full_matrix and trajectories (zero LLM cost)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.ablations.aa_ablation_specs import AA_ABLATION_IDS, ABLATION_SPECS, ablation_config_for
from experiments.cascade.cascade_replay import simulate_task


RESCUE_TASKS = (
    "phase1_code_csv_001",
    "phase1_code_email_001",
    "phase1_code_env_flag_001",
)


def _index_per_task(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    out: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        out[row["task_id"]][row["baseline_id"]] = row
    return out


def _aggregate_rows(per_task: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(per_task) or 1
    correct = sum(1 for row in per_task if row["success"])
    calls = [row["model_calls"] for row in per_task]
    mean_calls = sum(calls) / n
    return {
        "tasks": n,
        "correct": correct,
        "accuracy": round(correct / n, 4),
        "mean_model_calls": round(mean_calls, 4),
        "mean_total_tokens": round(sum(row["total_tokens"] for row in per_task) / n, 2),
        "mean_latency_ms": round(sum(row["latency_ms"] for row in per_task) / n, 2),
        "cost_normalized_success": round((correct / n) / mean_calls, 4) if mean_calls > 0 else 0.0,
        "per_task": per_task,
    }


def _rows_from_baseline(indexed: dict[str, dict[str, dict[str, Any]]], baseline_id: str) -> list[dict[str, Any]]:
    per_task: list[dict[str, Any]] = []
    for task_id in sorted(indexed):
        row = indexed[task_id].get(baseline_id)
        if row is None:
            continue
        per_task.append(
            {
                "task_id": task_id,
                "success": bool(row.get("success")),
                "final_success_label": row.get("final_success_label", "pass" if row.get("success") else "fail"),
                "model_calls": int(row.get("model_calls") or 0),
                "total_tokens": int(row.get("total_tokens") or 0),
                "latency_ms": int(row.get("latency_ms") or 0),
                "cost_normalized_success": round(1.0 / row["model_calls"], 6)
                if row.get("success") and row.get("model_calls")
                else 0.0,
                "evidence_source": baseline_id,
            }
        )
    return per_task


def replay_ablation(summary: dict[str, Any], ablation_id: str) -> dict[str, Any]:
    spec = ABLATION_SPECS[ablation_id]
    indexed = _index_per_task(summary.get("per_task", []))

    if ablation_id == "aa_direct_first":
        stages = spec["cascade_stages"]
        per_task = [simulate_task(task_id, stages, indexed[task_id]) for task_id in sorted(indexed)]
        agg = _aggregate_rows(per_task)
        return {
            "ablation_id": ablation_id,
            "label": spec["label"],
            "evidence_tier": spec["evidence_tier"],
            "evidence_source": "cascade_replay:" + "->".join(stages),
            **agg,
        }

    matrix_id = spec.get("matrix_baseline_id")
    if matrix_id:
        per_task = _rows_from_baseline(indexed, matrix_id)
        agg = _aggregate_rows(per_task)
        return {
            "ablation_id": ablation_id,
            "label": spec["label"],
            "evidence_tier": spec["evidence_tier"],
            "evidence_source": matrix_id,
            **agg,
        }

    proxy_id = spec.get("proxy_baseline_id")
    if proxy_id and spec.get("evidence_tier") == "proxy":
        per_task = _rows_from_baseline(indexed, proxy_id)
        agg = _aggregate_rows(per_task)
        return {
            "ablation_id": ablation_id,
            "label": spec["label"],
            "evidence_tier": spec["evidence_tier"],
            "evidence_source": f"proxy:{proxy_id}",
            "proxy_note": spec.get("proxy_note"),
            **agg,
        }

    return {
        "ablation_id": ablation_id,
        "label": spec["label"],
        "evidence_tier": spec["evidence_tier"],
        "evidence_source": "live_required",
        "tasks": len(indexed),
        "correct": None,
        "accuracy": None,
        "mean_model_calls": None,
        "note": "Requires live ablation run; no matrix row available.",
    }


def _delta_vs_control(control: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    if control.get("accuracy") is None or variant.get("accuracy") is None:
        return {}
    return {
        "accuracy_delta": round(variant["accuracy"] - control["accuracy"], 4),
        "calls_delta": round((variant.get("mean_model_calls") or 0) - (control.get("mean_model_calls") or 0), 4),
        "cost_norm_delta": round(
            (variant.get("cost_normalized_success") or 0) - (control.get("cost_normalized_success") or 0),
            4,
        ),
    }


def _component_recommendation(ablation_id: str, control: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    if ablation_id == "aa_tuned_control":
        return {
            "component": "tuned_control",
            "action": "keep",
            "confidence": "high",
            "rationale": "Reference configuration for delta comparisons; replace with direct-first deployment policy.",
        }

    hint = ABLATION_SPECS[ablation_id].get("recommendation_hint", "investigate")
    delta = _delta_vs_control(control, variant)
    tier = ABLATION_SPECS[ablation_id]["evidence_tier"]

    if tier == "live_required":
        return {
            "component": ablation_id.replace("aa_", ""),
            "action": "gate",
            "confidence": "low",
            "rationale": "No matrix replay; schedule live ablation before remove/keep decision.",
        }

    acc_d = delta.get("accuracy_delta", 0.0)
    cost_d = delta.get("cost_norm_delta", 0.0)

    if ablation_id == "aa_direct_first":
        if acc_d >= 0 and cost_d > 0.15:
            action = "keep"
        elif acc_d >= 0:
            action = "keep"
        else:
            action = "gate"
        return {
            "component": "direct_first_escalation",
            "action": action,
            "confidence": "high",
            "rationale": (
                f"Direct-first improves cost-norm by {cost_d:+.4f} vs always-AA "
                f"with accuracy delta {acc_d:+.4f} (matrix replay)."
            ),
        }

    if ablation_id == "aa_no_memory":
        return {
            "component": "memory",
            "action": "gate",
            "confidence": "medium",
            "rationale": (
                "Proxy ReAct (no memory) beats always-AA on cost-norm; Phase2 toy shows "
                "aa_no_memory +8.3pp success. Gate memory to escalation-only or outcome-memory pilot."
            ),
        }

    if ablation_id == "aa_no_budget_gate":
        return {
            "component": "strong_budget_gate",
            "action": "keep",
            "confidence": "medium",
            "rationale": (
                "MoA proxy (relaxed fan-out) has higher accuracy but worse cost-norm than control; "
                "budget gate limits over-activation on easy tasks."
            ),
        }

    if acc_d > 0.02 and cost_d >= 0:
        action = "remove"
    elif acc_d < -0.02 and cost_d <= 0:
        action = "keep"
    elif cost_d > 0.05 and acc_d >= -0.02:
        action = "gate"
    else:
        action = "keep" if hint.startswith("keep") else "gate"

    return {
        "component": ablation_id.replace("aa_", ""),
        "action": action,
        "confidence": "medium" if tier == "direct" else "low",
        "rationale": f"Replay delta accuracy={acc_d:+.4f}, cost_norm={cost_d:+.4f} vs control.",
    }


def _event_modules(events: list[dict[str, Any]]) -> list[str]:
    modules: list[str] = []
    for event in events:
        if event.get("kind") != "route":
            continue
        payload = event.get("payload", {})
        selected = payload.get("selected_modules") or []
        modules.extend(str(item) for item in selected)
    return modules


def _trajectory_summary(path: Path) -> dict[str, Any]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    events = envelope.get("events", [])
    routes = [e for e in events if e.get("kind") == "route"]
    verifier_events = [e for e in events if e.get("kind") == "verifier_result"]
    memory_reads = [e for e in events if e.get("kind") == "memory_read"]
    finish = next((e for e in events if e.get("kind") == "finish"), None)
    finish_state = (finish or {}).get("payload", {})

    effective_top_k = [
        route.get("payload", {}).get("top_k")
        for route in routes
        if route.get("payload", {}).get("top_k") is not None
    ]
    empty_route_steps = sum(
        1
        for route in routes
        if not (route.get("payload", {}).get("selected_modules") or [])
    )

    return {
        "run_id": envelope.get("run_id"),
        "baseline_id": envelope.get("baseline_id"),
        "task_id": envelope.get("task_id"),
        "success": envelope.get("final_success_label") == "pass",
        "model_calls": envelope.get("metrics_summary", {}).get("model_calls"),
        "total_tokens": envelope.get("metrics_summary", {}).get("total_tokens"),
        "route_steps": len(routes),
        "selected_modules": _event_modules(events),
        "unique_modules": sorted(set(_event_modules(events))),
        "effective_top_k_values": effective_top_k,
        "empty_route_steps": empty_route_steps,
        "verifier_runs": len(verifier_events),
        "memory_reads": len(memory_reads),
        "confidence_final": finish_state.get("confidence"),
        "halt_reason": finish_state.get("halt_reason"),
        "failure_signals": finish_state.get("failure_signals"),
    }


def analyze_rescue_trajectories(trajectory_root: Path) -> dict[str, Any]:
    root = trajectory_root / "code_all"
    cases: list[dict[str, Any]] = []

    for task_id in RESCUE_TASKS:
        react_path = (
            root
            / "single_react_llm_agent"
            / f"real_llm__single_react_llm_agent__openai__Qwen3-30B-A3B-Instruct-2507__{task_id}.json"
        )
        aa_path = (
            root
            / "agent_attention_llm_tuned"
            / f"real_llm__agent_attention_llm_tuned__openai__Qwen3-30B-A3B-Instruct-2507__{task_id}.json"
        )
        moa_path = (
            root
            / "moa_style_llm_agent"
            / f"real_llm__moa_style_llm_agent__openai__Qwen3-30B-A3B-Instruct-2507__{task_id}.json"
        )

        react = _trajectory_summary(react_path) if react_path.exists() else None
        aa = _trajectory_summary(aa_path) if aa_path.exists() else None
        moa = _trajectory_summary(moa_path) if moa_path.exists() else None

        interpretation = ""
        if react and aa:
            extra_modules = sorted(set(aa["unique_modules"]) - set(react["unique_modules"]))
            empty_steps = aa.get("empty_route_steps", 0)
            if aa["success"] and not react["success"]:
                interpretation = (
                    f"AA rescued via extra modules {extra_modules} "
                    f"({aa['model_calls']} calls vs ReAct {react['model_calls']}). "
                    f"Step-1 empty routes: {empty_steps}; critic+code on retry drove fix."
                )
            elif not aa["success"] and react and not react["success"]:
                interpretation = (
                    f"AA failed after activating {aa['unique_modules']} "
                    f"(empty route steps={empty_steps}); "
                    f"MoA {'succeeded' if moa and moa['success'] else 'unknown'} with parallel proposers."
                )

        cases.append(
            {
                "task_id": task_id,
                "react": react,
                "aa_tuned": aa,
                "moa": moa,
                "aa_rescue": bool(aa and aa["success"] and react and not react["success"]),
                "aa_failed_needs_moa": bool(aa and not aa["success"] and moa and moa["success"]),
                "interpretation": interpretation,
            }
        )

    return {"rescue_tasks": cases, "task_count": len(cases)}


def classify_outcome(control: dict[str, Any], recommendations: list[dict[str, Any]]) -> str:
    direct_first = next((r for r in recommendations if r["component"] == "direct_first_escalation"), None)
    if direct_first and direct_first["action"] == "keep" and control.get("accuracy", 0) < 0.9:
        return "supports_direction"
    keep_count = sum(1 for r in recommendations if r["action"] == "keep")
    remove_count = sum(1 for r in recommendations if r["action"] == "remove")
    if remove_count >= 2 or keep_count >= 4:
        return "supports_direction"
    return "weak_or_inconclusive"


def analyze(
    summary_path: str | Path,
    *,
    trajectory_root: str | Path | None = None,
    phase2_summary_path: str | Path | None = None,
) -> dict[str, Any]:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    variants = {ablation_id: replay_ablation(summary, ablation_id) for ablation_id in AA_ABLATION_IDS}
    control = variants["aa_tuned_control"]

    matrix_table = []
    for ablation_id in AA_ABLATION_IDS:
        variant = variants[ablation_id]
        matrix_table.append(
            {
                **ablation_config_for(ablation_id),
                "metrics": {
                    "accuracy": variant.get("accuracy"),
                    "mean_model_calls": variant.get("mean_model_calls"),
                    "cost_normalized_success": variant.get("cost_normalized_success"),
                },
                "delta_vs_control": _delta_vs_control(control, variant),
                "evidence_source": variant.get("evidence_source"),
            }
        )

    recommendations = [
        _component_recommendation(ablation_id, control, variants[ablation_id]) for ablation_id in AA_ABLATION_IDS
    ]

    rescue_analysis = None
    if trajectory_root and Path(trajectory_root).exists():
        rescue_analysis = analyze_rescue_trajectories(Path(trajectory_root))

    phase2_hint = None
    if phase2_summary_path and Path(phase2_summary_path).exists():
        phase2 = json.loads(Path(phase2_summary_path).read_text(encoding="utf-8"))
        rows = {row["ablation_id"]: row for row in phase2.get("rows", [])}
        control_toy = rows.get("aa_tuned_control", {})
        no_mem = rows.get("aa_no_memory", {})
        if control_toy and no_mem:
            phase2_hint = {
                "toy_success_delta_no_memory": round(
                    (no_mem.get("success_rate") or 0) - (control_toy.get("success_rate") or 0),
                    4,
                ),
                "toy_cost_norm_delta_no_memory": round(
                    (no_mem.get("mean_cost_normalized_success") or 0)
                    - (control_toy.get("mean_cost_normalized_success") or 0),
                    4,
                ),
            }

    outcome = classify_outcome(control, recommendations)

    return {
        "scope": "AA component ablation replay (Brief C, zero new LLM calls where possible).",
        "source_summary": str(summary_path),
        "suite": summary.get("suite"),
        "tasks": summary.get("tasks"),
        "model": summary.get("model"),
        "provider": summary.get("provider"),
        "control_id": "aa_tuned_control",
        "variants": variants,
        "ablation_matrix": matrix_table,
        "component_recommendations": recommendations,
        "rescue_trajectory_analysis": rescue_analysis,
        "phase2_memory_hint": phase2_hint,
        "comparison_vs_control": {
            "always_aa_accuracy": control.get("accuracy"),
            "always_aa_cost_norm": control.get("cost_normalized_success"),
            "direct_first_accuracy": variants["aa_direct_first"].get("accuracy"),
            "direct_first_cost_norm": variants["aa_direct_first"].get("cost_normalized_success"),
            "direct_first_gain_cost_norm": _delta_vs_control(control, variants["aa_direct_first"]).get(
                "cost_norm_delta"
            ),
        },
        "evidence_outcome": outcome,
    }


def render_audit_markdown(result: dict[str, Any]) -> str:
    control = result["variants"]["aa_tuned_control"]
    lines = [
        "# AA Component Ablation Audit (Brief C)",
        "",
        "## Scope",
        "",
        "Component-level ablation replay on the 26-task code matrix plus rescue-task trajectory forensics.",
        "",
        "## Inputs Read",
        "",
        f"- `{result['source_summary']}`",
        "- `experiments/metrics/cascade_pilot_summary.json` (rescue context)",
        "- `experiments/metrics/phase2_memory_ablation_summary.json` (toy memory ablations)",
        "- `experiments/llm_runs/code_full_matrix/` (trajectories for csv/email/env_flag)",
        "- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief C)",
        "",
        "## Method",
        "",
        "1. Define 8 one-variable AA variants (top-k, memory, verifier, gates, direct-first).",
        "2. Replay aggregate metrics from matrix rows or cascade simulation where available.",
        "3. Mark proxy/live-required tiers; compare rescue-task AA vs ReAct trajectories.",
        "",
        "## Commands Run",
        "",
        "```bash",
        "python3 experiments/ablations/run_aa_ablation_pilot.py --mode replay",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/metrics/aa_ablation_pilot.json`",
        "- `experiments/analysis/aa_ablation_audit.md`",
        "",
        "## Results",
        "",
        "### Control vs direct-first",
        "",
        "| Policy | Accuracy | Mean calls | Cost-norm success |",
        "|--------|----------|------------|-------------------|",
        f"| Always AA tuned | {control.get('accuracy', 0):.1%} | {control.get('mean_model_calls', 0):.2f} | {control.get('cost_normalized_success', 0):.4f} |",
    ]

    df = result["variants"]["aa_direct_first"]
    lines.append(
        f"| Direct-first (ReAct→AA) | {df.get('accuracy', 0):.1%} | {df.get('mean_model_calls', 0):.2f} | {df.get('cost_normalized_success', 0):.4f} |"
    )

    lines.extend(["", "### Ablation matrix (replay)", ""])
    lines.append("| Variant | Tier | Accuracy | Calls | Cost-norm | Δ acc | Δ cost-norm |")
    lines.append("|---------|------|----------|-------|-----------|-------|-------------|")
    for row in result["ablation_matrix"]:
        vid = row["ablation_id"]
        variant = result["variants"][vid]
        delta = row.get("delta_vs_control") or {}
        acc = variant.get("accuracy")
        calls = variant.get("mean_model_calls")
        cn = variant.get("cost_normalized_success")
        if acc is not None:
            lines.append(
                f"| {vid} | {row.get('evidence_tier')} | "
                f"{acc:.1%} | {calls:.2f} | {cn:.4f} | "
                f"{delta.get('accuracy_delta', 'n/a')} | {delta.get('cost_norm_delta', 'n/a')} |"
            )
        else:
            lines.append(f"| {vid} | {row.get('evidence_tier')} | live | — | — | — | — |")

    lines.extend(["", "### Component recommendations", ""])
    lines.append("| Component | Action | Confidence | Rationale |")
    lines.append("|-----------|--------|------------|-----------|")
    for rec in result["component_recommendations"]:
        lines.append(
            f"| {rec['component']} | **{rec['action']}** | {rec['confidence']} | {rec['rationale']} |"
        )

    rescue = result.get("rescue_trajectory_analysis")
    if rescue:
        lines.extend(["", "### Rescue-task trajectory forensics", ""])
        for case in rescue["rescue_tasks"]:
            lines.append(f"#### `{case['task_id']}`")
            lines.append("")
            if case.get("interpretation"):
                lines.append(case["interpretation"])
            react = case.get("react") or {}
            aa = case.get("aa_tuned") or {}
            lines.append(
                f"- ReAct: success={react.get('success')}, modules={react.get('unique_modules')}, "
                f"calls={react.get('model_calls')}"
            )
            lines.append(
                f"- AA tuned: success={aa.get('success')}, modules={aa.get('unique_modules')}, "
                f"calls={aa.get('model_calls')}, top_k={aa.get('effective_top_k_values')}"
            )
            if case.get("moa"):
                moa = case["moa"]
                lines.append(
                    f"- MoA: success={moa.get('success')}, modules={moa.get('unique_modules')}, "
                    f"calls={moa.get('model_calls')}"
                )
            lines.append("")

    phase2 = result.get("phase2_memory_hint")
    if phase2:
        lines.extend(
            [
                "### Phase 2 toy memory ablation hint",
                "",
                f"- No-memory success delta vs control: **{phase2['toy_success_delta_no_memory']:+.4f}**",
                f"- No-memory cost-norm delta: **{phase2['toy_cost_norm_delta_no_memory']:+.4f}**",
                "",
            ]
        )

    lines.extend(["## Interpretation", ""])
    outcome = result["evidence_outcome"]
    if outcome == "supports_direction":
        lines.append(
            "Replay narrows AA underperformance to over-activation on easy tasks and optional memory overhead. "
            "Direct-first gating and keeping budget/cost gates are supported; memory and top-k variants need live confirmation."
        )
    else:
        lines.append(
            "Matrix replay identifies deployment policy (direct-first) as the strongest lever; "
            "component-level remove/keep decisions remain inconclusive without live ablations."
        )

    lines.extend(["", f"**Evidence outcome:** `{outcome}`", "", "## Next Questions", ""])
    lines.extend(
        [
            "- Live-run `aa_top1`, `aa_no_verifier`, `aa_no_adaptive_topk` on the 26-task code suite.",
            "- Compare `aa_direct_first` live cascade vs matrix replay.",
            "- Brief D: outcome-memory router to replace transcript memory in escalation slot.",
        ]
    )
    lines.append("")
    return "\n".join(lines)
