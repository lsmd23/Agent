"""Train learned router from oracle labels and trajectory replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.baselines.common import load_jsonl
from experiments.phase4.learned_router_policy import LearnedRouterPolicy, train_logistic_router
from experiments.phase4.oracle_matrix import build_oracle_matrix, oracle_label
from experiments.phase4.route_features import extract_features, features_from_route_event
from src.agent_attention_runtime import ModuleSpec, RuntimeState, build_default_runtime


def synthetic_oracle_rows(tasks: list[dict[str, Any]]) -> list[tuple[dict[str, float], int, str]]:
    template = build_default_runtime()
    rows: list[tuple[dict[str, float], int, str]] = []
    for task in tasks:
        state = RuntimeState(goal=task["prompt"], max_budget=float(task["budget"]["max_activation_cost"]))
        state.step = 1
        task_family = task.get("task_family", "")
        for module_id in ("memory", "code_agent", "search_agent", "critic_agent", "aggregator"):
            module = template.modules[module_id]
            features = extract_features(state, module, task_family=task_family)
            rows.append((features, oracle_label(task, module_id), module_id))
    return rows


def trajectory_rows(trajectory_paths: list[Path], tasks_by_id: dict[str, dict[str, Any]]) -> list[tuple[dict[str, float], int, str]]:
    rows: list[tuple[dict[str, float], int, str]] = []
    for path in trajectory_paths:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        task = tasks_by_id.get(envelope["task_id"])
        if task is None:
            continue
        goal = ""
        max_budget = float(task["budget"]["max_activation_cost"])
        for event in envelope.get("events", []):
            if event.get("kind") == "start":
                goal = str(event.get("payload", {}).get("goal", task["prompt"]))
            if event.get("kind") != "route":
                continue
            payload = event.get("payload", {})
            step = int(event.get("step", 1))
            rows.extend(features_from_route_event(task, payload, step=step, goal=goal, max_budget=max_budget))
    return rows


def train_policy(
    tasks_path: Path,
    trajectory_dir: Path | None = None,
    *,
    policy_output: Path,
    oracle_output: Path | None = None,
) -> tuple[LearnedRouterPolicy, dict[str, Any]]:
    tasks = load_jsonl(tasks_path)
    oracle_matrix = build_oracle_matrix(tasks)
    if oracle_output is not None:
        oracle_output.parent.mkdir(parents=True, exist_ok=True)
        oracle_output.write_text(json.dumps(oracle_matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rows = synthetic_oracle_rows(tasks)
    if trajectory_dir is not None:
        tasks_by_id = {task["task_id"]: task for task in tasks}
        paths = sorted(
            path
            for path in trajectory_dir.glob("*.json")
            if not path.name.endswith(".metrics.json")
        )
        rows.extend(trajectory_rows(paths, tasks_by_id))

    policy = train_logistic_router(rows)
    policy.save(policy_output)
    return policy, oracle_matrix
