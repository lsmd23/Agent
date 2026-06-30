#!/usr/bin/env python3
"""Lightweight route-selector diagnostic on oracle labels (Brief E)."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.baselines.common import load_jsonl
from experiments.real_benchmarks.code_verifier import fixture_dir_for_task, load_manifest


ROUTE_BASELINES = (
    "agent_attention_llm_tuned",
    "fixed_workflow_llm_agent",
    "moa_style_llm_agent",
    "retrieval_memory_llm_agent",
    "single_react_llm_agent",
)

ROUTE_FEATURE_NAMES = (
    "prompt_words",
    "prompt_has_memory",
    "prompt_has_refactor",
    "prompt_has_import",
    "prompt_has_edge",
    "prompt_has_parse",
    "prompt_has_security",
    "prompt_has_config",
    "prompt_has_doc",
    "prompt_has_workflow",
    "tag_memory",
    "tag_negative_transfer",
    "tag_edge_case",
    "tag_security",
    "tag_parsing",
    "tag_import",
    "tag_refactor",
    "tag_config",
    "tag_docs",
    "tag_pytest",
    "negative_transfer_probe",
    "memory_injected_count",
    "is_phase0_seed",
    "is_expanded_split",
    "fixture_desc_words",
    "fix_file_count",
    "matrix_successful_route_count",
    "matrix_min_success_model_calls",
    "matrix_route_entropy",
)

WORD_RE = re.compile(r"[a-z0-9_]+")


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def tokenize(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def task_slug(task_id: str) -> str:
    if task_id.startswith("phase0_seed_"):
        return task_id.removeprefix("phase0_seed_").removesuffix("_001")
    if task_id.startswith("phase1_code_"):
        return task_id.removeprefix("phase1_code_").removesuffix("_001")
    return task_id


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


def matrix_row_features(task_row: dict[str, Any]) -> dict[str, float]:
    successes = [
        bid
        for bid in ROUTE_BASELINES
        if task_row.get("baselines", {}).get(bid, {}).get("success")
    ]
    success_calls = [
        float(task_row["baselines"][bid].get("model_calls") or 0)
        for bid in successes
        if bid in task_row.get("baselines", {})
    ]
    winner_counts = Counter(
        bid
        for bid in ROUTE_BASELINES
        if task_row.get("baselines", {}).get(bid, {}).get("success")
    )
    return {
        "matrix_successful_route_count": float(len(successes)),
        "matrix_min_success_model_calls": float(min(success_calls)) if success_calls else 0.0,
        "matrix_route_entropy": round(entropy(winner_counts), 6),
    }


def extract_route_features(task: dict[str, Any], task_row: dict[str, Any]) -> dict[str, float]:
    prompt = str(task.get("prompt", ""))
    prompt_tokens = tokenize(prompt)
    tags = {str(tag).lower() for tag in task.get("tags", [])}
    memory_setup = task.get("memory_setup", {}) or {}
    injected = memory_setup.get("injected_memory_ids") or []
    negative_probe = bool((task.get("negative_transfer_probe") or {}).get("enabled"))

    fixture_desc = ""
    fix_file_count = 0.0
    fixture_dir = fixture_dir_for_task(str(task.get("task_id", "")))
    if fixture_dir is not None:
        manifest = load_manifest(fixture_dir)
        fixture_desc = str(manifest.get("description", ""))
        fix_file_count = float(len(manifest.get("fix_files") or []))

    features: dict[str, float] = {
        "prompt_words": float(len(prompt.split())),
        "prompt_has_memory": 1.0 if {"memory", "stale", "memories"} & prompt_tokens else 0.0,
        "prompt_has_refactor": 1.0 if {"refactor", "rename", "renamed"} & prompt_tokens else 0.0,
        "prompt_has_import": 1.0 if {"import", "module", "path", "helpers"} & prompt_tokens else 0.0,
        "prompt_has_edge": 1.0 if {"edge", "edge-case", "off-by-one", "exact"} & prompt_tokens else 0.0,
        "prompt_has_parse": 1.0
        if {"parse", "csv", "json", "int", "quoted", "split", "traverse", "nested"} & prompt_tokens
        else 0.0,
        "prompt_has_security": 1.0 if {"html", "sanitize", "escape", "tags", "strip"} & prompt_tokens else 0.0,
        "prompt_has_config": 1.0 if {"requirements", "dependency", "version", "config"} & prompt_tokens else 0.0,
        "prompt_has_doc": 1.0 if {"documentation", "doc", "examples"} & prompt_tokens else 0.0,
        "prompt_has_workflow": 1.0 if {"verify", "inspect", "minimal", "tests"} & prompt_tokens else 0.0,
        "tag_memory": 1.0 if "memory" in tags else 0.0,
        "tag_negative_transfer": 1.0 if "negative_transfer" in tags else 0.0,
        "tag_edge_case": 1.0 if "edge_case" in tags else 0.0,
        "tag_security": 1.0 if "security" in tags else 0.0,
        "tag_parsing": 1.0 if "parsing" in tags else 0.0,
        "tag_import": 1.0 if "import" in tags else 0.0,
        "tag_refactor": 1.0 if "refactor" in tags else 0.0,
        "tag_config": 1.0 if "config" in tags else 0.0,
        "tag_docs": 1.0 if "docs" in tags else 0.0,
        "tag_pytest": 1.0 if "pytest" in tags else 0.0,
        "negative_transfer_probe": 1.0 if negative_probe else 0.0,
        "memory_injected_count": float(len(injected)),
        "is_phase0_seed": 1.0 if str(task.get("task_id", "")).startswith("phase0_seed") else 0.0,
        "is_expanded_split": 1.0 if task.get("split") == "phase1_expanded" else 0.0,
        "fixture_desc_words": float(len(fixture_desc.split())),
        "fix_file_count": fix_file_count,
    }
    features.update(matrix_row_features(task_row))
    return features


def feature_vector(features: dict[str, float]) -> list[float]:
    return [float(features.get(name, 0.0)) for name in ROUTE_FEATURE_NAMES]


@dataclass
class RouteLogisticPolicy:
    feature_names: tuple[str, ...]
    route_weights: dict[str, list[float]]
    training_rows: int
    training_accuracy: float

    def route_scores(self, features: dict[str, float]) -> dict[str, float]:
        vector = feature_vector(features) + [1.0]
        return {
            route: sigmoid(sum(weight * value for weight, value in zip(self.route_weights[route], vector)))
            for route in ROUTE_BASELINES
        }

    def predict_route(self, features: dict[str, float]) -> str:
        scores = self.route_scores(features)
        return max(scores, key=lambda route: (scores[route], route))


def train_route_logistic(
    rows: list[tuple[dict[str, float], str]],
    *,
    epochs: int = 400,
    learning_rate: float = 0.06,
) -> RouteLogisticPolicy:
    if not rows:
        raise ValueError("Cannot train route selector without rows")

    feature_dim = len(ROUTE_FEATURE_NAMES) + 1
    route_weights = {route: [0.0] * feature_dim for route in ROUTE_BASELINES}

    for _ in range(epochs):
        for features, label in rows:
            vector = feature_vector(features) + [1.0]
            for route in ROUTE_BASELINES:
                target = 1.0 if route == label else 0.0
                weights = route_weights[route]
                linear = sum(weight * value for weight, value in zip(weights, vector))
                prediction = sigmoid(linear)
                error = prediction - target
                for index, value in enumerate(vector):
                    weights[index] -= learning_rate * error * value

    correct = 0
    policy = RouteLogisticPolicy(
        feature_names=ROUTE_FEATURE_NAMES,
        route_weights=route_weights,
        training_rows=len(rows),
        training_accuracy=0.0,
    )
    for features, label in rows:
        if policy.predict_route(features) == label:
            correct += 1
    policy.training_accuracy = round(correct / len(rows), 6)
    return policy


def predict_lexical_route(features: dict[str, float], task: dict[str, Any]) -> str:
    prompt = str(task.get("prompt", "")).lower()
    if features.get("negative_transfer_probe") or features.get("tag_negative_transfer"):
        return "retrieval_memory_llm_agent"
    if features.get("tag_memory") or "memory" in prompt or "stale" in prompt:
        return "retrieval_memory_llm_agent"
    if features.get("prompt_has_refactor") or features.get("tag_refactor"):
        return "moa_style_llm_agent"
    if features.get("prompt_has_edge") or features.get("tag_edge_case"):
        return "moa_style_llm_agent"
    if features.get("prompt_words", 0.0) <= 14.0:
        return "single_react_llm_agent"
    if features.get("prompt_has_workflow") or features.get("prompt_has_config"):
        return "fixed_workflow_llm_agent"
    return "single_react_llm_agent"


def predict_static_route(dominant_route: str) -> str:
    return dominant_route


def route_metrics(
    predictions: dict[str, str],
    labeled_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not labeled_rows:
        return {
            "tasks": 0,
            "route_accuracy": 0.0,
            "mean_regret_vs_oracle_reward": 0.0,
            "mean_cost_normalized_success": 0.0,
            "success_rate": 0.0,
            "confusion": {},
        }

    correct = 0
    regrets: list[float] = []
    costs: list[float] = []
    successes: list[float] = []
    confusion: Counter[tuple[str, str]] = Counter()

    for row in labeled_rows:
        task_id = row["task_id"]
        label = row["cheapest_successful_route"]
        predicted = predictions[task_id]
        if predicted == label:
            correct += 1
        confusion[(label, predicted)] += 1
        baseline = row.get("baselines", {}).get(predicted, {})
        regrets.append(float(baseline.get("regret_vs_oracle_reward", row["oracle_route_reward"])))
        costs.append(float(baseline.get("cost_normalized_success", 0.0)))
        successes.append(1.0 if baseline.get("success") else 0.0)

    return {
        "tasks": len(labeled_rows),
        "route_accuracy": round(correct / len(labeled_rows), 6),
        "mean_regret_vs_oracle_reward": round(sum(regrets) / len(regrets), 6),
        "mean_cost_normalized_success": round(sum(costs) / len(costs), 6),
        "success_rate": round(sum(successes) / len(successes), 6),
        "confusion": {
            f"{gold}->{pred}": count for (gold, pred), count in sorted(confusion.items())
        },
    }


def build_examples(
    matrix: dict[str, Any],
    tasks_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for row in matrix.get("per_task", []):
        task_id = str(row["task_id"])
        task = tasks_by_id.get(task_id)
        if task is None:
            continue
        label = row.get("cheapest_successful_route")
        if not label:
            continue
        features = extract_route_features(task, row)
        examples.append(
            {
                "task_id": task_id,
                "task_slug": task_slug(task_id),
                "split": task.get("split", "unknown"),
                "label": label,
                "features": features,
                "task": task,
                "matrix_row": row,
            }
        )
    return examples


def split_examples(
    examples: list[dict[str, Any]],
    *,
    strategy: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if strategy == "split_field":
        train = [ex for ex in examples if ex["split"] != "phase1_expanded"]
        test = [ex for ex in examples if ex["split"] == "phase1_expanded"]
        return train, test

    if strategy == "task_slug":
        slugs = sorted({ex["task_slug"] for ex in examples})
        holdout = set(slugs[::5])  # deterministic ~20% slug families
        train = [ex for ex in examples if ex["task_slug"] not in holdout]
        test = [ex for ex in examples if ex["task_slug"] in holdout]
        return train, test

    raise ValueError(f"Unknown split strategy: {strategy}")


def dominant_cheapest_route(examples: list[dict[str, Any]]) -> str:
    counts = Counter(ex["label"] for ex in examples)
    return counts.most_common(1)[0][0]


def classify_outcome(
    *,
    learned: dict[str, Any],
    static: dict[str, Any],
    lexical: dict[str, Any],
    held_out_tasks: int,
) -> str:
    if held_out_tasks < 8:
        return "weak_or_inconclusive"

    regret_gain_static = static["mean_regret_vs_oracle_reward"] - learned["mean_regret_vs_oracle_reward"]
    regret_gain_lexical = lexical["mean_regret_vs_oracle_reward"] - learned["mean_regret_vs_oracle_reward"]
    accuracy_gain_static = learned["route_accuracy"] - static["route_accuracy"]

    if regret_gain_static >= 0.02 and regret_gain_lexical >= 0.01:
        return "supports_direction"
    if regret_gain_static >= 0.005 or accuracy_gain_static >= 0.05:
        return "weak_or_inconclusive"
    if learned["mean_regret_vs_oracle_reward"] <= min(
        static["mean_regret_vs_oracle_reward"],
        lexical["mean_regret_vs_oracle_reward"],
    ):
        return "weak_or_inconclusive"
    return "falsified_or_blocked"


def render_audit_markdown(result: dict[str, Any]) -> str:
    held = result["held_out"]["learned_logistic"]
    static = result["held_out"]["static_dominant"]
    lexical = result["held_out"]["lexical_rules"]
    split = result["split"]
    outcome = result["evidence_outcome"]

    lines = [
        "# Route Selector Diagnostic (Brief E)",
        "",
        "## Scope",
        "",
        "Lightweight route classifier diagnostic on the 26-task code suite using oracle "
        "`cheapest_successful_route` labels from Brief A. Replay-only; no new LLM calls.",
        "",
        "## Inputs Read",
        "",
        f"- `{result['inputs']['oracle_route_matrix']}`",
        f"- `{result['inputs']['task_manifest']}`",
        "- Fixture manifests under `experiments/fixtures/code/`",
        "- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief E)",
        "",
        "## Method",
        "",
        f"- Label: `cheapest_successful_route` from oracle route matrix.",
        f"- Features: task prompt/tags/memory flags, fixture metadata, and matrix-row difficulty "
        f"signals (`matrix_successful_route_count`, min successful calls, route entropy).",
        f"- Train: logistic one-vs-rest route ranker on {split['train_tasks']} tasks.",
        f"- Held-out split: `{split['strategy']}` ({split['test_tasks']} tasks).",
        "- Baselines: static dominant cheapest route; lexical/tag rule router.",
        "- Metrics: route accuracy, mean regret vs oracle reward, cost-normalized success, success rate.",
        "",
        "## Commands Run",
        "",
        "```bash",
        "python3 experiments/analysis/route_selector_diagnostic.py",
        "```",
        "",
        "## Artifacts Created",
        "",
        "- `experiments/metrics/route_selector_diagnostic.json`",
        "- `experiments/analysis/route_selector_audit.md`",
        "",
        "## Results",
        "",
        "### Held-out comparison",
        "",
        "| Policy | Route accuracy | Mean regret | Cost-norm success | Success rate |",
        "|--------|----------------|-------------|-------------------|--------------|",
        f"| Learned logistic | {held['route_accuracy']:.1%} | {held['mean_regret_vs_oracle_reward']:.4f} | "
        f"{held['mean_cost_normalized_success']:.4f} | {held['success_rate']:.1%} |",
        f"| Static dominant | {static['route_accuracy']:.1%} | {static['mean_regret_vs_oracle_reward']:.4f} | "
        f"{static['mean_cost_normalized_success']:.4f} | {static['success_rate']:.1%} |",
        f"| Lexical rules | {lexical['route_accuracy']:.1%} | {lexical['mean_regret_vs_oracle_reward']:.4f} | "
        f"{lexical['mean_cost_normalized_success']:.4f} | {lexical['success_rate']:.1%} |",
        "",
        f"- Training accuracy (in-split): {result['train']['learned_logistic']['route_accuracy']:.1%} "
        f"on {split['train_tasks']} tasks.",
        f"- Dominant training cheapest route: `{result['dominant_cheapest_route']}`.",
        "",
        "### Learned held-out confusion (gold -> pred)",
        "",
    ]
    if held["confusion"]:
        for key, count in held["confusion"].items():
            lines.append(f"- `{key}`: {count}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ]
    )
    if outcome == "supports_direction":
        lines.append(
            "Cheap task features predict the oracle cheapest route on held-out tasks well enough "
            "to beat static and lexical routing on regret."
        )
    elif outcome == "weak_or_inconclusive":
        lines.append(
            "At N=26 with a small train split, results are diagnostic only. Some signal may exist, "
            "but regret gains over static/lexical baselines are not strong enough for production routing."
        )
    else:
        lines.append(
            "Task metadata features do not reliably beat static or lexical routing on held-out regret. "
            "Learned route selection should stay offline/diagnostic on this suite."
        )

    lines.extend(
        [
            "",
            f"**Evidence outcome:** `{outcome}`",
            "",
            "## Next Questions",
            "",
            "- Brief B: cascade rescue on oracle-failure subsets without relying on a learned upfront router.",
            "- Expand suite / harder splits before live learned routing.",
            "- Brief H: check whether route winners correlate with proposer specialization rather than prompt tags.",
            "",
        ]
    )
    return "\n".join(lines)


def run_diagnostic(
    *,
    oracle_path: Path,
    tasks_path: Path,
    split_strategy: str = "split_field",
) -> dict[str, Any]:
    matrix = json.loads(oracle_path.read_text(encoding="utf-8"))
    tasks = load_jsonl(tasks_path)
    tasks_by_id = {task["task_id"]: task for task in tasks}
    examples = build_examples(matrix, tasks_by_id)
    train_examples, test_examples = split_examples(examples, strategy=split_strategy)
    dominant = dominant_cheapest_route(train_examples or examples)

    train_rows = [(ex["features"], ex["label"]) for ex in train_examples]
    policy = train_route_logistic(train_rows)

    def evaluate_split(split_examples_list: list[dict[str, Any]], train_for_static: list[dict[str, Any]]) -> dict[str, Any]:
        static_route = dominant_cheapest_route(train_for_static or split_examples_list)
        learned_predictions = {
            ex["task_id"]: policy.predict_route(ex["features"]) for ex in split_examples_list
        }
        static_predictions = {
            ex["task_id"]: predict_static_route(static_route) for ex in split_examples_list
        }
        lexical_predictions = {
            ex["task_id"]: predict_lexical_route(ex["features"], ex["task"]) for ex in split_examples_list
        }
        matrix_rows = [ex["matrix_row"] for ex in split_examples_list]
        return {
            "static_dominant": route_metrics(static_predictions, matrix_rows),
            "lexical_rules": route_metrics(lexical_predictions, matrix_rows),
            "learned_logistic": route_metrics(learned_predictions, matrix_rows),
            "static_route": static_route,
        }

    train_eval = evaluate_split(train_examples, train_examples)
    held_out = evaluate_split(test_examples, train_examples)

    outcome = classify_outcome(
        learned=held_out["learned_logistic"],
        static=held_out["static_dominant"],
        lexical=held_out["lexical_rules"],
        held_out_tasks=held_out["learned_logistic"]["tasks"],
    )

    return {
        "scope": "Lightweight route-selector diagnostic (Brief E).",
        "inputs": {
            "oracle_route_matrix": str(oracle_path),
            "task_manifest": str(tasks_path),
        },
        "suite": matrix.get("suite"),
        "tasks": len(examples),
        "split": {
            "strategy": split_strategy,
            "train_tasks": len(train_examples),
            "test_tasks": len(test_examples),
            "train_task_ids": [ex["task_id"] for ex in train_examples],
            "test_task_ids": [ex["task_id"] for ex in test_examples],
        },
        "dominant_cheapest_route": dominant,
        "feature_names": list(ROUTE_FEATURE_NAMES),
        "train": train_eval,
        "held_out": held_out,
        "policy": {
            "type": "logistic_one_vs_rest",
            "training_rows": policy.training_rows,
            "training_accuracy": policy.training_accuracy,
            "route_weights": policy.route_weights,
        },
        "evidence_outcome": outcome,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train/evaluate lightweight route selector (Brief E).")
    parser.add_argument("--oracle-matrix", default="experiments/metrics/oracle_route_matrix.json")
    parser.add_argument("--tasks", default="experiments/tasks/phase1_code_all.jsonl")
    parser.add_argument("--split", default="split_field", choices=("split_field", "task_slug"))
    parser.add_argument("--output-json", default="experiments/metrics/route_selector_diagnostic.json")
    parser.add_argument("--output-md", default="experiments/analysis/route_selector_audit.md")
    args = parser.parse_args()

    result = run_diagnostic(
        oracle_path=Path(args.oracle_matrix),
        tasks_path=Path(args.tasks),
        split_strategy=args.split,
    )

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
                "evidence_outcome": result["evidence_outcome"],
                "held_out_accuracy": result["held_out"]["learned_logistic"]["route_accuracy"],
                "held_out_regret_learned": result["held_out"]["learned_logistic"]["mean_regret_vs_oracle_reward"],
                "held_out_regret_static": result["held_out"]["static_dominant"]["mean_regret_vs_oracle_reward"],
                "held_out_regret_lexical": result["held_out"]["lexical_rules"]["mean_regret_vs_oracle_reward"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
