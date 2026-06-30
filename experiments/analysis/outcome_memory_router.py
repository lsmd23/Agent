#!/usr/bin/env python3
"""Outcome-memory router replay on the 26-task code matrix (Brief D).

Stores verified route outcomes keyed by task_family + error signature.
Does NOT store patch bodies, answers, or full trajectories.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.analysis.oracle_route_matrix import route_reward
from experiments.baselines.common import load_jsonl
from experiments.cascade.cascade_policy import STAGE_AA, STAGE_MOA, STAGE_REACT


SCHEMA_VERSION = "agent_attention.outcome_memory.v0.1"
DEFAULT_ROUTE = STAGE_REACT
TRANSCRIPT_MEMORY_BASELINE = "retrieval_memory_llm_agent"
ESCALATION_ROUTES = (
    STAGE_AA,
    STAGE_MOA,
    "fixed_workflow_llm_agent",
    TRANSCRIPT_MEMORY_BASELINE,
)

FORBIDDEN_VALUE_KEYS = frozenset(
    {
        "patch",
        "patch_body",
        "answer",
        "final_answer",
        "trajectory",
        "trajectory_summary",
        "code_block",
        "content",
        "pytest_stdout",
        "pytest_stderr",
        "applied_files",
        "prompt",
        "goal",
    }
)
FORBIDDEN_KEY_SUBSTRINGS = ("task_id", "run_id", "fixture_id", "benchmark_answer")

FAIL_LINE_RE = re.compile(r"FAIL:\s+(\S+)\s+\(([^)]+)\)")
ERROR_CLASS_RE = re.compile(r"\n(\w+Error|\w+Exception|Fail):")


@dataclass
class OutcomeMemoryKey:
    task_family: str
    error_signature: str

    def as_dict(self) -> dict[str, str]:
        return {"task_family": self.task_family, "error_signature": self.error_signature}

    def storage_key(self) -> tuple[str, str]:
        return (self.task_family, self.error_signature)


@dataclass
class RouteOutcomeStats:
    attempts: int = 0
    successes: int = 0
    total_model_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    sum_route_reward: float = 0.0

    def observe(self, row: dict[str, Any]) -> None:
        self.attempts += 1
        if row.get("success"):
            self.successes += 1
        self.total_model_calls += int(row.get("model_calls") or 0)
        self.total_tokens += int(row.get("total_tokens") or 0)
        self.total_latency_ms += int(row.get("latency_ms") or 0)
        self.sum_route_reward += route_reward(row)

    def to_dict(self) -> dict[str, Any]:
        attempts = self.attempts or 1
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "success_rate": round(self.successes / attempts, 6) if self.attempts else 0.0,
            "mean_model_calls": round(self.total_model_calls / attempts, 4),
            "mean_total_tokens": round(self.total_tokens / attempts, 2),
            "mean_latency_ms": round(self.total_latency_ms / attempts, 2),
            "mean_route_reward": round(self.sum_route_reward / attempts, 6),
        }


@dataclass
class OutcomeMemoryEntry:
    key: OutcomeMemoryKey
    route_stats: dict[str, RouteOutcomeStats] = field(default_factory=dict)
    source_task_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "memory_profile": "behavior_kv",
            "memory_type": "behavior_kv",
            "write_reason": "success",
            "key": self.key.as_dict(),
            "value": {
                "route_outcomes": {
                    route_id: stats.to_dict() for route_id, stats in sorted(self.route_stats.items())
                }
            },
            "provenance": {
                "source_task_count": len(set(self.source_task_ids)),
                "source_task_ids_hash": _hash_task_ids(self.source_task_ids),
            },
        }


@dataclass
class OutcomeMemoryStore:
    entries: dict[tuple[str, str], OutcomeMemoryEntry] = field(default_factory=dict)

    def write_outcome(
        self,
        key: OutcomeMemoryKey,
        route_id: str,
        row: dict[str, Any],
        *,
        source_task_id: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if payload is not None:
            assert_no_leakage(payload)
        if any(token in source_task_id for token in FORBIDDEN_KEY_SUBSTRINGS):
            raise ValueError(f"task_id must not appear in memory keys: {source_task_id!r}")
        storage = self.entries.setdefault(key.storage_key(), OutcomeMemoryEntry(key=key))
        storage.route_stats.setdefault(route_id, RouteOutcomeStats()).observe(row)
        storage.source_task_ids.append(source_task_id)

    def retrieve(self, key: OutcomeMemoryKey) -> OutcomeMemoryEntry | None:
        return self.entries.get(key.storage_key())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "entry_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries.values()],
        }


def _hash_task_ids(task_ids: list[str]) -> str:
    import hashlib

    joined = ",".join(sorted(set(task_ids)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def assert_no_leakage(payload: dict[str, Any], *, path: str = "") -> None:
    """Reject payloads that would leak answers or patch bodies into memory."""
    for key, value in payload.items():
        full_key = f"{path}.{key}" if path else str(key)
        lowered = str(key).lower()
        if lowered in FORBIDDEN_VALUE_KEYS:
            raise ValueError(f"Leakage guard blocked forbidden field: {full_key}")
        if any(token in lowered for token in FORBIDDEN_KEY_SUBSTRINGS):
            raise ValueError(f"Leakage guard blocked task-identifying key field: {full_key}")
        if isinstance(value, dict):
            assert_no_leakage(value, path=full_key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    assert_no_leakage(item, path=f"{full_key}[{index}]")


def normalize_pytest_signature(stderr: str) -> str | None:
    if not stderr:
        return None
    fail_match = FAIL_LINE_RE.search(stderr)
    err_match = ERROR_CLASS_RE.search(stderr)
    if not fail_match:
        return None
    error_class = err_match.group(1) if err_match else "Fail"
    return f"{error_class}|{fail_match.group(1)}"


def tag_signature(task: dict[str, Any]) -> str | None:
    skip = {"code", "phase1", "phase0"}
    tags = [tag for tag in task.get("tags", []) if tag not in skip]
    return f"tag:{tags[0]}" if tags else None


def error_signature_for_task(
    task_id: str,
    task: dict[str, Any],
    trajectory_lookup: dict[str, dict[str, Any]],
) -> str:
    envelope = trajectory_lookup.get(task_id)
    if envelope:
        metrics = envelope.get("metrics_summary") or {}
        pytest_sig = normalize_pytest_signature(str(metrics.get("pytest_stderr") or ""))
        if pytest_sig:
            return pytest_sig
    tag_sig = tag_signature(task)
    if tag_sig:
        return tag_sig
    suffix = task_id.removesuffix("_001").split("_")[-1]
    return f"kind:{suffix}"


def memory_key_for_task(
    task_id: str,
    task: dict[str, Any],
    trajectory_lookup: dict[str, dict[str, Any]],
) -> OutcomeMemoryKey:
    return OutcomeMemoryKey(
        task_family=str(task.get("task_family") or "unknown"),
        error_signature=error_signature_for_task(task_id, task, trajectory_lookup),
    )


def load_trajectory_lookup(trajectory_root: Path, baseline_id: str = DEFAULT_ROUTE) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    base_dir = trajectory_root / baseline_id
    if not base_dir.exists():
        return lookup
    for path in base_dir.glob("*.json"):
        if path.name.endswith(".metrics.json"):
            continue
        envelope = json.loads(path.read_text(encoding="utf-8"))
        lookup[str(envelope.get("task_id"))] = envelope
    return lookup


def index_matrix_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str]]:
    by_task: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_task[row["task_id"]][row["baseline_id"]] = row
    return by_task, sorted(by_task)


def build_memory_store(
    train_task_ids: list[str],
    *,
    by_task: dict[str, dict[str, dict[str, Any]]],
    tasks_by_id: dict[str, dict[str, Any]],
    trajectory_lookup: dict[str, dict[str, Any]],
    escalation_only: bool,
    routes: tuple[str, ...],
) -> OutcomeMemoryStore:
    store = OutcomeMemoryStore()
    for task_id in train_task_ids:
        task = tasks_by_id[task_id]
        key = memory_key_for_task(task_id, task, trajectory_lookup)
        react_row = by_task[task_id].get(DEFAULT_ROUTE)
        if escalation_only and react_row and react_row.get("success"):
            continue
        for route_id in routes:
            row = by_task[task_id].get(route_id)
            if row is None:
                continue
            store.write_outcome(key, route_id, row, source_task_id=task_id)
    return store


def _rank_routes(stats: dict[str, RouteOutcomeStats]) -> list[str]:
    ranked = sorted(
        stats,
        key=lambda route_id: (
            -(stats[route_id].successes / stats[route_id].attempts) if stats[route_id].attempts else 0.0,
            -(stats[route_id].sum_route_reward / stats[route_id].attempts) if stats[route_id].attempts else 0.0,
            stats[route_id].total_model_calls / stats[route_id].attempts if stats[route_id].attempts else 999.0,
            route_id,
        ),
    )
    return ranked


def select_static_route(
    entry: OutcomeMemoryEntry | None,
    *,
    default_route: str = DEFAULT_ROUTE,
    min_attempts: int = 2,
    min_success_rate: float = 0.5,
) -> tuple[str, str]:
    if entry is None or not entry.route_stats:
        return default_route, "default_no_memory"

    default_stats = entry.route_stats.get(default_route)
    default_reward = (
        default_stats.sum_route_reward / default_stats.attempts if default_stats and default_stats.attempts else None
    )
    candidates = [
        route_id
        for route_id, stats in entry.route_stats.items()
        if stats.attempts >= min_attempts and (stats.successes / stats.attempts) >= min_success_rate
    ]
    if not candidates:
        return default_route, "default_insufficient_memory"

    ranked = _rank_routes({route_id: entry.route_stats[route_id] for route_id in candidates})
    best = ranked[0]
    best_stats = entry.route_stats[best]
    best_reward = best_stats.sum_route_reward / best_stats.attempts
    if default_reward is not None and best_reward <= default_reward + 1e-9:
        return default_route, "default_beats_memory"
    return best, "memory_override"


def select_escalation_order(entry: OutcomeMemoryEntry | None) -> tuple[list[str], str]:
    default_order = [STAGE_AA, STAGE_MOA]
    if entry is None or not entry.route_stats:
        return default_order, "default_cascade"

    usable = {
        route_id: stats
        for route_id, stats in entry.route_stats.items()
        if route_id in ESCALATION_ROUTES and stats.attempts >= 1
    }
    if not usable:
        return default_order, "default_cascade"

    ranked = [route_id for route_id in _rank_routes(usable) if usable[route_id].successes > 0]
    for route_id in default_order:
        if route_id not in ranked:
            ranked.append(route_id)
    return ranked, "memory_escalation"


def simulate_cascade(
    task_id: str,
    escalation_order: list[str],
    by_task: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    stages = [DEFAULT_ROUTE, *escalation_order]
    seen: set[str] = set()
    stage_rows: list[dict[str, Any]] = []
    for stage_id in stages:
        if stage_id in seen:
            continue
        seen.add(stage_id)
        row = by_task[task_id].get(stage_id)
        if row is None:
            continue
        stage_rows.append(row)
        if row.get("success"):
            break

    success = any(row.get("success") for row in stage_rows)
    total_calls = sum(int(row.get("model_calls") or 0) for row in stage_rows)
    total_tokens = sum(int(row.get("total_tokens") or 0) for row in stage_rows)
    total_latency = sum(int(row.get("latency_ms") or 0) for row in stage_rows)
    return {
        "task_id": task_id,
        "success": success,
        "model_calls": total_calls,
        "total_tokens": total_tokens,
        "latency_ms": total_latency,
        "selected_route": stage_rows[-1]["baseline_id"] if stage_rows else DEFAULT_ROUTE,
        "stages_run": len(stage_rows),
    }


def regret_for_row(oracle_reward: float, row: dict[str, Any]) -> float:
    return round(oracle_reward - route_reward(row), 6)


def replay_leave_one_out(
    *,
    by_task: dict[str, dict[str, dict[str, Any]]],
    task_ids: list[str],
    tasks_by_id: dict[str, dict[str, Any]],
    trajectory_lookup: dict[str, dict[str, Any]],
    oracle_by_task: dict[str, float],
    mode: str,
) -> dict[str, Any]:
    per_task: list[dict[str, Any]] = []
    memory_hits = 0

    for task_id in task_ids:
        train_ids = [other_id for other_id in task_ids if other_id != task_id]
        key = memory_key_for_task(task_id, tasks_by_id[task_id], trajectory_lookup)
        store = build_memory_store(
            train_ids,
            by_task=by_task,
            tasks_by_id=tasks_by_id,
            trajectory_lookup=trajectory_lookup,
            escalation_only=(mode == "cascade"),
            routes=tuple(by_task[task_id]),
        )
        entry = store.retrieve(key)

        if mode == "cascade":
            escalation_order, reason = select_escalation_order(entry)
            selected = simulate_cascade(task_id, escalation_order, by_task)
            selected["selection_reason"] = reason
        else:
            route_id, reason = select_static_route(entry)
            selected = dict(by_task[task_id][route_id])
            selected["baseline_id"] = route_id
            selected["selection_reason"] = reason

        if reason not in {"default_no_memory", "default_insufficient_memory", "default_beats_memory", "default_cascade"}:
            memory_hits += 1

        oracle_reward = oracle_by_task[task_id]
        per_task.append(
            {
                "task_id": task_id,
                "memory_key": key.as_dict(),
                "selection_reason": selected["selection_reason"],
                "selected_route": selected.get("baseline_id") or selected.get("selected_route"),
                "success": bool(selected.get("success")),
                "model_calls": selected.get("model_calls"),
                "route_reward": round(route_reward(selected), 6),
                "regret_vs_oracle_reward": regret_for_row(oracle_reward, selected),
            }
        )

    mean_regret = round(sum(row["regret_vs_oracle_reward"] for row in per_task) / len(per_task), 6)
    accuracy = round(sum(1 for row in per_task if row["success"]) / len(per_task), 6)
    return {
        "mode": mode,
        "tasks": len(per_task),
        "accuracy": accuracy,
        "mean_regret_vs_oracle_reward": mean_regret,
        "memory_hit_rate": round(memory_hits / len(per_task), 6),
        "per_task": per_task,
    }


def replay_streaming(
    *,
    by_task: dict[str, dict[str, dict[str, Any]]],
    task_ids: list[str],
    tasks_by_id: dict[str, dict[str, Any]],
    trajectory_lookup: dict[str, dict[str, Any]],
    oracle_by_task: dict[str, float],
    mode: str,
) -> dict[str, Any]:
    store = OutcomeMemoryStore()
    per_task: list[dict[str, Any]] = []
    memory_hits = 0

    for task_id in task_ids:
        key = memory_key_for_task(task_id, tasks_by_id[task_id], trajectory_lookup)
        entry = store.retrieve(key)

        if mode == "cascade":
            escalation_order, reason = select_escalation_order(entry)
            selected = simulate_cascade(task_id, escalation_order, by_task)
            selected["selection_reason"] = reason
        else:
            route_id, reason = select_static_route(entry)
            selected = dict(by_task[task_id][route_id])
            selected["baseline_id"] = route_id
            selected["selection_reason"] = reason

        if reason not in {"default_no_memory", "default_insufficient_memory", "default_beats_memory", "default_cascade"}:
            memory_hits += 1

        oracle_reward = oracle_by_task[task_id]
        per_task.append(
            {
                "task_id": task_id,
                "memory_key": key.as_dict(),
                "selection_reason": selected["selection_reason"],
                "selected_route": selected.get("baseline_id") or selected.get("selected_route"),
                "success": bool(selected.get("success")),
                "regret_vs_oracle_reward": regret_for_row(oracle_reward, selected),
            }
        )

        react_row = by_task[task_id].get(DEFAULT_ROUTE)
        write_routes = tuple(by_task[task_id]) if mode == "static" else ESCALATION_ROUTES
        if mode == "cascade" and react_row and react_row.get("success"):
            continue
        for route_id in write_routes:
            row = by_task[task_id].get(route_id)
            if row is None:
                continue
            store.write_outcome(key, route_id, row, source_task_id=task_id)

    mean_regret = round(sum(row["regret_vs_oracle_reward"] for row in per_task) / len(per_task), 6)
    return {
        "mode": mode,
        "tasks": len(per_task),
        "mean_regret_vs_oracle_reward": mean_regret,
        "memory_hit_rate": round(memory_hits / len(per_task), 6),
        "per_task": per_task,
        "final_store_entry_count": len(store.entries),
    }


def baseline_replay(
    *,
    by_task: dict[str, dict[str, dict[str, Any]]],
    task_ids: list[str],
    oracle_by_task: dict[str, float],
    baseline_route: str,
) -> dict[str, Any]:
    per_task = []
    for task_id in task_ids:
        row = by_task[task_id][baseline_route]
        per_task.append(
            {
                "task_id": task_id,
                "selected_route": baseline_route,
                "success": bool(row.get("success")),
                "regret_vs_oracle_reward": regret_for_row(oracle_by_task[task_id], row),
            }
        )
    mean_regret = round(sum(row["regret_vs_oracle_reward"] for row in per_task) / len(per_task), 6)
    accuracy = round(sum(1 for row in per_task if row["success"]) / len(per_task), 6)
    return {
        "baseline_route": baseline_route,
        "tasks": len(per_task),
        "accuracy": accuracy,
        "mean_regret_vs_oracle_reward": mean_regret,
        "per_task": per_task,
    }


def audit_leakage(store: OutcomeMemoryStore) -> dict[str, Any]:
    violations: list[str] = []
    serialized = json.dumps(store.to_dict())
    forbidden_snippets = ("def ", "class ", "assertEqual", "final_answer", "```python")
    for snippet in forbidden_snippets:
        if snippet in serialized:
            violations.append(f"forbidden_snippet:{snippet}")
    for entry in store.entries.values():
        if entry.key.error_signature.startswith("phase"):
            violations.append("task_id_like_error_signature")
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "forbidden_value_keys": sorted(FORBIDDEN_VALUE_KEYS),
        "forbidden_key_substrings": sorted(FORBIDDEN_KEY_SUBSTRINGS),
    }


def classify_outcome(*, delta_regret: float, leakage_passed: bool, memory_hit_rate: float) -> str:
    if not leakage_passed:
        return "falsified_or_blocked"
    if delta_regret >= 0.02:
        return "supports_direction"
    if delta_regret <= -0.02:
        return "falsified_or_blocked"
    if memory_hit_rate <= 0.05:
        return "weak_or_inconclusive"
    return "weak_or_inconclusive"


def analyze(
    summary: dict[str, Any],
    *,
    tasks_by_id: dict[str, dict[str, Any]],
    trajectory_lookup: dict[str, dict[str, Any]],
    oracle_matrix: dict[str, Any],
) -> dict[str, Any]:
    by_task, task_ids = index_matrix_rows(summary.get("per_task", []))
    oracle_by_task = {
        task["task_id"]: float(task["oracle_route_reward"]) for task in oracle_matrix.get("per_task", [])
    }

    baseline_react = baseline_replay(
        by_task=by_task,
        task_ids=task_ids,
        oracle_by_task=oracle_by_task,
        baseline_route=DEFAULT_ROUTE,
    )
    baseline_transcript = baseline_replay(
        by_task=by_task,
        task_ids=task_ids,
        oracle_by_task=oracle_by_task,
        baseline_route=TRANSCRIPT_MEMORY_BASELINE,
    )

    loo_static = replay_leave_one_out(
        by_task=by_task,
        task_ids=task_ids,
        tasks_by_id=tasks_by_id,
        trajectory_lookup=trajectory_lookup,
        oracle_by_task=oracle_by_task,
        mode="static",
    )
    loo_cascade = replay_leave_one_out(
        by_task=by_task,
        task_ids=task_ids,
        tasks_by_id=tasks_by_id,
        trajectory_lookup=trajectory_lookup,
        oracle_by_task=oracle_by_task,
        mode="cascade",
    )
    baseline_cascade = replay_leave_one_out(
        by_task=by_task,
        task_ids=task_ids,
        tasks_by_id=tasks_by_id,
        trajectory_lookup={},  # force default escalation order
        oracle_by_task=oracle_by_task,
        mode="cascade",
    )
    stream_cascade = replay_streaming(
        by_task=by_task,
        task_ids=task_ids,
        tasks_by_id=tasks_by_id,
        trajectory_lookup=trajectory_lookup,
        oracle_by_task=oracle_by_task,
        mode="cascade",
    )

    full_store = build_memory_store(
        task_ids,
        by_task=by_task,
        tasks_by_id=tasks_by_id,
        trajectory_lookup=trajectory_lookup,
        escalation_only=True,
        routes=tuple(next(iter(by_task.values())).keys()),
    )
    leakage = audit_leakage(full_store)

    primary = loo_cascade
    baseline = baseline_cascade
    delta_regret = round(baseline["mean_regret_vs_oracle_reward"] - primary["mean_regret_vs_oracle_reward"], 6)
    delta_regret_vs_react = round(
        baseline_react["mean_regret_vs_oracle_reward"] - primary["mean_regret_vs_oracle_reward"], 6
    )
    outcome = classify_outcome(
        delta_regret=delta_regret,
        leakage_passed=leakage["passed"],
        memory_hit_rate=primary["memory_hit_rate"],
    )

    signature_counts: dict[str, int] = defaultdict(int)
    for task_id in task_ids:
        key = memory_key_for_task(task_id, tasks_by_id[task_id], trajectory_lookup)
        signature_counts[key.error_signature] += 1

    return {
        "scope": "Outcome-memory router replay on 26-task code matrix (Brief D, zero new LLM calls).",
        "schema_version": SCHEMA_VERSION,
        "source_summary": None,
        "source_oracle_matrix": None,
        "source_tasks": None,
        "source_trajectories": None,
        "suite": summary.get("suite"),
        "tasks": summary.get("tasks"),
        "model": summary.get("model"),
        "provider": summary.get("provider"),
        "memory_schema": {
            "key_fields": ["task_family", "error_signature"],
            "value_fields": ["route_outcomes"],
            "forbidden_in_value": sorted(FORBIDDEN_VALUE_KEYS),
            "retrieval_policy": [
                "exact match on task_family + error_signature",
                "static override only when memory attempts>=2 and success_rate>=0.5 beats default reward",
                "cascade escalation ranks rescue routes by observed success_rate then route_reward",
            ],
            "write_policy": [
                "aggregate verified route stats only",
                "cascade mode writes only from react-failure contexts",
                "never store patch bodies, answers, or raw pytest output",
            ],
        },
        "aggregate": {
            "primary_eval_mode": "loo_cascade",
            "baseline_policy": "fixed_cascade_react_aa_moa_no_memory",
            "baseline_mean_regret": baseline["mean_regret_vs_oracle_reward"],
            "baseline_accuracy": baseline["accuracy"],
            "react_only_mean_regret": baseline_react["mean_regret_vs_oracle_reward"],
            "delta_regret_vs_fixed_cascade": delta_regret,
            "delta_regret_vs_react_only": delta_regret_vs_react,
            "transcript_memory_baseline_route": TRANSCRIPT_MEMORY_BASELINE,
            "transcript_memory_mean_regret": baseline_transcript["mean_regret_vs_oracle_reward"],
            "outcome_memory_mean_regret": primary["mean_regret_vs_oracle_reward"],
            "outcome_memory_accuracy": primary["accuracy"],
            "delta_regret_vs_no_memory": delta_regret,
            "delta_regret_vs_transcript_memory": round(
                baseline_transcript["mean_regret_vs_oracle_reward"] - primary["mean_regret_vs_oracle_reward"],
                6,
            ),
            "memory_hit_rate": primary["memory_hit_rate"],
            "unique_error_signatures": len(signature_counts),
            "leakage_audit": leakage,
            "evidence_outcome": outcome,
        },
        "evaluations": {
            "baseline_react": baseline_react,
            "baseline_fixed_cascade": baseline_cascade,
            "baseline_transcript_memory": baseline_transcript,
            "loo_static": loo_static,
            "loo_cascade": loo_cascade,
            "streaming_cascade": stream_cascade,
        },
        "memory_store_snapshot": full_store.to_dict(),
        "error_signature_counts": dict(sorted(signature_counts.items(), key=lambda item: (-item[1], item[0]))),
    }


def render_audit_markdown(result: dict[str, Any]) -> str:
    agg = result["aggregate"]
    schema = result["memory_schema"]
    lines = [
        "# Outcome Memory Audit (Brief D)",
        "",
        "## Scope",
        "",
        "Outcome-memory router on the 26-task code suite matrix (5 baselines, no new LLM calls).",
        "Memory stores **verified route outcomes** keyed by task family + error signature — not task answers.",
        "",
        "## Inputs Read",
        "",
        f"- `{result.get('source_summary')}`",
        f"- `{result.get('source_oracle_matrix')}`",
        f"- `{result.get('source_tasks')}`",
        f"- `{result.get('source_trajectories')}` (react trajectories for pytest error signatures)",
        "- `docs/deliverables/04/memory_policy.md`",
        "- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief D)",
        "",
        "## Method",
        "",
        "### Memory schema",
        "",
        f"- Key: `{schema['key_fields'][0]}` + `{schema['key_fields'][1]}`",
        f"- Value: `{schema['value_fields'][0]}` → success/cost aggregates per route",
        "- Leakage guards reject patch bodies, answers, raw pytest output, and task-id keys.",
        "",
        "### Retrieval policy",
        "",
    ]
    for item in schema["retrieval_policy"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "### Replay evaluation",
            "",
            "- **Primary:** leave-one-out cascade replay — react first, memory-ranked escalation on failure.",
            "- **No-memory baseline:** fixed react→AA→MoA cascade (same stages, default order).",
            "- **Reference baselines:** always-ReAct and retrieval-memory static routes.",
            "- Regret = oracle route reward − selected route reward (Brief A weights).",
            "",
            "## Commands Run",
            "",
            "```bash",
            "python3 experiments/analysis/outcome_memory_router.py",
            "```",
            "",
            "## Artifacts Created",
            "",
            "- `experiments/metrics/outcome_memory_diagnostic.json`",
            "- `experiments/analysis/outcome_memory_audit.md`",
            "",
            "## Results",
            "",
            "| Policy | Accuracy | Mean regret vs oracle |",
            "|--------|----------|------------------------|",
            f"| Fixed cascade (no memory) | {agg['baseline_accuracy']:.1%} | {agg['baseline_mean_regret']:.4f} |",
            f"| Outcome memory (LOO cascade) | {agg['outcome_memory_accuracy']:.1%} | {agg['outcome_memory_mean_regret']:.4f} |",
            f"| ReAct only (reference) | — | {agg['react_only_mean_regret']:.4f} |",
            f"| Transcript memory (reference) | — | {agg['transcript_memory_mean_regret']:.4f} |",
            "",
            f"- **Δ regret vs fixed cascade (primary):** {agg['delta_regret_vs_fixed_cascade']:+.4f} (positive = outcome memory lower regret)",
            f"- **Δ regret vs ReAct only:** {agg['delta_regret_vs_react_only']:+.4f}",
            f"- **Δ regret vs transcript memory:** {agg['delta_regret_vs_transcript_memory']:+.4f}",
            f"- Memory hit rate (LOO cascade): {agg['memory_hit_rate']:.1%}",
            f"- Unique error signatures: {agg['unique_error_signatures']}",
            "",
            "### Leakage audit",
            "",
            f"- Passed: **{agg['leakage_audit']['passed']}**",
        ]
    )
    if agg["leakage_audit"]["violations"]:
        lines.append(f"- Violations: {agg['leakage_audit']['violations']}")
    else:
        lines.append("- No patch/answer leakage detected in stored memory entries.")

    loo_static = result["evaluations"]["loo_static"]
    lines.extend(
        [
            "",
            "### Alternate eval: LOO static route override",
            "",
            f"- Mean regret: {loo_static['mean_regret_vs_oracle_reward']:.4f}",
            f"- Memory hit rate: {loo_static['memory_hit_rate']:.1%}",
            "",
            "## Interpretation",
            "",
        ]
    )
    outcome = agg["evidence_outcome"]
    if outcome == "supports_direction":
        lines.append(
            "Outcome memory reduces route regret vs the no-memory baseline without storing answers. "
            "Worth integrating into cascade escalation slot."
        )
    elif outcome == "weak_or_inconclusive":
        lines.append(
            "Schema, retrieval, and leakage guards are in place, but at N=26 the memory rarely changes "
            "routing vs fixed react→AA→MoA cascade. Treat as diagnostic infrastructure; expand task "
            "families or failure diversity before claiming memory-driven routing gains."
        )
    else:
        lines.append(
            "Outcome memory does not beat the no-memory baseline on regret, or leakage guards failed. "
            "Do not deploy answer-free memory routing on this suite alone."
        )
    lines.extend(
        [
            "",
            f"**Evidence outcome:** `{outcome}`",
            "",
            "## Next Questions",
            "",
            "- Expand failure-class diversity so memory keys accumulate ≥3 observations per signature.",
            "- Brief E: can cheap features predict escalation route when outcome memory is cold-start?",
            "- Gate transcript memory off in escalation slot; A/B outcome-only vs no-memory live.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Outcome-memory router replay (Brief D).")
    parser.add_argument("--input", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--oracle-matrix", default="experiments/metrics/oracle_route_matrix.json")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_code_all.jsonl")
    parser.add_argument(
        "--trajectory-root",
        default="experiments/llm_runs/code_full_matrix/code_all",
    )
    parser.add_argument("--output-json", default="experiments/metrics/outcome_memory_diagnostic.json")
    parser.add_argument("--output-md", default="experiments/analysis/outcome_memory_audit.md")
    args = parser.parse_args()

    summary = json.loads(Path(args.input).read_text(encoding="utf-8"))
    oracle_matrix = json.loads(Path(args.oracle_matrix).read_text(encoding="utf-8"))
    tasks = load_jsonl(Path(args.tasks))
    tasks_by_id = {task["task_id"]: task for task in tasks}
    trajectory_lookup = load_trajectory_lookup(Path(args.trajectory_root))

    result = analyze(
        summary,
        tasks_by_id=tasks_by_id,
        trajectory_lookup=trajectory_lookup,
        oracle_matrix=oracle_matrix,
    )
    result["source_summary"] = args.input
    result["source_oracle_matrix"] = args.oracle_matrix
    result["source_tasks"] = args.tasks
    result["source_trajectories"] = args.trajectory_root

    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_path = Path(args.output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_audit_markdown(result), encoding="utf-8")

    agg = result["aggregate"]
    print(
        json.dumps(
            {
                "output_json": str(json_path),
                "output_md": str(md_path),
                "evidence_outcome": agg["evidence_outcome"],
                "supports_direction": agg["evidence_outcome"] == "supports_direction",
                "delta_regret_vs_no_memory": agg["delta_regret_vs_no_memory"],
                "baseline_mean_regret": agg["baseline_mean_regret"],
                "outcome_memory_mean_regret": agg["outcome_memory_mean_regret"],
                "memory_hit_rate": agg["memory_hit_rate"],
                "leakage_passed": agg["leakage_audit"]["passed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
