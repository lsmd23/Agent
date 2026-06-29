"""Shared LLM module executors for real benchmark runners."""

from __future__ import annotations

from typing import Any, Callable

from experiments.real_benchmarks.code_verifier import (
    build_fixture_context,
    fix_paths_for_task,
    select_code_patch,
)
from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.run_gsm8k_llm import extract_model_answer
from src.agent_attention_runtime import ModuleOutput, ModuleSpec, RuntimeState, build_default_runtime


MODULE_ROLES: dict[str, str] = {
    "code_agent": (
        "You are the primary code repair module. "
        "Inspect the repository snapshot and failing tests, then produce the minimal fix. "
        "Output the complete corrected file in a fenced ```python block. "
        "The first line inside the block must be `# file: <relative/path>`."
    ),
    "search_agent": (
        "You are a search/evidence module. Restate known facts from the problem "
        "and identify what evidence or computation is still needed."
    ),
    "critic_agent": (
        "You are a critic module. Review prior reasoning for mistakes or missing steps. "
        "For code repair tasks, output a corrected ```python block with `# file: <path>` when possible. "
        "For numeric answers end with #### <number> when applicable."
    ),
    "aggregator": (
        "You are the aggregator module. Read prior module outputs and produce the best final answer. "
        "For code repair tasks, output ONLY one ```python block with `# file: <path>` and full file contents. "
        "End with #### <number> when the task expects a numeric result."
    ),
    "memory": (
        "You are a memory reflection module. Summarize reusable lessons from prior steps briefly."
    ),
}

CODE_PATCH_MODULES = {"code_agent", "aggregator", "critic_agent"}


def observation_context(state: RuntimeState) -> str:
    if not state.observations:
        return "(none)"
    return "\n".join(f"- {obs}" for obs in state.observations[-10:])


def code_task_context(task: dict[str, Any] | None) -> str:
    if not task or task.get("task_family") != "code_agent_task":
        return ""
    task_id = task.get("task_id", "")
    fixture_context = build_fixture_context(task_id) if task_id else None
    if not fixture_context:
        return "This is a code repair/debug task. Provide a ```python patch block with `# file: <path>`.\n"
    return f"This is an executable code repair task.\n\n{fixture_context}\n"


def build_module_prompt(module_id: str, state: RuntimeState, task: dict[str, Any] | None = None) -> str:
    role = MODULE_ROLES.get(module_id, f"You are module {module_id}. Help solve the task.")
    family = (task or {}).get("task_family", "")
    family_hint = ""
    if family == "math_word_problem":
        family_hint = "This is a grade-school math word problem.\n"
    elif family == "code_agent_task":
        family_hint = code_task_context(task)
    elif family in {"search_agent_task", "mini_research_task"}:
        family_hint = "This is a research/evidence task. Cite sources and note uncertainty.\n"
    return (
        f"{role}\n\n"
        f"{family_hint}"
        f"Problem:\n{state.goal}\n\n"
        f"Prior observations:\n{observation_context(state)}\n\n"
        f"Respond as module {module_id}."
    )


def maybe_set_code_patch(state: RuntimeState, task: dict[str, Any], module_id: str, text: str) -> bool:
    if task.get("task_family") != "code_agent_task" or module_id not in CODE_PATCH_MODULES:
        return False
    fix_paths = fix_paths_for_task(task.get("task_id", ""))
    patch = select_code_patch(text, fix_paths)
    if not patch:
        return False
    state.final_answer = patch
    state.confidence = max(state.confidence, 0.9)
    return True


def llm_module_executor(
    client: LLMClient,
    module_id: str,
    task: dict[str, Any],
    *,
    on_prediction: Callable[[RuntimeState, str | None], None] | None = None,
) -> Callable[[RuntimeState, ModuleSpec], ModuleOutput]:
    def executor(state: RuntimeState, module: ModuleSpec) -> ModuleOutput:
        prompt = build_module_prompt(module_id, state, task)
        text, _metadata, _latency = client.complete(prompt, module_id=module_id)
        if maybe_set_code_patch(state, task, module_id, text):
            confidence = 0.9
        else:
            prediction = extract_model_answer(text)
            if on_prediction:
                on_prediction(state, prediction)
            elif prediction:
                state.final_answer = text
                state.confidence = max(state.confidence, 0.85)
            confidence = 0.82 if prediction or len(text.strip()) > 20 else 0.55
        failure_signal = None
        if module_id not in {"search_agent", "critic_agent", "memory"} and not text.strip():
            failure_signal = "empty_module_output"
        return ModuleOutput(
            module_id=module.module_id,
            content=text,
            confidence=confidence,
            failure_signal=failure_signal,
        )

    return executor


def inject_llm_executors(
    modules: list[ModuleSpec],
    client: LLMClient,
    task: dict[str, Any],
    *,
    llm_module_ids: set[str] | None = None,
    on_prediction: Callable[[RuntimeState, str | None], None] | None = None,
) -> list[ModuleSpec]:
    if llm_module_ids is None:
        llm_module_ids = {"code_agent", "search_agent", "critic_agent", "aggregator", "memory"}
    injected: list[ModuleSpec] = []
    for module in modules:
        executor = (
            llm_module_executor(client, module.module_id, task, on_prediction=on_prediction)
            if module.module_id in llm_module_ids
            else module.executor
        )
        cost = 1.0 if module.module_id in llm_module_ids else module.cost
        injected.append(
            ModuleSpec(
                module_id=module.module_id,
                kind=module.kind,
                description=module.description,
                cost=cost,
                latency=module.latency,
                risk=module.risk,
                reliability=module.reliability,
                historical_success=module.historical_success,
                executor=executor,
            )
        )
    return injected


def default_module_specs() -> list[ModuleSpec]:
    template = build_default_runtime()
    return list(template.modules.values())
