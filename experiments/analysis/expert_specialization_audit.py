#!/usr/bin/env python3
"""Expert Specialization Auditor (Brief H / Objective 5)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from experiments.real_benchmarks.code_verifier import strip_file_hint, verify_code_task


FOCUS_BASELINES = ("agent_attention_llm_tuned", "moa_style_llm_agent")
PROPOSER_MODULES = ("code_agent", "critic_agent", "search_agent", "aggregator")
TRAJECTORY_ROOT = Path("experiments/llm_runs/code_full_matrix/code_all")


def event_kind(event: dict[str, Any]) -> str:
    return str(event.get("kind") or event.get("event_type") or "")


def task_family(task_id: str, trajectory: dict[str, Any]) -> str:
    explicit = trajectory.get("task_family")
    if explicit:
        return str(explicit)
    if task_id.startswith("phase0_seed"):
        return "phase0_seed"
    if task_id.startswith("phase1_code_"):
        suffix = task_id.removeprefix("phase1_code_").removesuffix("_001")
        return f"phase1_{suffix}"
    return "unknown"


def normalize_patch_body(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"```(?:python)?", "", text, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    cleaned = strip_file_hint(cleaned.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def patch_fingerprint(text: str) -> str:
    body = normalize_patch_body(text)
    if not body:
        return ""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def collect_module_outputs(events: list[dict[str, Any]]) -> dict[str, str]:
    """Latest non-empty output per module across trajectory."""
    outputs: dict[str, str] = {}
    for event in events:
        kind = event_kind(event)
        payload = event.get("payload") or {}
        if kind == "model_call":
            module_id = payload.get("module_id")
            output = payload.get("output")
            if module_id and output:
                outputs[str(module_id)] = str(output)
        elif kind == "module_execution":
            for item in payload.get("outputs") or []:
                if not isinstance(item, dict):
                    continue
                module_id = item.get("module_id")
                content = item.get("content")
                if module_id and content:
                    outputs[str(module_id)] = str(content)
    return outputs


def collect_route_selections(events: list[dict[str, Any]]) -> list[list[str]]:
    selections: list[list[str]] = []
    for event in events:
        if event_kind(event) != "route":
            continue
        payload = event.get("payload") or {}
        selected = payload.get("selected_modules") or []
        if selected:
            selections.append([str(m) for m in selected])
    return selections


def collect_disagreements(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pairwise proposer disagreements within each module_execution step."""
    cases: list[dict[str, Any]] = []
    for event in events:
        if event_kind(event) != "module_execution":
            continue
        payload = event.get("payload") or {}
        outputs = payload.get("outputs") or []
        proposers = [
            (str(o["module_id"]), str(o.get("content") or ""))
            for o in outputs
            if isinstance(o, dict) and o.get("module_id") in PROPOSER_MODULES and o.get("content")
        ]
        if len(proposers) < 2:
            continue
        fps = {mid: patch_fingerprint(content) for mid, content in proposers}
        unique_fps = set(fps.values())
        if len(unique_fps) <= 1:
            continue
        cases.append(
            {
                "event_id": event.get("event_id"),
                "step": event.get("step"),
                "modules": [mid for mid, _ in proposers],
                "fingerprints": fps,
            }
        )
    return cases


def verify_module_patch(task_id: str, content: str) -> bool:
    if not content.strip():
        return False
    return verify_code_task(task_id, content).passed


def analyze_trajectory(path: Path, summary_row: dict[str, Any] | None) -> dict[str, Any]:
    trajectory = json.loads(path.read_text(encoding="utf-8"))
    events = trajectory.get("events") or []
    task_id = trajectory["task_id"]
    baseline_id = trajectory["baseline_id"]
    family = task_family(task_id, trajectory)
    run_success = (
        trajectory.get("final_success_label") == "pass"
        or (summary_row or {}).get("success") is True
    )

    module_outputs = collect_module_outputs(events)
    route_selections = collect_route_selections(events)
    disagreements = collect_disagreements(events)

    selected_modules = list(trajectory.get("runtime_config", {}).get("selected_modules") or [])
    if not selected_modules:
        finish = next((e for e in events if event_kind(e) == "finish"), None)
        if finish:
            selected_modules = list((finish.get("payload") or {}).get("selected_modules") or [])

    per_module_verify: dict[str, bool] = {}
    for module_id, content in module_outputs.items():
        if module_id in PROPOSER_MODULES:
            per_module_verify[module_id] = verify_module_patch(task_id, content)

    empty_execution_steps = sum(
        1
        for e in events
        if event_kind(e) == "module_execution" and not (e.get("payload") or {}).get("outputs")
    )
    model_calls = [e for e in events if event_kind(e) == "model_call"]
    no_module_activated = any(
        "no_module_activated" in str((e.get("payload") or {}).get("state", {}).get("failure_signals", []))
        for e in events
        if event_kind(e) == "state_update"
    )

    redundant_signals: list[str] = []
    if empty_execution_steps:
        redundant_signals.append(f"empty_module_execution_steps={empty_execution_steps}")
    if no_module_activated:
        redundant_signals.append("no_module_activated_failure_signal")

    # Redundant proposer: both pass pytest but fingerprints differ (MoA pays 2x for overlapping fix)
    passing_proposers = [m for m, ok in per_module_verify.items() if ok]
    if len(passing_proposers) >= 2:
        fps = {m: patch_fingerprint(module_outputs[m]) for m in passing_proposers}
        if len(set(fps.values())) == 1:
            redundant_signals.append("duplicate_passing_proposer_patches")
        else:
            redundant_signals.append("multiple_distinct_passing_proposers")

    # Selected but never produced output
    for module_id in selected_modules:
        if module_id in PROPOSER_MODULES and module_id not in module_outputs:
            redundant_signals.append(f"selected_without_output:{module_id}")

    multi_proposer_steps = sum(
        1
        for e in events
        if event_kind(e) == "module_execution"
        and len(
            [
                o
                for o in (e.get("payload") or {}).get("outputs") or []
                if isinstance(o, dict)
                and o.get("module_id") in PROPOSER_MODULES
                and o.get("content")
            ]
        )
        >= 2
    )

    return {
        "run_id": trajectory.get("run_id"),
        "task_id": task_id,
        "task_family": family,
        "baseline_id": baseline_id,
        "run_success": run_success,
        "selected_modules": selected_modules,
        "route_selections": route_selections,
        "module_outputs_present": sorted(module_outputs.keys()),
        "per_module_pytest_pass": per_module_verify,
        "disagreements": disagreements,
        "disagreement_count": len(disagreements),
        "multi_proposer_steps": multi_proposer_steps,
        "redundant_signals": redundant_signals,
        "model_call_count": len(model_calls),
        "empty_module_execution_steps": empty_execution_steps,
    }


def build_specialization_table(
    per_run: list[dict[str, Any]], unique_rescues: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "activations": 0,
            "runs_with_output": 0,
            "pytest_pass_when_output": 0,
            "run_success_when_selected": 0,
            "task_families": Counter(),
            "failure_modes": Counter(),
        }
    )

    for run in per_run:
        baseline = run["baseline_id"]
        for module_id in run["selected_modules"]:
            key = f"{baseline}::{module_id}"
            stats[key]["activations"] += 1
            stats[key]["task_families"][run["task_family"]] += 1
            if run["run_success"]:
                stats[key]["run_success_when_selected"] += 1
            if module_id in run["per_module_pytest_pass"]:
                stats[key]["runs_with_output"] += 1
                if run["per_module_pytest_pass"][module_id]:
                    stats[key]["pytest_pass_when_output"] += 1
                else:
                    stats[key]["failure_modes"]["patch_fails_pytest"] += 1
            elif module_id in PROPOSER_MODULES:
                stats[key]["failure_modes"]["no_output"] += 1

    sole_rescue_counts: Counter[str] = Counter()
    for case in unique_rescues:
        sole_rescue_counts[f"{case['baseline_id']}::{case['sole_passing_module']}"] += 1

    rows: list[dict[str, Any]] = []
    for key in sorted(stats):
        baseline, module_id = key.split("::", 1)
        s = stats[key]
        activations = s["activations"]
        with_output = s["runs_with_output"]
        pytest_passes = s["pytest_pass_when_output"]
        sole_rescues = sole_rescue_counts.get(key, 0)
        rows.append(
            {
                "baseline_id": baseline,
                "module_id": module_id,
                "activations": activations,
                "runs_with_output": with_output,
                "pytest_pass_count": s["pytest_pass_when_output"],
                "pytest_pass_rate_given_output": round(
                    s["pytest_pass_when_output"] / with_output, 4
                )
                if with_output
                else None,
                "specialist_precision": round(s["run_success_when_selected"] / activations, 4)
                if activations
                else None,
                "specialist_recall": round(sole_rescues / pytest_passes, 4)
                if pytest_passes
                else None,
                "unique_rescue_count": sole_rescues,
                "success_by_task_family": dict(sorted(s["task_families"].items())),
                "failure_modes": dict(sorted(s["failure_modes"].items())),
            }
        )
    return rows


def unique_rescue_cases(per_run: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tasks where exactly one proposer module's patch passes pytest (within baseline)."""
    by_task_baseline: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in per_run:
        by_task_baseline[(run["task_id"], run["baseline_id"])].append(run)

    cases: list[dict[str, Any]] = []
    for (task_id, baseline_id), runs in sorted(by_task_baseline.items()):
        run = runs[0]
        passers = [m for m, ok in run["per_module_pytest_pass"].items() if ok]
        if len(passers) == 1:
            cases.append(
                {
                    "task_id": task_id,
                    "task_family": run["task_family"],
                    "baseline_id": baseline_id,
                    "sole_passing_module": passers[0],
                    "run_success": run["run_success"],
                    "other_modules": {
                        m: run["per_module_pytest_pass"].get(m)
                        for m in run["per_module_pytest_pass"]
                        if m != passers[0]
                    },
                }
            )
    return cases


def cross_baseline_rescue(per_run: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Module uniquely solves task across both baselines' proposer outputs."""
    by_task: dict[str, dict[str, dict[str, bool]]] = defaultdict(lambda: defaultdict(dict))
    for run in per_run:
        for module_id, passed in run["per_module_pytest_pass"].items():
            by_task[run["task_id"]][module_id][run["baseline_id"]] = passed

    cases: list[dict[str, Any]] = []
    for task_id, module_results in sorted(by_task.items()):
        for module_id, baseline_pass in sorted(module_results.items()):
            if sum(1 for v in baseline_pass.values() if v) >= 1:
                others_fail = all(
                    not any(
                        mod != module_id and results.get(bid) is True
                        for mod, results in module_results.items()
                        for bid in results
                    )
                    for _ in [0]
                )
                # sole module that ever passes on this task
                all_passers = [m for m, res in module_results.items() if any(res.values())]
                if len(all_passers) == 1 and all_passers[0] == module_id:
                    cases.append(
                        {
                            "task_id": task_id,
                            "sole_passing_module": module_id,
                            "baseline_results": baseline_pass,
                        }
                    )
    return cases


def classify_outcome(
    *,
    specialization_table: list[dict[str, Any]],
    unique_rescues: list[dict[str, Any]],
    disagreement_rate: float,
    redundant_activation_rate: float,
    search_agent_activations: int,
) -> str:
    proposer_rows = [r for r in specialization_table if r["module_id"] in PROPOSER_MODULES]
    if not proposer_rows:
        return "weak_or_inconclusive"

    pass_rates = [r["pytest_pass_rate_given_output"] for r in proposer_rows if r["pytest_pass_rate_given_output"] is not None]
    spread = (max(pass_rates) - min(pass_rates)) if len(pass_rates) >= 2 else 0.0

    # Strong specialization: distinct pass rates, meaningful unique rescues, low redundancy
    if (
        unique_rescues
        and spread >= 0.08
        and disagreement_rate >= 0.15
        and redundant_activation_rate < 0.5
        and search_agent_activations > 0
    ):
        return "supports_direction"

    # Weak modules / redundant prompts block routing
    if (
        redundant_activation_rate >= 0.35
        or (spread < 0.05 and len(unique_rescues) <= 1)
        or search_agent_activations == 0
    ):
        return "falsified_or_blocked"

    return "weak_or_inconclusive"


def render_markdown(result: dict[str, Any]) -> str:
    agg = result["aggregate"]
    lines = [
        "# Expert Specialization Audit (Brief H)",
        "",
        "## Scope",
        "",
        "Expert Specialization Auditor on 26-task code matrix trajectories for "
        "`agent_attention_llm_tuned` and `moa_style_llm_agent` (52 runs, no new LLM calls).",
        "",
        "## Inputs Read",
        "",
        "- `experiments/metrics/code_full_matrix_summary.json`",
        "- `experiments/llm_runs/code_full_matrix/` (AA + MoA trajectories)",
        "- `docs/next_iteration/research_directions/03_objectives_and_metrics.md` (Objective 5)",
        "- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief H)",
        "",
        "## Method",
        "",
        "- Parse trajectory events: `route.selected_modules`, `module_execution.outputs`, `model_call` payloads.",
        "- Normalize proposer patch bodies; fingerprint for disagreement detection.",
        "- Independently pytest-verify each proposer module output via `verify_code_task`.",
        "- Compute specialist precision (run success | module selected), pytest pass rate given output, "
        "disagreement rate (multi-proposer steps with distinct fingerprints), redundant activation signals.",
        "",
        "## Commands Run",
        "",
        "```bash",
        "PYTHONPATH=. python3 experiments/analysis/expert_specialization_audit.py",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/analysis/expert_specialization_audit.json`",
        "- `experiments/analysis/expert_specialization_audit.md`",
        "",
        "## Results",
        "",
        "### Aggregate (Objective 5)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Runs analyzed | {agg['runs_analyzed']} |",
        f"| Disagreement rate (multi-proposer steps) | {agg['disagreement_rate']:.1%} ({agg['disagreement_steps']}/{agg['multi_proposer_steps']}) |",
        f"| Redundant activation rate | {agg['redundant_activation_rate']:.1%} ({agg['runs_with_redundant_signals']}/{agg['runs_analyzed']}) |",
        f"| Unique rescue cases (sole passing proposer) | {agg['unique_rescue_count']} |",
        f"| Cross-baseline sole-module rescues | {agg['cross_baseline_sole_rescue_count']} |",
        f"| search_agent activations | {agg['search_agent_activations']} |",
        f"| code_agent vs critic_agent pass-rate spread | {agg['code_critic_pass_rate_spread']:.1%} |",
        "",
        "### Module specialization table",
        "",
        "| Baseline | Module | Activations | Pytest pass (given output) | Specialist precision |",
        "|----------|--------|-------------|------------------------------|----------------------|",
    ]
    for row in result["module_specialization_table"]:
        ppr = row["pytest_pass_rate_given_output"]
        ppr_s = f"{ppr:.1%}" if ppr is not None else "n/a"
        sp = row["specialist_precision"]
        sp_s = f"{sp:.1%}" if sp is not None else "n/a"
        lines.append(
            f"| {row['baseline_id']} | {row['module_id']} | {row['activations']} | "
            f"{row['pytest_pass_count']}/{row['runs_with_output']} ({ppr_s}) | {sp_s} |"
        )

    lines.extend(["", "### Unique rescue cases (sole passing proposer within run)", ""])
    if result["unique_rescue_cases"]:
        for case in result["unique_rescue_cases"]:
            lines.append(
                f"- `{case['task_id']}` ({case['baseline_id']}): only `{case['sole_passing_module']}` "
                f"patch passes pytest; run_success={case['run_success']}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "### Redundant activation signals (sample)", ""])
    for item in result["redundant_activation_examples"][:8]:
        lines.append(f"- `{item['task_id']}` ({item['baseline_id']}): {', '.join(item['redundant_signals'])}")

    lines.extend(
        [
            "",
            "### Stronger specialist definitions (proposal)",
            "",
        ]
    )
    for item in result["specialist_proposals"]:
        lines.append(f"- {item}")

    outcome = agg["evidence_outcome"]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ]
    )
    if outcome == "supports_direction":
        lines.append(
            "Proposer modules show measurable specialization: distinct pass rates, disagreements that matter, "
            "and unique rescues. Sparse routing can leverage differentiated experts after prompt/tool hardening."
        )
    elif outcome == "weak_or_inconclusive":
        lines.append(
            "Some disagreement exists but modules largely overlap (same model, similar patches). "
            "Routing cannot win until specialists diverge—especially search_agent (never activated) and "
            "AA empty-execution routing bugs."
        )
    else:
        lines.append(
            "Modules behave as redundant prompts: high redundant activation, minimal pass-rate spread, "
            "search_agent unused. Redesign specialists before investing in learned routing."
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
    if outcome == "falsified_or_blocked":
        lines.extend(
            [
                "- Brief C: fix AA `no_module_activated` / empty module_execution before re-auditing.",
                "- Replace label-only prompts with tool-scoped roles (critic gets failing patch only; search gets retrieval tool).",
                "- Re-run Brief H after search_agent is routable on evidence-heavy tasks.",
            ]
        )
    elif outcome == "weak_or_inconclusive":
        lines.extend(
            [
                "- Ablate critic_agent on MoA: does accuracy drop when code_agent alone is sufficient?",
                "- Add task families that require search (API docs) to test search_agent specialization.",
                "- Brief B cascade: use MoA only when proposer disagreement + both patches fail pytest.",
            ]
        )
    else:
        lines.extend(
            [
                "- Train router on proposer pass-rate features from this audit.",
                "- Brief E: predict which proposer patch will pass pytest from task metadata.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brief H expert specialization audit.")
    parser.add_argument("--summary", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--output-json", default="experiments/analysis/expert_specialization_audit.json")
    parser.add_argument("--output-md", default="experiments/analysis/expert_specialization_audit.md")
    args = parser.parse_args()

    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    summary_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in summary.get("per_task", []):
        if row["baseline_id"] in FOCUS_BASELINES:
            summary_index[(row["baseline_id"], row["task_id"])] = row

    per_run: list[dict[str, Any]] = []
    for baseline in FOCUS_BASELINES:
        baseline_dir = TRAJECTORY_ROOT / baseline
        for path in sorted(baseline_dir.glob("*.json")):
            key = (baseline, json.loads(path.read_text(encoding="utf-8"))["task_id"])
            per_run.append(analyze_trajectory(path, summary_index.get(key)))

    unique_rescues = unique_rescue_cases(per_run)
    specialization_table = build_specialization_table(per_run, unique_rescues)
    cross_rescues = cross_baseline_rescue(per_run)

    multi_proposer_steps = sum(run["multi_proposer_steps"] for run in per_run)
    disagreement_steps = sum(run["disagreement_count"] for run in per_run)
    runs_with_redundant = sum(1 for run in per_run if run["redundant_signals"])
    search_activations = sum(
        1 for run in per_run for m in run["selected_modules"] if m == "search_agent"
    )

    code_rates = [
        r["pytest_pass_rate_given_output"]
        for r in specialization_table
        if r["module_id"] == "code_agent" and r["pytest_pass_rate_given_output"] is not None
    ]
    critic_rates = [
        r["pytest_pass_rate_given_output"]
        for r in specialization_table
        if r["module_id"] == "critic_agent" and r["pytest_pass_rate_given_output"] is not None
    ]
    spread = 0.0
    if code_rates and critic_rates:
        spread = abs(sum(code_rates) / len(code_rates) - sum(critic_rates) / len(critic_rates))

    redundant_rate = runs_with_redundant / len(per_run) if per_run else 0.0
    disagreement_rate = disagreement_steps / multi_proposer_steps if multi_proposer_steps else 0.0

    outcome = classify_outcome(
        specialization_table=specialization_table,
        unique_rescues=unique_rescues,
        disagreement_rate=disagreement_rate,
        redundant_activation_rate=redundant_rate,
        search_agent_activations=search_activations,
    )

    proposals = [
        "Scope code_agent to repo edit + pytest loop with file-write tool; forbid free-form rewrites without test feedback.",
        "Scope critic_agent to diff review against failing assertion only; must output structured issue list before optional patch.",
        "Activate search_agent only when task manifest marks external_evidence=true; bind to retrieval tool I/O.",
        "Treat aggregator as fusion layer, not a fourth proposer—run only when proposer fingerprints disagree.",
        "AA router: block verifier-first routes on code tasks; require code_agent before verifier/critic.",
    ]

    result = {
        "scope": "Expert Specialization Auditor (Brief H / Objective 5).",
        "source_summary": args.summary,
        "trajectory_root": str(TRAJECTORY_ROOT),
        "baselines_analyzed": list(FOCUS_BASELINES),
        "runs_analyzed": len(per_run),
        "aggregate": {
            "runs_analyzed": len(per_run),
            "multi_proposer_steps": multi_proposer_steps,
            "disagreement_steps": disagreement_steps,
            "disagreement_rate": round(disagreement_rate, 4),
            "runs_with_redundant_signals": runs_with_redundant,
            "redundant_activation_rate": round(redundant_rate, 4),
            "unique_rescue_count": len(unique_rescues),
            "cross_baseline_sole_rescue_count": len(cross_rescues),
            "search_agent_activations": search_activations,
            "code_critic_pass_rate_spread": round(spread, 4),
            "evidence_outcome": outcome,
        },
        "module_specialization_table": specialization_table,
        "unique_rescue_cases": unique_rescues,
        "cross_baseline_sole_rescues": cross_rescues,
        "redundant_activation_examples": [
            {
                "task_id": r["task_id"],
                "baseline_id": r["baseline_id"],
                "redundant_signals": r["redundant_signals"],
            }
            for r in per_run
            if r["redundant_signals"]
        ],
        "disagreement_examples": [
            {
                "task_id": r["task_id"],
                "baseline_id": r["baseline_id"],
                "disagreements": r["disagreements"][:2],
            }
            for r in per_run
            if r["disagreements"]
        ][:10],
        "specialist_proposals": proposals,
        "per_run": per_run,
    }

    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_path = Path(args.output_md)
    md_path.write_text(render_markdown(result), encoding="utf-8")

    print(
        json.dumps(
            {
                "output_json": str(json_path),
                "output_md": str(md_path),
                "evidence_outcome": outcome,
                "unique_rescue_count": len(unique_rescues),
                "disagreement_rate": round(disagreement_rate, 4),
                "redundant_activation_rate": round(redundant_rate, 4),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
