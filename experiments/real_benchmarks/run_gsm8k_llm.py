#!/usr/bin/env python3
"""Run a real LLM on a small GSM8K sample.

Supported backends:
- openai-compatible chat completions via OPENAI_API_KEY / OPENAI_BASE_URL
- ollama local chat API via OLLAMA_BASE_URL

This script performs actual model calls unless --dry-run is set. Dry-run only
validates configuration and task parsing; it does not write benchmark results.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

import requests

from experiments.real_benchmarks.llm_client import LLMClient, model_call

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402

load_project_env(start=_ROOT)


NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def normalize_number(text: str) -> str | None:
    text = text.replace(",", "").strip()
    matches = NUMBER_RE.findall(text)
    if not matches:
        return None
    value = matches[-1]
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value


def extract_model_answer(text: str) -> str | None:
    for marker in ["####", "Final answer:", "Answer:", "final answer is"]:
        if marker in text:
            candidate = text.split(marker)[-1]
            normalized = normalize_number(candidate)
            if normalized is not None:
                return normalized
    return normalize_number(text)


def exact_match(prediction: str | None, gold: str) -> bool:
    return prediction is not None and normalize_number(prediction) == normalize_number(gold)


def build_prompt(question: str) -> str:
    return (
        "Solve the following grade-school math word problem. "
        "Reason briefly, then put the final numeric answer on a line starting with '####'.\n\n"
        f"Problem: {question}"
    )


def trajectory_for(
    task: dict[str, Any],
    provider: str,
    model: str,
    prompt: str,
    output_text: str,
    metadata: dict[str, Any],
    latency_ms: int,
) -> dict[str, Any]:
    prediction = extract_model_answer(output_text)
    passed = exact_match(prediction, task["gold_answer"])
    run_id = f"real_gsm8k__{provider}__{model.replace('/', '_')}__{task['task_id']}"
    events = [
        {
            "event_id": 1,
            "step": 0,
            "kind": "start",
            "payload": {
                "goal": task["prompt"],
                "task_id": task["task_id"],
                "benchmark_id": task["benchmark_id"],
                "baseline_id": "llm_direct_agent",
                "provider": provider,
                "model": model,
            },
            "timestamp": time.time(),
        },
        {
            "event_id": 2,
            "step": 1,
            "kind": "model_call",
            "payload": {
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "output": output_text,
                "prediction": prediction,
                "gold_answer": task["gold_answer"],
                "latency_ms": latency_ms,
                "usage": metadata,
            },
            "timestamp": time.time(),
        },
        {
            "event_id": 3,
            "step": 1,
            "kind": "verifier_result",
            "payload": {
                "enabled": True,
                "required": True,
                "status": "pass" if passed else "fail",
                "reason": "exact_numeric_match" if passed else "numeric_mismatch",
                "prediction": prediction,
                "gold_answer": task["gold_answer"],
            },
            "timestamp": time.time(),
        },
        {
            "event_id": 4,
            "step": 1,
            "kind": "halt_gate",
            "payload": {
                "halt": True,
                "reason": "answer_ready" if passed else "oracle_failed",
                "success_signal": "pass" if passed else "fail",
                "verifier_status": "pass" if passed else "fail",
                "budget_snapshot": {"remaining_budget": 0},
            },
            "timestamp": time.time(),
        },
        {
            "event_id": 5,
            "step": 1,
            "kind": "finish",
            "payload": {
                "final_answer": output_text,
                "selected_modules": ["llm_direct_agent", "exact_match_verifier"],
                "failure_signals": [] if passed else ["exact_match_failed"],
            },
            "timestamp": time.time(),
        },
    ]
    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": run_id,
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": "llm_direct_agent",
        "runtime_config": {
            "provider": provider,
            "model": model,
            "temperature": task["budget"]["temperature"],
            "max_tokens": task["budget"]["max_tokens"],
        },
        "task_family": task["task_family"],
        "events": events,
        "final_answer": output_text,
        "final_success_label": "pass" if passed else "fail",
        "failure_reason": None if passed else "exact_match_failed",
        "known_deviations": [
            "single_call_llm_baseline",
            "gsm8k_exact_match_only",
            "no_agent_attention_routing",
            "no_token_price_normalization",
        ],
        "metrics_summary": {
            "prediction": prediction,
            "gold_answer": task["gold_answer"],
            "exact_match": passed,
            "latency_ms": latency_ms,
        },
    }


def run_llm_direct(task: dict[str, Any], client: LLMClient) -> dict[str, Any]:
    prompt = build_prompt(task["prompt"])
    output_text, metadata, latency_ms = client.complete(prompt, module_id="llm_direct_agent")
    return trajectory_for(task, client.provider, client.model, prompt, output_text, metadata, latency_ms)


def write_summary(trajectories: list[dict[str, Any]], output: Path) -> None:
    total = len(trajectories)
    correct = sum(1 for item in trajectories if item["final_success_label"] == "pass")
    latencies = [item["metrics_summary"]["latency_ms"] for item in trajectories]
    summary = {
        "scope": "Real LLM GSM8K exact-match evaluation.",
        "runs": total,
        "accuracy": (correct / total) if total else None,
        "correct": correct,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "known_deviations": sorted({dev for item in trajectories for dev in item["known_deviations"]}),
        "results": [
            {
                "task_id": item["task_id"],
                "success": item["final_success_label"],
                "prediction": item["metrics_summary"]["prediction"],
                "gold_answer": item["metrics_summary"]["gold_answer"],
                "latency_ms": item["metrics_summary"]["latency_ms"],
            }
            for item in trajectories
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real LLM on a GSM8K sample.")
    parser.add_argument("--tasks", default="experiments/tasks/gsm8k_test_sample.jsonl")
    parser.add_argument("--provider", choices=["openai", "ollama"], default=os.environ.get("LLM_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-dir", default="experiments/llm_runs/gsm8k")
    parser.add_argument("--summary-output", default="experiments/metrics/gsm8k_llm_summary.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate task/provider setup without making model calls.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_jsonl(Path(args.tasks), args.limit)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "provider": args.provider, "model": args.model, "tasks": len(tasks)}, indent=2))
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trajectories: list[dict[str, Any]] = []
    for task in tasks:
        prompt = build_prompt(task["prompt"])
        started = time.time()
        try:
            output_text, metadata = model_call(
                args.provider,
                args.model,
                prompt,
                int(task["budget"]["max_tokens"]),
                float(task["budget"]["temperature"]),
            )
        except (requests.RequestException, urllib.error.URLError, RuntimeError) as error:
            raise SystemExit(f"Model call failed for {task['task_id']}: {error}") from error
        latency_ms = int((time.time() - started) * 1000)
        trajectory = trajectory_for(task, args.provider, args.model, prompt, output_text, metadata, latency_ms)
        target = output_dir / f"{trajectory['run_id']}.json"
        target.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        trajectories.append(trajectory)
        print(json.dumps({"task_id": task["task_id"], "success": trajectory["final_success_label"], "prediction": trajectory["metrics_summary"]["prediction"]}, ensure_ascii=False))
    write_summary(trajectories, Path(args.summary_output))
    print(json.dumps({"runs": len(trajectories), "summary": args.summary_output, "trajectory_dir": args.output_dir}, indent=2))


if __name__ == "__main__":
    main()
