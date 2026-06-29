"""Faithful baseline runtimes with real LLM module executors."""

from __future__ import annotations

from typing import Any

from experiments.baselines.common import memory_for_task, primary_executor_for_task
from experiments.baselines.faithful_runners import (
    FAITHFUL_BASELINE_IDS,
    AgentAttentionFaithfulRuntime,
    AgentAttentionTunedRuntime,
    FixedWorkflowRuntime,
    FullHistoryRuntime,
    MoAStyleRuntime,
    RetrievalMemoryRuntime,
    SingleReActRuntime,
    baseline_config_for,
    build_faithful_runtime,
    discouraged_modules_for_task,
)
from experiments.baselines.memory_ablations import ABLATION_SPECS, MEMORY_ABLATION_IDS, ablation_config_for
from experiments.phase4.learned_router_policy import LearnedRouterPolicy
from experiments.phase4.router_variants import (
    PHASE4_ROUTER_IDS,
    OracleRouterTunedRuntime,
    ROUTER_SPECS,
    router_config_for,
)
from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.llm_executors import default_module_specs, inject_llm_executors
from experiments.real_benchmarks.real_llm_envelope import envelope_for_real_llm
from experiments.real_benchmarks.run_gsm8k_llm import exact_match, extract_model_answer
from src.agent_attention_runtime import ModuleOutput, ModuleSpec, RuntimeState


FAITHFUL_LLM_ID_MAP = {
    "single_react_agent": "single_react_llm_agent",
    "fixed_workflow_agent": "fixed_workflow_llm_agent",
    "full_history_agent": "full_history_llm_agent",
    "retrieval_memory_agent": "retrieval_memory_llm_agent",
    "moa_style_agent": "moa_style_llm_agent",
    "agent_attention_agent": "agent_attention_llm_agent",
    "agent_attention_agent_tuned": "agent_attention_llm_tuned",
}
FAITHFUL_TOY_TO_LLM = FAITHFUL_LLM_ID_MAP
LLM_TO_FAITHFUL = {value: key for key, value in FAITHFUL_LLM_ID_MAP.items()}

MEMORY_LLM_ID_MAP = {ablation_id: f"{ablation_id}_llm" for ablation_id in MEMORY_ABLATION_IDS}
ROUTER_LLM_ID_MAP = {router_id: f"{router_id}_llm" for router_id in PHASE4_ROUTER_IDS}


class LLMExecutorMixin:
    """Inject LLM executors and log model_call events after each execute()."""

    client: LLMClient
    task: dict[str, Any]
    _logged_calls: int

    def _wire_llm(self, client: LLMClient, task: dict[str, Any], modules: list[ModuleSpec]) -> list[ModuleSpec]:
        self.client = client
        self.task = task
        self._logged_calls = 0

        def on_prediction(state: RuntimeState, prediction: str | None) -> None:
            if prediction:
                state.final_answer = state.final_answer or f"#### {prediction}"

        return inject_llm_executors(modules, client, task, on_prediction=on_prediction)

    def execute(self, state: RuntimeState, route: list) -> list[ModuleOutput]:  # type: ignore[no-untyped-def]
        outputs = super().execute(state, route)  # type: ignore[misc]
        for call in self.client.calls[self._logged_calls :]:
            self._log(
                state,
                "model_call",
                {
                    "provider": call["provider"],
                    "model": call["model"],
                    "module_id": call["module_id"],
                    "prompt": call["prompt"],
                    "output": call["output"],
                    "latency_ms": call["latency_ms"],
                    "usage": call["usage"],
                },
            )
        self._logged_calls = len(self.client.calls)
        return outputs


class SingleReActLLMRuntime(LLMExecutorMixin, SingleReActRuntime):
    baseline_id = "single_react_llm_agent"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class RetrievalMemoryLLMRuntime(LLMExecutorMixin, RetrievalMemoryRuntime):
    baseline_id = "retrieval_memory_llm_agent"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class FullHistoryLLMRuntime(LLMExecutorMixin, FullHistoryRuntime):
    baseline_id = "full_history_llm_agent"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class FixedWorkflowLLMRuntime(LLMExecutorMixin, FixedWorkflowRuntime):
    baseline_id = "fixed_workflow_llm_agent"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class MoAStyleLLMRuntime(LLMExecutorMixin, MoAStyleRuntime):
    baseline_id = "moa_style_llm_agent"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class AgentAttentionFaithfulLLMRuntime(LLMExecutorMixin, AgentAttentionFaithfulRuntime):
    baseline_id = "agent_attention_llm_agent"
    routing_policy_label = "lexical_sparse_llm"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class AgentAttentionTunedLLMRuntime(LLMExecutorMixin, AgentAttentionTunedRuntime):
    baseline_id = "agent_attention_llm_tuned"
    routing_policy_label = "lexical_sparse_adaptive_llm"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


class AgentAttentionTunedLLMRuntimeGSM8K(AgentAttentionTunedLLMRuntime):
    """GSM8K tuned runtime with exact-match verifier override."""

    def __init__(self, *, client: LLMClient, task: dict[str, Any], gold_answer: str, **kwargs: Any) -> None:
        self.gold_answer = gold_answer
        super().__init__(client=client, task=task, **kwargs)
        self.modules["verifier"].executor = self._gsm8k_verifier_executor

    def _gsm8k_verifier_executor(self, state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
        prediction = extract_model_answer(state.final_answer or "")
        passed = exact_match(prediction, self.gold_answer)
        content = (
            f"Verifier exact-match {'passed' if passed else 'failed'}: "
            f"prediction={prediction}, gold={self.gold_answer}"
        )
        return ModuleOutput(
            module_id=module.module_id,
            content=content,
            confidence=0.95 if passed else 0.2,
            failure_signal=None if passed else "exact_match_failed",
        )

    def maybe_verify(self, state: RuntimeState) -> dict:
        payload = super().maybe_verify(state)
        prediction = extract_model_answer(state.final_answer or "")
        if prediction and exact_match(prediction, self.gold_answer):
            state.verifier_status = "pass"
            payload["status"] = "pass"
        elif state.verifier_status == "pass" and not exact_match(prediction, self.gold_answer):
            state.verifier_status = "fail"
            payload["status"] = "fail"
        payload["prediction"] = prediction
        payload["gold_answer"] = self.gold_answer
        return payload


FAITHFUL_LLM_CLASSES = {
    "single_react_agent": SingleReActLLMRuntime,
    "fixed_workflow_agent": FixedWorkflowLLMRuntime,
    "full_history_agent": FullHistoryLLMRuntime,
    "retrieval_memory_agent": RetrievalMemoryLLMRuntime,
    "moa_style_agent": MoAStyleLLMRuntime,
    "agent_attention_agent": AgentAttentionFaithfulLLMRuntime,
    "agent_attention_agent_tuned": AgentAttentionTunedLLMRuntime,
}


def _faithful_common_kwargs(baseline_id: str, task: dict[str, Any], max_steps: int) -> dict[str, Any]:
    executor = primary_executor_for_task(task)
    discouraged = discouraged_modules_for_task(task)
    memory_enabled = baseline_id in {"retrieval_memory_agent", "agent_attention_agent", "agent_attention_agent_tuned"}
    memory = memory_for_task(task) if memory_enabled else []
    return {
        "executor_module": executor,
        "discouraged_modules": discouraged,
        "memory": memory,
        "max_steps": max_steps,
        "verifier_threshold": 0.64,
        "verifier_enabled": True,
        "task_family": task.get("task_family", ""),
    }


def build_faithful_llm_runtime(
    faithful_baseline_id: str,
    task: dict[str, Any],
    client: LLMClient,
    max_steps: int,
) -> LLMExecutorMixin:
    if faithful_baseline_id not in FAITHFUL_LLM_CLASSES:
        raise ValueError(f"Unknown faithful_baseline_id={faithful_baseline_id!r}")

    cls = FAITHFUL_LLM_CLASSES[faithful_baseline_id]
    common = _faithful_common_kwargs(faithful_baseline_id, task, max_steps)

    if faithful_baseline_id == "agent_attention_agent_tuned" and task.get("task_family") == "math_word_problem":
        return AgentAttentionTunedLLMRuntimeGSM8K(
            client=client,
            task=task,
            gold_answer=str(task["gold_answer"]),
            modules=default_module_specs(),
            memory_enabled=False,
            top_k=1,
            max_top_k=1,
            router_strategy="lexical",
            adaptive_top_k_enabled=False,
            strong_budget_gate=False,
            max_steps=max_steps,
            verifier_threshold=0.5,
            verifier_enabled=True,
        )

    kwargs: dict[str, Any] = {
        "client": client,
        "task": task,
        "modules": default_module_specs(),
        "max_steps": max_steps,
        "verifier_threshold": common["verifier_threshold"],
        "verifier_enabled": True,
    }

    if faithful_baseline_id in {"single_react_agent", "full_history_agent", "retrieval_memory_agent"}:
        kwargs["executor_module"] = common["executor_module"]
        kwargs["discouraged_modules"] = common["discouraged_modules"]
    if faithful_baseline_id == "fixed_workflow_agent":
        kwargs["executor_module"] = common["executor_module"]
        kwargs["memory_enabled"] = False
    if faithful_baseline_id == "single_react_agent":
        kwargs["memory_enabled"] = False
    if faithful_baseline_id == "full_history_agent":
        kwargs["memory_enabled"] = False
    if faithful_baseline_id == "retrieval_memory_agent":
        kwargs["memory"] = common["memory"]
        kwargs["memory_enabled"] = True
    if faithful_baseline_id == "moa_style_agent":
        kwargs["memory_enabled"] = False
    if faithful_baseline_id in {"agent_attention_agent", "agent_attention_agent_tuned"}:
        kwargs["memory"] = common["memory"]
        kwargs["memory_enabled"] = True

    return cls(**kwargs)


def build_memory_ablation_llm_runtime(
    ablation_id: str,
    task: dict[str, Any],
    client: LLMClient,
    max_steps: int,
) -> AgentAttentionTunedLLMRuntime:
    if ablation_id not in ABLATION_SPECS:
        raise ValueError(f"Unknown ablation_id={ablation_id!r}")
    spec = ABLATION_SPECS[ablation_id]
    memory_enabled = bool(spec["memory_enabled"])
    memory = (
        memory_for_task(task, quarantine_at_load=bool(spec.get("quarantine_at_load", True)))
        if memory_enabled
        else []
    )
    modules = default_module_specs()
    runtime = AgentAttentionTunedLLMRuntime(
        client=client,
        task=task,
        modules=modules,
        memory=memory,
        max_steps=max_steps,
        verifier_threshold=0.64,
        verifier_enabled=True,
        memory_enabled=memory_enabled,
        memory_write_enabled=bool(spec.get("memory_write_enabled", True)),
        memory_write_policy=str(spec.get("memory_write_policy", "success_plus_failure")),
        quarantine_aware=bool(spec.get("quarantine_aware", False)),
        adaptive_top_k_enabled=True,
        strong_budget_gate=True,
        budget_cost_fraction=0.30,
        cost_quality_epsilon=0.05,
        task_family=task.get("task_family", ""),
    )
    runtime.ablation_id = ablation_id
    return runtime


class OracleRouterLLMRuntime(LLMExecutorMixin, OracleRouterTunedRuntime):
    baseline_id = "agent_attention_llm_tuned_oracle"

    def __init__(self, *, client: LLMClient, task: dict[str, Any], **kwargs: Any) -> None:
        modules = self._wire_llm(client, task, kwargs.pop("modules", default_module_specs()))
        super().__init__(modules=modules, **kwargs)


def build_router_variant_llm_runtime(
    router_id: str,
    task: dict[str, Any],
    client: LLMClient,
    max_steps: int,
    *,
    learned_policy: LearnedRouterPolicy | None = None,
    oracle_utilities: dict[str, float] | None = None,
) -> LLMExecutorMixin:
    if router_id not in ROUTER_SPECS:
        raise ValueError(f"Unknown router_id={router_id!r}")

    spec = ROUTER_SPECS[router_id]
    memory = memory_for_task(task, quarantine_at_load=True)
    modules = default_module_specs()
    common: dict[str, Any] = {
        "client": client,
        "task": task,
        "modules": modules,
        "memory": memory,
        "max_steps": max_steps,
        "verifier_threshold": 0.64,
        "verifier_enabled": True,
        "memory_enabled": True,
        "memory_write_enabled": True,
        "memory_write_policy": "success_plus_failure",
        "quarantine_aware": False,
        "adaptive_top_k_enabled": True,
        "strong_budget_gate": True,
        "budget_cost_fraction": 0.30,
        "cost_quality_epsilon": 0.05,
        "task_family": task.get("task_family", ""),
    }

    if router_id == "aa_oracle_router":
        runtime = OracleRouterLLMRuntime(oracle_utilities=oracle_utilities or {}, **common)
        runtime.router_id = router_id
        return runtime

    if router_id == "aa_learned_router_replay":
        if learned_policy is None:
            raise ValueError("learned_policy is required for aa_learned_router_replay")
        bound = learned_policy.bind_task_family(task.get("task_family", ""))

        def semantic_fn(state, module, query_tokens):  # type: ignore[no-untyped-def]
            return bound.semantic_match(state, module, query_tokens)

        runtime = AgentAttentionTunedLLMRuntime(
            router_strategy="learned",
            learned_semantic_fn=semantic_fn,
            learned_router_version=bound.version,
            **common,
        )
        runtime.router_id = router_id
        return runtime

    runtime = AgentAttentionTunedLLMRuntime(router_strategy=spec["router_strategy"], **common)
    runtime.router_id = router_id
    return runtime


def run_faithful_llm(
    llm_baseline_id: str,
    task: dict[str, Any],
    client: LLMClient,
) -> dict[str, Any]:
    faithful_id = LLM_TO_FAITHFUL.get(llm_baseline_id)
    if faithful_id is None:
        raise ValueError(f"Unknown llm_baseline_id={llm_baseline_id!r}")
    budget = task.get("budget", {})
    max_steps = int(budget.get("max_steps", 4))
    max_budget = float(budget.get("max_activation_cost", 5.0))
    runtime = build_faithful_llm_runtime(faithful_id, task, client, max_steps)
    state = runtime.run(task["prompt"], max_budget=max_budget)
    return envelope_for_real_llm(
        task,
        llm_baseline_id,
        state,
        runtime.events,
        client,
        baseline_config=baseline_config_for(faithful_id),
        extra_known_deviations=[f"faithful_control_policy:{faithful_id}"],
    )


def run_memory_ablation_llm(ablation_id: str, task: dict[str, Any], client: LLMClient) -> dict[str, Any]:
    llm_ablation_id = MEMORY_LLM_ID_MAP.get(ablation_id, f"{ablation_id}_llm")
    budget = task.get("budget", {})
    max_steps = int(budget.get("max_steps", 4))
    max_budget = float(budget.get("max_activation_cost", 5.0))
    runtime = build_memory_ablation_llm_runtime(ablation_id, task, client, max_steps)
    state = runtime.run(task["prompt"], max_budget=max_budget)
    return envelope_for_real_llm(
        task,
        "agent_attention_llm_tuned",
        state,
        runtime.events,
        client,
        baseline_config=ablation_config_for(ablation_id),
        ablation_id=llm_ablation_id,
        extra_known_deviations=["memory_ablation_llm"],
    )


def run_router_variant_llm(
    router_id: str,
    task: dict[str, Any],
    client: LLMClient,
    *,
    learned_policy: LearnedRouterPolicy | None = None,
    oracle_utilities: dict[str, float] | None = None,
) -> dict[str, Any]:
    llm_router_id = ROUTER_LLM_ID_MAP.get(router_id, f"{router_id}_llm")
    budget = task.get("budget", {})
    max_steps = int(budget.get("max_steps", 4))
    max_budget = float(budget.get("max_activation_cost", 5.0))
    runtime = build_router_variant_llm_runtime(
        router_id,
        task,
        client,
        max_steps,
        learned_policy=learned_policy,
        oracle_utilities=oracle_utilities,
    )
    state = runtime.run(task["prompt"], max_budget=max_budget)
    return envelope_for_real_llm(
        task,
        "agent_attention_llm_tuned",
        state,
        runtime.events,
        client,
        baseline_config=router_config_for(router_id),
        router_id=llm_router_id,
        extra_known_deviations=["router_variant_llm"],
    )
