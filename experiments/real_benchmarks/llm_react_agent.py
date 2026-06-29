"""Real LLM ReAct multi-turn baseline for GSM8K."""

from __future__ import annotations

import time
from typing import Any

from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.run_gsm8k_llm import build_prompt, exact_match, extract_model_answer


def build_react_prompt(task_prompt: str, scratchpad: list[str]) -> str:
    header = (
        "Solve the grade-school math word problem. "
        "Think step by step. Put the final numeric answer on a line starting with '####'.\n\n"
        f"Problem: {task_prompt}\n"
    )
    if not scratchpad:
        return header + "\nStep 1:"
    joined = "\n\n".join(f"Step {index + 1}:\n{text}" for index, text in enumerate(scratchpad))
    return header + joined + f"\n\nStep {len(scratchpad) + 1}:"


def run_llm_react(task: dict[str, Any], client: LLMClient, *, max_steps: int = 4) -> dict[str, Any]:
    scratchpad: list[str] = []
    events: list[dict[str, Any]] = [
        {
            "event_id": 1,
            "step": 0,
            "kind": "start",
            "payload": {
                "goal": task["prompt"],
                "baseline_id": "llm_react_agent",
                "provider": client.provider,
                "model": client.model,
                "max_steps": max_steps,
            },
            "timestamp": time.time(),
        }
    ]
    event_id = 2
    prediction: str | None = None
    output_text = ""

    for step in range(1, max_steps + 1):
        prompt = build_react_prompt(task["prompt"], scratchpad)
        text, metadata, latency_ms = client.complete(prompt, module_id="llm_react_agent")
        scratchpad.append(text)
        output_text = text
        prediction = extract_model_answer(text)
        events.append(
            {
                "event_id": event_id,
                "step": step,
                "kind": "model_call",
                "payload": {
                    "provider": client.provider,
                    "model": client.model,
                    "prompt": prompt,
                    "output": text,
                    "prediction": prediction,
                    "latency_ms": latency_ms,
                    "usage": metadata,
                },
                "timestamp": time.time(),
            }
        )
        event_id += 1
        if prediction is not None:
            break

    passed = exact_match(prediction, task["gold_answer"])
    events.extend(
        [
            {
                "event_id": event_id,
                "step": step,
                "kind": "verifier_result",
                "payload": {
                    "enabled": True,
                    "status": "pass" if passed else "fail",
                    "reason": "exact_numeric_match" if passed else "numeric_mismatch",
                    "prediction": prediction,
                    "gold_answer": task["gold_answer"],
                },
                "timestamp": time.time(),
            },
            {
                "event_id": event_id + 1,
                "step": step,
                "kind": "finish",
                "payload": {
                    "final_answer": output_text,
                    "selected_modules": ["llm_react_agent"] * len(scratchpad),
                    "failure_signals": [] if passed else ["exact_match_failed"],
                },
                "timestamp": time.time(),
            },
        ]
    )
    total_latency = sum(call["latency_ms"] for call in client.calls)
    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": f"real_gsm8k__react__{client.provider}__{client.model.replace('/', '_')}__{task['task_id']}",
        "task_id": task["task_id"],
        "benchmark_id": task["benchmark_id"],
        "baseline_id": "llm_react_agent",
        "runtime_config": {
            "provider": client.provider,
            "model": client.model,
            "max_steps": max_steps,
            "model_calls": len(client.calls),
        },
        "task_family": task.get("task_family", "math_word_problem"),
        "events": events,
        "final_answer": output_text,
        "final_success_label": "pass" if passed else "fail",
        "failure_reason": None if passed else "exact_match_failed",
        "known_deviations": [
            "real_llm_react_multi_turn",
            "gsm8k_exact_match_only",
            "no_agent_attention_routing",
        ],
        "metrics_summary": {
            "prediction": prediction,
            "gold_answer": task["gold_answer"],
            "exact_match": passed,
            "model_calls": len(client.calls),
            "latency_ms": total_latency,
        },
    }
