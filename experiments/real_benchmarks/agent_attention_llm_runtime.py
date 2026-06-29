"""Agent-Attention runtime with real LLM module executors (backward-compatible shim)."""

from __future__ import annotations

from typing import Any

from experiments.real_benchmarks.faithful_llm_runners import (
    AgentAttentionTunedLLMRuntime,
    AgentAttentionTunedLLMRuntimeGSM8K,
    build_faithful_llm_runtime,
    run_faithful_llm,
)
from experiments.real_benchmarks.llm_client import LLMClient

AgentAttentionLLMRuntime = AgentAttentionTunedLLMRuntimeGSM8K


def build_agent_attention_llm_runtime(task: dict[str, Any], client: LLMClient) -> AgentAttentionTunedLLMRuntimeGSM8K:
    budget = task.get("budget", {})
    max_steps = int(budget.get("max_steps", 4))
    return build_faithful_llm_runtime("agent_attention_agent_tuned", task, client, max_steps)  # type: ignore[return-value]


def run_agent_attention_llm(task: dict[str, Any], client: LLMClient) -> dict[str, Any]:
    return run_faithful_llm("agent_attention_llm_tuned", task, client)
