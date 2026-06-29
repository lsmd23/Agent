#!/usr/bin/env python3
"""Score Agent-Attention benchmark trajectories.

scope:
  Local scoring utility for Phase 0-1 benchmark trajectories. It accepts the
  target trajectory envelope from docs/deliverables/07/trajectory_schema.json
  and the Subtask 06 legacy JSON list envelope.
claims:
  - [prototype] Existing Subtask 06 logs expose enough events to compute a
    useful subset of final, process, route, memory, verifier, and halt metrics.
  - [experiment] The script can score at least one existing trajectory locally.
  - [conjecture] Missing oracle/cost fields should be reported as deviations
    instead of silently filled with optimistic defaults.
design:
  minimal_version: normalize events, compute log-derived metrics, print JSON.
  enhanced_version: join task schema/oracle route matrices and full cost_delta.
  counterexamples: final success without cost is insufficient; cheap failure is
    not a win; harmful memory must be counted separately from useful reuse.
interfaces:
  API: python3 docs/deliverables/07/scoring_script.py <trajectory_path> [...]
  Input: target envelope object or legacy list of {event_id, step, kind, payload}.
  Output: JSON with runs, aggregate, and known_deviations.
experiments:
  - Score experiments/trajectories/runtime_demo.json.
  - Score multiple legacy trajectories and compare aggregate means.
risks:
  - Legacy module-cost is not token/API price.
  - Premature halt and verifier catch are conservative approximations without
    explicit oracle/correction events.
open_questions:
  - Should unknown memory usefulness count against retrieval precision?
  - When should proxy regret become mandatory for synthetic tasks?
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


SUCCESS_PASS = "pass"
LOOP_STUCK_REPEAT_THRESHOLD = 0.60
TOOL_LIKE_MODULES = {"code_agent", "search_agent", "memory"}


METADATA = {
    "scope": "Score benchmark trajectories from target envelopes or Subtask 06 legacy logs.",
    "claims": [
        {"evidence_type": "原型", "claim": "Subtask 06 trajectories can produce Phase 0 metric summaries."},
        {"evidence_type": "实验", "claim": "The script is directly runnable on local trajectory JSON files."},
        {"evidence_type": "猜想", "claim": "Unavailable oracle metrics should be null with deviations, not inferred."},
    ],
    "design": {
        "minimal_version": "Normalize events and compute success, process, routing, memory, verifier, and halt metrics.",
        "enhanced_version": "Use full cost_delta, task oracles, and oracle route matrices when available.",
        "counterexamples": [
            "A successful but expensive run has lower cost-normalized success.",
            "A cheap failed run keeps low cost but zero cost-normalized success.",
            "A harmful memory read is counted even if the final answer passes.",
        ],
    },
    "interfaces": {
        "inputs": ["trajectory envelope object", "Subtask 06 legacy event list"],
        "outputs": ["runs", "aggregate", "known_deviations"],
    },
    "experiments": [
        "python3 docs/deliverables/07/scoring_script.py experiments/trajectories/runtime_demo.json",
        "python3 docs/deliverables/07/scoring_script.py experiments/trajectories/*.json",
    ],
    "risks": [
        "Module activation cost is a toy proxy when token/tool price is absent.",
        "Verifier catch is undercounted without explicit correction events.",
    ],
    "open_questions": [
        "Should unknown memory labels count against precision?",
        "Should proxy route regret be required for all synthetic seed tasks?",
    ],
}


def load_trajectory(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    deviations: list[str] = []
    if isinstance(data, list):
        deviations.extend(
            [
                "legacy_06_event_list_no_top_level_run_metadata",
                "legacy_06_uses_scalar_activation_cost_not_full_cost_delta",
                "legacy_06_lacks_oracle_route_regret",
                "legacy_06_lacks_task_schema_join",
            ]
        )
        return {"schema_version": "legacy_06_event_list"}, data, deviations
    if isinstance(data, dict):
        events = data.get("events") or data.get("trajectory") or []
        if not isinstance(events, list):
            raise ValueError(f"{path}: expected events list in trajectory object")
        known = data.get("known_deviations")
        if isinstance(known, list):
            deviations.extend(str(item) for item in known)
        return data, events, deviations
    raise ValueError(f"{path}: expected JSON object or list")


def event_kind(event: dict[str, Any]) -> str:
    kind = event.get("event_type") or event.get("kind") or ""
    if kind == "route_decision":
        return "route"
    if kind == "halt":
        return "halt_gate"
    return str(kind)


def payload(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("payload")
    return value if isinstance(value, dict) else event


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def repeated_ratio(items: list[str]) -> float:
    if not items:
        return 0.0
    return (len(items) - len(set(items))) / len(items)


def entropy(items: list[str]) -> float:
    if not items:
        return 0.0
    counts = Counter(items)
    total = len(items)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def compact_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def candidate_score(candidate: dict[str, Any]) -> float | None:
    value = candidate.get("score", candidate.get("score_total"))
    if isinstance(value, (int, float)):
        return float(value)
    terms = candidate.get("score_terms")
    weights = candidate.get("score_weights")
    if isinstance(terms, dict) and isinstance(weights, dict):
        return float(sum(float(terms.get(key, 0.0)) * float(weights.get(key, 0.0)) for key in terms))
    return None


def collect_failure_signals(events: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for event in events:
        item = payload(event)
        state = item.get("state") if isinstance(item.get("state"), dict) else item
        raw = state.get("failure_signals") if isinstance(state, dict) else None
        if isinstance(raw, list):
            signals.extend(str(signal) for signal in raw)
        for output in item.get("outputs", []) if isinstance(item.get("outputs"), list) else []:
            signal = output.get("failure_signal")
            if signal:
                signals.append(str(signal))
        error_type = item.get("error_type")
        if error_type and error_type != "none":
            signals.append(str(error_type))
    return signals


def final_state_from_events(envelope: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event_kind(event) == "finish":
            item = payload(event)
            state = item.get("state") if isinstance(item.get("state"), dict) else item
            return state if isinstance(state, dict) else {}
    return envelope if envelope else {}


def last_halt(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event_kind(event) == "halt_gate":
            return payload(event)
    return {}


def score_trajectory(path: Path) -> dict[str, Any]:
    envelope, events, deviations = load_trajectory(path)
    final_state = final_state_from_events(envelope, events)
    final_answer_text = str(envelope.get("final_answer") or final_state.get("final_answer") or "")
    halt = last_halt(events)
    failure_signals = collect_failure_signals(events)

    success_label = envelope.get("final_success_label")
    if not success_label:
        success_label = halt.get("success_signal") or "unknown"
    if success_label not in {"pass", "fail", "partial", "unknown"}:
        success_label = "unknown"
        deviations.append("unknown_final_success_label_normalized")
    task_success = success_label == SUCCESS_PASS

    allowed_modules: list[str] = []
    activation_cost = 0.0
    verifier_calls = 0
    budget_rejections = 0
    for event in events:
        item = payload(event)
        if event_kind(event) == "budget_gate":
            module_id = str(item.get("module_id", ""))
            if item.get("decision") == "allow":
                allowed_modules.append(module_id)
                activation_cost += float(item.get("module_cost") or 0.0)
                if module_id == "verifier":
                    verifier_calls += 1
            elif item.get("decision") == "reject":
                budget_rejections += 1

        cost_delta = item.get("cost_delta")
        if isinstance(cost_delta, dict):
            activation_cost += float(cost_delta.get("monetary_cost_estimate") or cost_delta.get("token_cost_estimate") or 0.0)
            verifier_calls += int(cost_delta.get("verifier_calls") or 0)

    if not allowed_modules:
        selected = final_state.get("selected_modules")
        if isinstance(selected, list):
            allowed_modules = [str(module) for module in selected]
            deviations.append("module_calls_inferred_from_finish_selected_modules")

    route_events = [event for event in events if event_kind(event) == "route"]
    candidates: list[dict[str, Any]] = []
    selected_candidates: list[dict[str, Any]] = []
    selected_from_routes: list[str] = []
    oracle_regrets: list[float] = []
    proxy_regrets: list[float] = []

    for event in route_events:
        item = payload(event)
        for module_id in item.get("selected_modules", []) if isinstance(item.get("selected_modules"), list) else []:
            selected_from_routes.append(str(module_id))
        for candidate in item.get("candidates", []) if isinstance(item.get("candidates"), list) else []:
            candidates.append(candidate)
            if candidate.get("selected"):
                selected_candidates.append(candidate)
        oracle = item.get("oracle") if isinstance(item.get("oracle"), dict) else {}
        if isinstance(oracle.get("oracle_regret"), (int, float)):
            oracle_regrets.append(float(oracle["oracle_regret"]))
        if isinstance(oracle.get("proxy_regret"), (int, float)):
            proxy_regrets.append(float(oracle["proxy_regret"]))

    if not oracle_regrets:
        deviations.append("oracle_route_regret_unavailable")
    if not proxy_regrets:
        deviations.append("proxy_route_regret_unavailable")

    selected_scores = [score for score in (candidate_score(candidate) for candidate in selected_candidates) if score is not None]
    selected_cost_terms = [
        float(candidate["score_terms"]["cost"])
        for candidate in selected_candidates
        if isinstance(candidate.get("score_terms"), dict) and isinstance(candidate["score_terms"].get("cost"), (int, float))
    ]
    route_rejects = [candidate for candidate in candidates if candidate.get("reject_reason")]
    route_modules = allowed_modules or selected_from_routes

    memory_reads = 0
    useful_memory_reads = 0
    harmful_memory_reads = 0
    neutral_memory_reads = 0
    unknown_memory_reads = 0
    negative_transfer_cases = 0
    for event in events:
        item = payload(event)
        if event_kind(event) == "memory_read" or item.get("action_type") == "memory_read":
            memory_reads += 1
            label = str(item.get("memory_usefulness_label") or item.get("usefulness_label") or "unknown")
            if label == "useful":
                useful_memory_reads += 1
            elif label == "harmful":
                harmful_memory_reads += 1
                negative_transfer_cases += 1
            elif label == "neutral":
                neutral_memory_reads += 1
            else:
                unknown_memory_reads += 1
            negative_transfer_cases += int(item.get("negative_transfer_count") or 0)

    negative_transfer_cases += sum(1 for signal in failure_signals if "negative_transfer" in signal)

    verifier_failures = 0
    verifier_statuses: list[str] = []
    for event in events:
        if event_kind(event) == "verifier_result":
            item = payload(event)
            status = str(item.get("status") or item.get("verifier_result") or "unknown")
            verifier_statuses.append(status)
            if status == "fail":
                verifier_failures += 1
    verifier_catches = verifier_failures if verifier_failures and task_success else 0

    invalid_failures = [signal for signal in failure_signals if "invalid_tool" in signal or "wrong_module" in signal]
    tool_like_calls = sum(1 for module_id in allowed_modules if module_id in TOOL_LIKE_MODULES)
    invalid_tool_call_ratio = safe_div(len(invalid_failures), tool_like_calls)

    remaining_budget = None
    budget_snapshot = halt.get("budget_snapshot") if isinstance(halt.get("budget_snapshot"), dict) else {}
    if isinstance(budget_snapshot.get("remaining_budget"), (int, float)):
        remaining_budget = float(budget_snapshot["remaining_budget"])

    halt_reason = str(halt.get("reason") or envelope.get("failure_reason") or "")
    extracted_finish_reason = None
    marker = "Finalized because "
    if marker in final_answer_text:
        extracted_finish_reason = final_answer_text.split(marker, 1)[1].split(".", 1)[0].strip()
    finish_without_terminal_halt = bool(events and event_kind(events[-1]) == "finish" and halt and halt.get("halt") is False)
    step_exhaustion = extracted_finish_reason == "max_steps_reached"
    budget_exhaustion = (
        halt_reason == "budget_exhausted"
        or budget_rejections > 0
        or any("budget" in signal for signal in failure_signals)
    )
    loop_stuck = halt_reason == "loop_stuck" or repeated_ratio(route_modules) > LOOP_STUCK_REPEAT_THRESHOLD
    premature_halt = (
        not task_success
        and (
            halt_reason in {"answer_ready", "success"}
            or (finish_without_terminal_halt and not step_exhaustion and (remaining_budget is None or remaining_budget > 0))
        )
    )
    failure_reason = envelope.get("failure_reason")
    if not failure_reason and not task_success:
        failure_reason = extracted_finish_reason or halt_reason or None

    labeled_memory_reads = useful_memory_reads + harmful_memory_reads + neutral_memory_reads
    known_deviations = sorted(set(deviations))

    run = {
        "trajectory_path": str(path),
        "task_id": envelope.get("task_id"),
        "benchmark_id": envelope.get("benchmark_id"),
        "baseline_id": envelope.get("baseline_id", "agent_attention_agent" if envelope.get("schema_version") == "legacy_06_event_list" else None),
        "ablation_id": envelope.get("ablation_id"),
        "final": {
            "success_label": success_label,
            "task_success": task_success,
            "failure_reason": failure_reason,
            "final_answer_present": bool(final_answer_text),
        },
        "process": {
            "activation_cost": compact_float(activation_cost),
            "cost_normalized_success": compact_float((1.0 if task_success else 0.0) / (1.0 + activation_cost)),
            "module_calls": len(allowed_modules),
            "verifier_calls": verifier_calls,
            "budget_rejections": budget_rejections,
            "repeated_action_ratio": compact_float(repeated_ratio(route_modules)),
            "invalid_tool_call_ratio": compact_float(invalid_tool_call_ratio),
            "loop_stuck": loop_stuck,
            "budget_exhaustion": budget_exhaustion,
            "step_exhaustion": step_exhaustion,
            "premature_halt": premature_halt,
        },
        "routing": {
            "route_events": len(route_events),
            "route_candidates": len(candidates),
            "selected_candidates": len(selected_candidates),
            "route_reject_rate": compact_float(safe_div(len(route_rejects), len(candidates))),
            "route_entropy": compact_float(entropy(route_modules)),
            "selected_route_score_mean": compact_float(mean(selected_scores) if selected_scores else None),
            "selected_route_cost_mean": compact_float(mean(selected_cost_terms) if selected_cost_terms else None),
            "oracle_route_regret_mean": compact_float(mean(oracle_regrets) if oracle_regrets else None),
            "proxy_route_regret_mean": compact_float(mean(proxy_regrets) if proxy_regrets else None),
            "activated_modules": route_modules,
        },
        "memory": {
            "memory_reads": memory_reads,
            "useful_memory_reads": useful_memory_reads,
            "harmful_memory_reads": harmful_memory_reads,
            "neutral_memory_reads": neutral_memory_reads,
            "unknown_memory_reads": unknown_memory_reads,
            "useful_memory_reuse_rate": compact_float(safe_div(useful_memory_reads, labeled_memory_reads)),
            "negative_transfer_cases": negative_transfer_cases,
        },
        "verifier": {
            "verifier_statuses": verifier_statuses,
            "verifier_failures": verifier_failures,
            "verifier_catches": verifier_catches,
            "verifier_catch_rate": compact_float(safe_div(verifier_catches, verifier_failures)),
        },
        "known_deviations": known_deviations,
    }
    if envelope.get("oracle_route_regret") is not None:
        run["oracle_route_regret"] = compact_float(float(envelope["oracle_route_regret"]))
    if envelope.get("router_id") is not None:
        run["router_id"] = envelope.get("router_id")
    return run


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {}

    def values(section: str, key: str) -> list[float]:
        result: list[float] = []
        for run in runs:
            value = run.get(section, {}).get(key)
            if isinstance(value, bool):
                result.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                result.append(float(value))
        return result

    def mean_or_none(items: list[float]) -> float | None:
        return mean(items) if items else None

    success_values = [1.0 if run["final"]["task_success"] else 0.0 for run in runs]
    aggregate = {
        "run_count": len(runs),
        "success_rate": compact_float(mean(success_values)),
        "mean_cost_normalized_success": compact_float(mean(values("process", "cost_normalized_success"))),
        "mean_activation_cost": compact_float(mean(values("process", "activation_cost"))),
        "mean_module_calls": compact_float(mean(values("process", "module_calls"))),
        "mean_repeated_action_ratio": compact_float(mean(values("process", "repeated_action_ratio"))),
        "budget_exhaustion_rate": compact_float(mean(values("process", "budget_exhaustion"))),
        "premature_halt_rate": compact_float(mean(values("process", "premature_halt"))),
        "loop_stuck_rate": compact_float(mean(values("process", "loop_stuck"))),
        "step_exhaustion_rate": compact_float(mean(values("process", "step_exhaustion"))),
        "mean_route_entropy": compact_float(mean_or_none(values("routing", "route_entropy"))),
        "mean_route_reject_rate": compact_float(mean_or_none(values("routing", "route_reject_rate"))),
        "mean_oracle_route_regret": compact_float(mean_or_none(values("routing", "oracle_route_regret_mean"))),
        "mean_proxy_route_regret": compact_float(mean_or_none(values("routing", "proxy_route_regret_mean"))),
        "total_memory_reads": int(sum(values("memory", "memory_reads"))),
        "total_negative_transfer_cases": int(sum(values("memory", "negative_transfer_cases"))),
        "total_verifier_failures": int(sum(values("verifier", "verifier_failures"))),
        "total_verifier_catches": int(sum(values("verifier", "verifier_catches"))),
    }
    deviations = sorted({deviation for run in runs for deviation in run.get("known_deviations", [])})
    aggregate["known_deviations"] = deviations
    return aggregate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score Agent-Attention trajectory JSON files.")
    parser.add_argument("trajectory_paths", nargs="+", help="Trajectory JSON path(s).")
    parser.add_argument("--output", help="Optional path to write the metrics JSON summary.")
    parser.add_argument("--metadata", action="store_true", help="Include script metadata in the JSON output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runs = [score_trajectory(Path(path)) for path in args.trajectory_paths]
    output: dict[str, Any] = {
        "runs": runs,
        "aggregate": aggregate_runs(runs),
    }
    if args.metadata:
        output["metadata"] = METADATA

    text = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
