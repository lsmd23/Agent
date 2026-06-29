#!/usr/bin/env python3
"""Unified real-LLM evaluation runner for all baseline families."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
from pathlib import Path
from typing import Any, Callable

import requests

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.baselines.faithful_runners import FAITHFUL_BASELINE_IDS  # noqa: E402
from experiments.baselines.memory_ablations import MEMORY_ABLATION_IDS  # noqa: E402
from experiments.phase4.learned_router_policy import LearnedRouterPolicy  # noqa: E402
from experiments.phase4.router_variants import PHASE4_ROUTER_IDS  # noqa: E402
from experiments.real_benchmarks.faithful_llm_runners import (  # noqa: E402
    FAITHFUL_LLM_ID_MAP,
    LLM_TO_FAITHFUL,
    MEMORY_LLM_ID_MAP,
    ROUTER_LLM_ID_MAP,
    run_faithful_llm,
    run_memory_ablation_llm,
    run_router_variant_llm,
)
from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402
from experiments.real_benchmarks.llm_client import LLMClient  # noqa: E402
from experiments.real_benchmarks.llm_react_agent import run_llm_react  # noqa: E402
from experiments.real_benchmarks.run_gsm8k_llm import load_jsonl, run_llm_direct  # noqa: E402

load_project_env(start=_ROOT)

STANDALONE_BASELINES = ("llm_direct_agent", "llm_react_agent")
FAITHFUL_LLM_BASELINES = tuple(FAITHFUL_LLM_ID_MAP.values())
MEMORY_LLM_BASELINES = tuple(MEMORY_LLM_ID_MAP.values())
ROUTER_LLM_BASELINES = tuple(ROUTER_LLM_ID_MAP.values())

ALL_REAL_LLM_BASELINES = (
    STANDALONE_BASELINES + FAITHFUL_LLM_BASELINES + MEMORY_LLM_BASELINES + ROUTER_LLM_BASELINES
)

SUITE_TASKS = {
    "gsm8k": "experiments/tasks/gsm8k_test_sample.jsonl",
    "phase1": "experiments/tasks/phase1_tasks.jsonl",
}


def summarize_by_baseline(trajectories: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"scope": "Unified real LLM evaluation.", "baselines": {}}
    for baseline_id, runs in trajectories.items():
        total = len(runs)
        correct = sum(1 for item in runs if item["final_success_label"] == "pass")
        partial = sum(1 for item in runs if item["final_success_label"] == "partial")
        latencies = [item["metrics_summary"]["latency_ms"] for item in runs]
        model_calls = [item["metrics_summary"].get("model_calls", 1) for item in runs]
        summary["baselines"][baseline_id] = {
            "runs": total,
            "accuracy": (correct / total) if total else None,
            "partial_rate": (partial / total) if total else None,
            "correct": correct,
            "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "mean_model_calls": round(sum(model_calls) / len(model_calls), 2) if model_calls else None,
        }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unified real-LLM evaluation.")
    parser.add_argument("--suite", choices=list(SUITE_TASKS), default="gsm8k")
    parser.add_argument("--tasks")
    parser.add_argument("--provider", choices=["openai", "ollama"], default=os.environ.get("LLM_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--baselines", nargs="+", choices=list(ALL_REAL_LLM_BASELINES))
    parser.add_argument("--family", choices=["standalone", "faithful", "memory", "router", "all"], default="all")
    parser.add_argument("--output-dir", default="experiments/llm_runs/real_eval")
    parser.add_argument("--summary-output")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--react-max-steps", type=int, default=4)
    parser.add_argument("--learned-policy", default="experiments/phase4/learned_router_policy.json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def baselines_for_family(family: str) -> list[str]:
    if family == "standalone":
        return list(STANDALONE_BASELINES)
    if family == "faithful":
        return list(FAITHFUL_LLM_BASELINES)
    if family == "memory":
        return list(MEMORY_LLM_BASELINES)
    if family == "router":
        return list(ROUTER_LLM_BASELINES)
    return list(ALL_REAL_LLM_BASELINES)


def resolve_runner(baseline_id: str) -> Callable[..., dict[str, Any]]:
    if baseline_id == "llm_direct_agent":
        return run_llm_direct
    if baseline_id == "llm_react_agent":
        return lambda task, client, **kwargs: run_llm_react(task, client, max_steps=kwargs.get("react_max_steps", 4))
    if baseline_id in LLM_TO_FAITHFUL:
        return lambda task, client, **kwargs: run_faithful_llm(baseline_id, task, client)
    for ablation_id, llm_id in MEMORY_LLM_ID_MAP.items():
        if baseline_id == llm_id:
            return lambda task, client, ablation_id=ablation_id, **kwargs: run_memory_ablation_llm(ablation_id, task, client)
    for router_id, llm_id in ROUTER_LLM_ID_MAP.items():
        if baseline_id == llm_id:
            return lambda task, client, router_id=router_id, **kwargs: run_router_variant_llm(
                router_id,
                task,
                client,
                learned_policy=kwargs.get("learned_policy"),
                oracle_utilities=kwargs.get("oracle_utilities"),
            )
    raise ValueError(f"Unknown baseline_id={baseline_id!r}")


def load_learned_policy(path: Path) -> LearnedRouterPolicy | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return LearnedRouterPolicy.from_dict(payload)


def main() -> None:
    args = parse_args()
    tasks_path = Path(args.tasks or SUITE_TASKS[args.suite])
    baselines = args.baselines or baselines_for_family(args.family)
    tasks = load_jsonl(tasks_path, args.limit)
    learned_policy = load_learned_policy(_ROOT / args.learned_policy)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "suite": args.suite,
                    "tasks": len(tasks),
                    "baselines": baselines,
                    "provider": args.provider,
                    "model": args.model,
                },
                indent=2,
            )
        )
        return

    output_root = Path(args.output_dir) / args.suite
    summary_path = Path(
        args.summary_output or f"experiments/metrics/real_llm_{args.suite}_summary.json"
    )
    trajectories: dict[str, list[dict[str, Any]]] = {baseline_id: [] for baseline_id in baselines}

    for task in tasks:
        oracle_utilities = None
        expected = task.get("expected_route", {})
        if expected.get("oracle_best_module_id"):
            oracle_utilities = {str(expected["oracle_best_module_id"]): 1.0}

        for baseline_id in baselines:
            client = LLMClient(
                provider=args.provider,
                model=args.model,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            runner = resolve_runner(baseline_id)
            try:
                trajectory = runner(
                    task,
                    client,
                    react_max_steps=args.react_max_steps,
                    learned_policy=learned_policy,
                    oracle_utilities=oracle_utilities,
                )
            except (requests.RequestException, urllib.error.URLError, RuntimeError) as error:
                raise SystemExit(
                    f"Model call failed baseline={baseline_id} task={task['task_id']}: {error}"
                ) from error

            baseline_dir = output_root / baseline_id
            baseline_dir.mkdir(parents=True, exist_ok=True)
            target = baseline_dir / f"{trajectory['run_id']}.json"
            target.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            trajectories[baseline_id].append(trajectory)
            print(
                json.dumps(
                    {
                        "baseline_id": baseline_id,
                        "task_id": task["task_id"],
                        "success": trajectory["final_success_label"],
                        "model_calls": trajectory["metrics_summary"].get("model_calls", 1),
                    },
                    ensure_ascii=False,
                )
            )

    summary = summarize_by_baseline(trajectories)
    summary["suite"] = args.suite
    summary["provider"] = args.provider
    summary["model"] = args.model
    summary["tasks"] = len(tasks)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "trajectory_dir": str(output_root)}, indent=2))


if __name__ == "__main__":
    main()
