#!/usr/bin/env python3
"""Compare real-LLM evaluation summaries against toy Phase 1–4 baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FAITHFUL_TOY_TO_LLM = {
    "single_react_agent": "single_react_llm_agent",
    "fixed_workflow_agent": "fixed_workflow_llm_agent",
    "full_history_agent": "full_history_llm_agent",
    "retrieval_memory_agent": "retrieval_memory_llm_agent",
    "moa_style_agent": "moa_style_llm_agent",
    "agent_attention_agent": "agent_attention_llm_agent",
    "agent_attention_agent_tuned": "agent_attention_llm_tuned",
}

MEMORY_TOY_TO_LLM = {k: f"{k}_llm" for k in [
    "aa_tuned_control", "aa_no_memory", "aa_memory_read_only",
    "aa_success_only_memory_write", "aa_unfiltered_memory", "aa_quarantine_aware",
]}

ROUTER_TOY_TO_LLM = {k: f"{k}_llm" for k in [
    "aa_lexical_router", "aa_rule_router", "aa_learned_router_replay", "aa_oracle_router",
]}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rate_from_real_baseline(row: dict[str, Any]) -> dict[str, float | None]:
    runs = row.get("runs", 0)
    if not runs:
        return {"success_rate": None, "partial_rate": None, "pass_rate": None}
    correct = row.get("correct", 0)
    partial = row.get("partial_rate", 0)
    if partial is None:
        partial = 0
    return {
        "success_rate": round(correct / runs, 4),
        "partial_rate": round(partial, 4) if isinstance(partial, float) else partial,
        "pass_rate": round(correct / runs, 4),
        "mean_model_calls": row.get("mean_model_calls"),
        "mean_latency_ms": row.get("mean_latency_ms"),
    }


def compare_faithful(real_summary: dict[str, Any], toy_summary: dict[str, Any]) -> list[dict[str, Any]]:
    toy_by_id = {row["baseline_id"]: row for row in toy_summary.get("rows", [])}
    tuned_toy = load_json(ROOT / "experiments/metrics/phase1_tuned_comparison_summary.json")
    for key in ("default", "tuned"):
        variant = tuned_toy.get("variants", {}).get(key, {})
        if variant.get("baseline_id"):
            toy_by_id[variant["baseline_id"]] = variant

    rows: list[dict[str, Any]] = []
    real_baselines = real_summary.get("baselines", {})
    for toy_id, llm_id in FAITHFUL_TOY_TO_LLM.items():
        toy = toy_by_id.get(toy_id, {})
        real = real_baselines.get(llm_id, {})
        real_metrics = rate_from_real_baseline(real)
        rows.append(
            {
                "toy_baseline_id": toy_id,
                "real_baseline_id": llm_id,
                "toy_success_rate": toy.get("success_rate"),
                "real_pass_rate": real_metrics["pass_rate"],
                "real_partial_rate": real_metrics["partial_rate"],
                "delta_pass_vs_toy": (
                    round(real_metrics["pass_rate"] - toy.get("success_rate", 0), 4)
                    if real_metrics["pass_rate"] is not None and toy.get("success_rate") is not None
                    else None
                ),
                "toy_mean_module_calls": toy.get("mean_module_calls"),
                "real_mean_model_calls": real_metrics["mean_model_calls"],
                "real_mean_latency_ms": real_metrics["mean_latency_ms"],
                "toy_mean_proxy_regret": toy.get("mean_proxy_route_regret"),
            }
        )
    return rows


def compare_ablation(real_summary: dict[str, Any], toy_summary: dict[str, Any]) -> list[dict[str, Any]]:
    toy_by_id = {row["ablation_id"]: row for row in toy_summary.get("rows", [])}
    rows: list[dict[str, Any]] = []
    for toy_id, llm_id in MEMORY_TOY_TO_LLM.items():
        toy = toy_by_id.get(toy_id, {})
        real = real_summary.get("baselines", {}).get(llm_id, {})
        real_metrics = rate_from_real_baseline(real)
        rows.append(
            {
                "toy_ablation_id": toy_id,
                "real_ablation_id": llm_id,
                "toy_success_rate": toy.get("success_rate"),
                "real_pass_rate": real_metrics["pass_rate"],
                "real_partial_rate": real_metrics["partial_rate"],
                "delta_pass_vs_toy": (
                    round(real_metrics["pass_rate"] - toy.get("success_rate", 0), 4)
                    if real_metrics["pass_rate"] is not None and toy.get("success_rate") is not None
                    else None
                ),
                "real_mean_model_calls": real_metrics["mean_model_calls"],
                "real_mean_latency_ms": real_metrics["mean_latency_ms"],
            }
        )
    return rows


def compare_router(real_summary: dict[str, Any], toy_summary: dict[str, Any]) -> list[dict[str, Any]]:
    toy_by_id = {row["router_id"]: row for row in toy_summary.get("rows", [])}
    rows: list[dict[str, Any]] = []
    for toy_id, llm_id in ROUTER_TOY_TO_LLM.items():
        toy = toy_by_id.get(toy_id, {})
        real = real_summary.get("baselines", {}).get(llm_id, {})
        real_metrics = rate_from_real_baseline(real)
        rows.append(
            {
                "toy_router_id": toy_id,
                "real_router_id": llm_id,
                "toy_success_rate": toy.get("success_rate"),
                "real_pass_rate": real_metrics["pass_rate"],
                "real_partial_rate": real_metrics["partial_rate"],
                "delta_pass_vs_toy": (
                    round(real_metrics["pass_rate"] - toy.get("success_rate", 0), 4)
                    if real_metrics["pass_rate"] is not None and toy.get("success_rate") is not None
                    else None
                ),
                "toy_oracle_regret": toy.get("mean_oracle_route_regret"),
                "real_mean_model_calls": real_metrics["mean_model_calls"],
                "real_mean_latency_ms": real_metrics["mean_latency_ms"],
            }
        )
    return rows


def compare_gsm8k(real_summary: dict[str, Any], toy_tuned: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    real_baselines = real_summary.get("baselines", {})
    multi = load_json(ROOT / "experiments/metrics/gsm8k_multi_baseline_full_summary.json")
    for llm_id in real_baselines:
        real = real_baselines[llm_id]
        multi_row = multi.get("baselines", {}).get(llm_id.replace("_llm_agent", "_agent").replace("llm_", "llm_"), {})
        if llm_id in multi.get("baselines", {}):
            multi_row = multi["baselines"][llm_id]
        real_metrics = rate_from_real_baseline(real)
        rows.append(
            {
                "real_baseline_id": llm_id,
                "gsm8k_pass_rate": real_metrics["pass_rate"],
                "mean_model_calls": real_metrics["mean_model_calls"],
                "mean_latency_ms": real_metrics["mean_latency_ms"],
            }
        )
    direct = multi.get("baselines", {}).get("llm_direct_agent", {})
    if direct:
        rows.insert(
            0,
            {
                "real_baseline_id": "llm_direct_agent (reference)",
                "gsm8k_pass_rate": direct.get("accuracy"),
                "mean_model_calls": direct.get("mean_model_calls"),
                "mean_latency_ms": direct.get("mean_latency_ms"),
                "note": "from gsm8k_multi_baseline_full_summary",
            },
        )
    rows.append(
        {
            "toy_baseline_id": "agent_attention_agent_tuned (phase1 toy)",
            "gsm8k_pass_rate": None,
            "toy_phase1_success_rate": toy_tuned.get("rows", [{}])[1].get("success_rate")
            if len(toy_tuned.get("rows", [])) > 1
            else None,
            "note": "GSM8K exact-match vs phase1 route-oracle are not directly comparable",
        }
    )
    return rows


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Real LLM vs Toy Runtime Comparison",
        "",
        f"Generated from real-LLM full runs. Model: `{report.get('model', 'unknown')}`.",
        "",
        "## Phase1 Faithful (12 tasks, route-proxy for real LLM)",
        "",
        "| Toy Baseline | Real LLM | Toy Success | Real Pass | Real Partial | Δ Pass | Real Calls |",
        "|--------------|----------|-------------|-----------|--------------|--------|------------|",
    ]
    for row in report.get("phase1_faithful", []):
        lines.append(
            f"| {row['toy_baseline_id']} | {row['real_baseline_id']} | "
            f"{_pct(row.get('toy_success_rate'))} | {_pct(row.get('real_pass_rate'))} | "
            f"{_pct(row.get('real_partial_rate'))} | {_delta(row.get('delta_pass_vs_toy'))} | "
            f"{row.get('real_mean_model_calls', '-')} |"
        )

    lines.extend(["", "## Phase1 Memory Ablations", ""])
    lines.append("| Toy Ablation | Real LLM | Toy Success | Real Pass | Real Partial | Δ Pass |")
    lines.append("|--------------|----------|-------------|-----------|--------------|--------|")
    for row in report.get("phase1_memory", []):
        lines.append(
            f"| {row['toy_ablation_id']} | {row['real_ablation_id']} | "
            f"{_pct(row.get('toy_success_rate'))} | {_pct(row.get('real_pass_rate'))} | "
            f"{_pct(row.get('real_partial_rate'))} | {_delta(row.get('delta_pass_vs_toy'))} |"
        )

    lines.extend(["", "## Phase1 Router Variants", ""])
    lines.append("| Toy Router | Real LLM | Toy Success | Real Pass | Real Partial | Δ Pass |")
    lines.append("|------------|----------|-------------|-----------|--------------|--------|")
    for row in report.get("phase1_router", []):
        lines.append(
            f"| {row['toy_router_id']} | {row['real_router_id']} | "
            f"{_pct(row.get('toy_success_rate'))} | {_pct(row.get('real_pass_rate'))} | "
            f"{_pct(row.get('real_partial_rate'))} | {_delta(row.get('delta_pass_vs_toy'))} |"
        )

    lines.extend(["", "## GSM8K Faithful (20 tasks, exact-match)", ""])
    lines.append("| Baseline | Pass Rate | Mean Calls | Mean Latency |")
    lines.append("|----------|-----------|------------|--------------|")
    for row in report.get("gsm8k_faithful", []):
        if "real_baseline_id" in row:
            lines.append(
                f"| {row['real_baseline_id']} | {_pct(row.get('gsm8k_pass_rate'))} | "
                f"{row.get('mean_model_calls', '-')} | {row.get('mean_latency_ms', '-')} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **Toy** success = route-oracle on deterministic executors.",
            "- **Real LLM Phase1** pass/partial = same route-oracle on real module outputs.",
            "- **Real LLM GSM8K** = exact numeric match (end-task).",
            "- Large positive Δ on MoA/AA-default may reflect real LLM helping routing complete; large negative Δ on ReAct may reflect verifier/gate differences under latency.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.1f}%"


def _delta(value: Any) -> str:
    if value is None:
        return "—"
    sign = "+" if float(value) >= 0 else ""
    return f"{sign}{float(value) * 100:.1f}pp"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default="experiments/metrics/real_vs_toy_comparison.json")
    parser.add_argument("--output-md", default="docs/deliverables/08/result_table_real_vs_toy.md")
    args = parser.parse_args()

    paths = {
        "phase1_faithful": ROOT / "experiments/metrics/real_llm_phase1_faithful_full.json",
        "phase1_memory": ROOT / "experiments/metrics/real_llm_phase1_memory_full.json",
        "phase1_router": ROOT / "experiments/metrics/real_llm_phase1_router_full.json",
        "gsm8k_faithful": ROOT / "experiments/metrics/real_llm_gsm8k_faithful_full.json",
    }
    toy_faithful = load_json(ROOT / "experiments/metrics/phase1_faithful_matrix_by_baseline.json")
    toy_memory = load_json(ROOT / "experiments/metrics/phase2_memory_ablation_summary.json")
    toy_router = load_json(ROOT / "experiments/metrics/phase4_learned_routing_summary.json")
    toy_tuned = load_json(ROOT / "experiments/metrics/phase1_tuned_comparison_summary.json")

    report: dict[str, Any] = {"model": "Qwen3-30B-A3B-Instruct-2507", "provider": "openai/paratera"}
    if paths["phase1_faithful"].exists():
        real = load_json(paths["phase1_faithful"])
        report["model"] = real.get("model", report["model"])
        report["phase1_faithful"] = compare_faithful(real, toy_faithful)
    if paths["phase1_memory"].exists():
        report["phase1_memory"] = compare_ablation(load_json(paths["phase1_memory"]), toy_memory)
    if paths["phase1_router"].exists():
        report["phase1_router"] = compare_router(load_json(paths["phase1_router"]), toy_router)
    if paths["gsm8k_faithful"].exists():
        report["gsm8k_faithful"] = compare_gsm8k(load_json(paths["gsm8k_faithful"]), toy_tuned)

    out_json = ROOT / args.output_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(report, ROOT / args.output_md)
    print(json.dumps({"json": str(out_json), "markdown": args.output_md}, indent=2))


if __name__ == "__main__":
    main()
