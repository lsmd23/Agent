"""Lightweight logistic router trained from trajectory + oracle labels."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.phase4.route_features import FEATURE_NAMES, extract_features, feature_vector
from src.agent_attention_runtime import ModuleSpec, RuntimeState


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


@dataclass
class LearnedRouterPolicy:
    version: str
    feature_names: tuple[str, ...]
    weights: list[float]
    module_offsets: dict[str, float]
    training_rows: int
    training_accuracy: float

    def score_probability(self, features: dict[str, float], module_id: str) -> float:
        vector = feature_vector(features) + [1.0]
        offset = self.module_offsets.get(module_id, 0.0)
        linear = offset + sum(weight * value for weight, value in zip(self.weights, vector))
        return sigmoid(linear)

    def semantic_match(self, state: RuntimeState, module: ModuleSpec, query_tokens: set[str]) -> float:
        del query_tokens
        features = extract_features(
            state,
            module,
            task_family=self.task_family,
            memory_bonus=0.0,
        )
        return round(self.score_probability(features, module.module_id), 6)

    def bind_task_family(self, task_family: str) -> LearnedRouterPolicy:
        clone = LearnedRouterPolicy(
            version=self.version,
            feature_names=self.feature_names,
            weights=list(self.weights),
            module_offsets=dict(self.module_offsets),
            training_rows=self.training_rows,
            training_accuracy=self.training_accuracy,
        )
        clone.task_family = task_family
        return clone

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "feature_names": list(self.feature_names),
            "weights": self.weights,
            "module_offsets": self.module_offsets,
            "training_rows": self.training_rows,
            "training_accuracy": self.training_accuracy,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LearnedRouterPolicy:
        policy = cls(
            version=str(payload["version"]),
            feature_names=tuple(payload["feature_names"]),
            weights=[float(value) for value in payload["weights"]],
            module_offsets={str(key): float(value) for key, value in payload["module_offsets"].items()},
            training_rows=int(payload["training_rows"]),
            training_accuracy=float(payload["training_accuracy"]),
        )
        policy.task_family = ""
        return policy

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> LearnedRouterPolicy:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


def train_logistic_router(
    rows: list[tuple[dict[str, float], int, str]],
    *,
    version: str = "learned_router.v0.1",
    epochs: int = 250,
    learning_rate: float = 0.08,
) -> LearnedRouterPolicy:
    if not rows:
        raise ValueError("Cannot train learned router without training rows")

    feature_dim = len(FEATURE_NAMES) + 1
    weights = [0.0] * feature_dim
    module_offsets = {module_id: 0.0 for _, _, module_id in rows}

    for _ in range(epochs):
        for features, label, module_id in rows:
            vector = feature_vector(features) + [1.0]
            linear = module_offsets[module_id] + sum(w * x for w, x in zip(weights, vector))
            prediction = sigmoid(linear)
            error = prediction - float(label)
            for index, value in enumerate(vector):
                weights[index] -= learning_rate * error * value
            module_offsets[module_id] -= learning_rate * error

    correct = 0
    for features, label, module_id in rows:
        prediction = 1 if sigmoid(
            module_offsets[module_id] + sum(w * x for w, x in zip(weights, feature_vector(features) + [1.0]))
        ) >= 0.5 else 0
        if prediction == label:
            correct += 1

    policy = LearnedRouterPolicy(
        version=version,
        feature_names=FEATURE_NAMES,
        weights=weights,
        module_offsets=module_offsets,
        training_rows=len(rows),
        training_accuracy=round(correct / len(rows), 6),
    )
    policy.task_family = ""
    return policy
