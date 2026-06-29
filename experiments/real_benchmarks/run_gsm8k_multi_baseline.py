#!/usr/bin/env python3
"""Compare real-LLM GSM8K baselines: direct, ReAct, Agent-Attention."""

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

from experiments.real_benchmarks.agent_attention_llm_runtime import run_agent_attention_llm  # noqa: E402
from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402
from experiments.real_benchmarks.llm_client import LLMClient  # noqa: E402
from experiments.real_benchmarks.llm_react_agent import run_llm_react  # noqa: E402
from experiments.real_benchmarks.run_gsm8k_llm import load_jsonl, run_llm_direct  # noqa: E402

load_project_env(start=_ROOT)

BASELINES: dict[str, Callable[[dict[str, Any], LLMClient], dict[str, Any]]] = {
    "llm_direct_agent": run_llm_direct,
    "llm_react_agent": run_llm_react,
    "agent_attention_llm_tuned": run_agent_attention_llm,
}


def summarize_by_baseline(trajectories: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"scope": "Real LLM GSM8K multi-baseline comparison.", "baselines": {}}
    for baseline_id, runs in trajectories.items():
        total = len(runs)
        correct = sum(1 for item in runs if item["final_success_label"] == "pass")
        latencies = [item["metrics_summary"]["latency_ms"] for item in runs]
        model_calls = [item["metrics_summary"].get("model_calls", 1) for item in runs]
        summary["baselines"][baseline_id] = {
            "runs": total,
            "accuracy": (correct / total) if total else None,
            "correct": correct,
            "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "mean_model_calls": round(sum(model_calls) / len(model_calls), 2) if model_calls else None,
            "results": [
                {
                    "task_id": item["task_id"],
                    "success": item["final_success_label"],
                    "prediction": item["metrics_summary"]["prediction"],
                    "gold_answer": item["metrics_summary"]["gold_answer"],
                    "latency_ms": item["metrics_summary"]["latency_ms"],
                    "model_calls": item["metrics_summary"].get("model_calls", 1),
                }
                for item in runs
            ],
        }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GSM8K multi-baseline real LLM comparison.")
    parser.add_argument("--tasks", default="experiments/tasks/gsm8k_test_sample.jsonl")
    parser.add_argument("--provider", choices=["openai", "ollama"], default=os.environ.get("LLM_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--baselines",
        nargs="+",
        choices=list(BASELINES),
        default=list(BASELINES),
    )
    parser.add_argument("--output-dir", default="experiments/llm_runs/gsm8k/multi_baseline")
    parser.add_argument("--summary-output", default="experiments/metrics/gsm8k_multi_baseline_summary.json")
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--react-max-steps", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run_baseline(
    baseline_id: str,
    task: dict[str, Any],
    client: LLMClient,
    *,
    react_max_steps: int,
) -> dict[str, Any]:
    if baseline_id == "llm_react_agent":
        return run_llm_react(task, client, max_steps=react_max_steps)
    return BASELINES[baseline_id](task, client)


def main() -> None:
    args = parse_args()
    tasks = load_jsonl(Path(args.tasks), args.limit)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "provider": args.provider,
                    "model": args.model,
                    "tasks": len(tasks),
                    "baselines": args.baselines,
                },
                indent=2,
            )
        )
        return

    output_root = Path(args.output_dir)
    trajectories: dict[str, list[dict[str, Any]]] = {baseline_id: [] for baseline_id in args.baselines}

    for task in tasks:
        for baseline_id in args.baselines:
            client = LLMClient(
                provider=args.provider,
                model=args.model,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            try:
                trajectory = run_baseline(
                    baseline_id,
                    task,
                    client,
                    react_max_steps=args.react_max_steps,
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
                        "prediction": trajectory["metrics_summary"]["prediction"],
                        "model_calls": trajectory["metrics_summary"].get("model_calls", 1),
                    },
                    ensure_ascii=False,
                )
            )

    summary = summarize_by_baseline(trajectories)
    summary["provider"] = args.provider
    summary["model"] = args.model
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "trajectory_dir": args.output_dir}, indent=2))


if __name__ == "__main__":
    main()
