"""Multi-step observe→act shell loop for Terminal-Bench faithful agents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from experiments.real_benchmarks.llm_client import LLMClient
from experiments.terminal_bench.adapter import (
    _sanitize_shell_commands,
    compress_observation,
    extract_shell_commands,
)

try:
    from terminal_bench.terminal.tmux_session import TmuxSession
except ImportError:  # pragma: no cover
    TmuxSession = Any  # type: ignore[misc, assignment]


@dataclass
class StepResponse:
    commands: list[str] = field(default_factory=list)
    is_task_complete: bool = False
    explanation: str = ""
    parse_status: str = "ok"  # ok | empty | truncated_json | prose_only


BASELINE_STEP_HINTS: dict[str, str] = {
    "single_react_llm_agent": (
        "You are a single-controller ReAct terminal agent. "
        "Each turn: inspect the terminal, run 1-3 concrete shell commands, observe output, repeat."
    ),
    "fixed_workflow_llm_agent": (
        "You follow a fixed workflow: (1) inspect with ls/cat, (2) diagnose the issue, "
        "(3) apply the fix, (4) verify with the same command the user would run. "
        "Advance through phases across turns; do not skip inspection."
    ),
    "agent_attention_llm_tuned": (
        "You may mentally route between planner, executor, critic, and verifier roles, "
        "but emit only executable shell commands each turn."
    ),
    "retrieval_memory_llm_agent": (
        "Before acting, recall relevant prior shell patterns (chmod for permission errors, "
        "systemctl for services, pip/uv for Python). Then run 1-3 commands."
    ),
    "moa_style_llm_agent": (
        "Consider two candidate command plans internally, pick the safer one, "
        "and emit 1-3 shell commands for this turn."
    ),
}

_FIXED_WORKFLOW_PHASES = (
    "Phase 1 — inspect: ls -la, cat relevant files, check permissions.",
    "Phase 2 — diagnose: identify root cause from output.",
    "Phase 3 — fix: chmod, sed, write files, install packages as needed.",
    "Phase 4 — verify: rerun the failing command or test script.",
)


def parse_step_response(text: str) -> StepResponse:
    raw = text.strip()
    commands = extract_shell_commands(raw)
    if commands:
        return StepResponse(commands=commands, is_task_complete=False)

    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|bash|sh|shell)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            cmds = _sanitize_shell_commands([str(c) for c in payload.get("commands", [])])
            return StepResponse(
                commands=cmds,
                is_task_complete=bool(payload.get("is_task_complete", False)),
                explanation=str(payload.get("explanation", "")),
            )
    except json.JSONDecodeError:
        if '"commands"' in cleaned:
            return StepResponse(parse_status="truncated_json")
    if raw and not commands:
        return StepResponse(parse_status="prose_only")
    return StepResponse(parse_status="empty")


def _workflow_phase_hint(step: int) -> str:
    return _FIXED_WORKFLOW_PHASES[min(step, len(_FIXED_WORKFLOW_PHASES) - 1)]


def build_step_prompt(
    *,
    baseline_id: str,
    instruction: str,
    terminal_state: str,
    step: int,
    max_steps: int,
    history: list[dict[str, str]],
) -> str:
    hint = BASELINE_STEP_HINTS.get(baseline_id, BASELINE_STEP_HINTS["single_react_llm_agent"])
    history_lines: list[str] = []
    for item in history[-6:]:
        history_lines.append(
            f"$ {item['command']}\n{compress_observation(item['output'], max_chars=1200)}"
        )

    phase_block = ""
    if baseline_id == "fixed_workflow_llm_agent":
        phase_block = f"\nCurrent workflow focus: {_workflow_phase_hint(step)}\n"

    return (
        f"{hint}\n"
        "You are in /app on Ubuntu inside a Docker container.\n"
        "Respond with JSON only:\n"
        '{"commands": ["cmd1"], "is_task_complete": false, "explanation": "..."}\n'
        "Rules:\n"
        "- commands must be valid bash (no prose lines, no markdown).\n"
        "- Use 1-3 commands per turn; prefer small steps.\n"
        "- Set is_task_complete true only when the task instruction is satisfied.\n"
        f"- Step {step + 1} of {max_steps}.\n"
        f"{phase_block}\n"
        f"Task instruction:\n{instruction}\n\n"
        f"Terminal state:\n{compress_observation(terminal_state)}\n\n"
        + ("Prior commands:\n" + "\n---\n".join(history_lines) + "\n\n" if history_lines else "")
        + "Next JSON response:"
    )


def run_shell_loop(
    *,
    baseline_id: str,
    instruction: str,
    session: TmuxSession,
    client: LLMClient,
    max_steps: int = 8,
) -> tuple[list[dict[str, Any]], int]:
    """Run observe→act loop. Returns (step_log, total_tokens)."""
    history: list[dict[str, str]] = []
    step_log: list[dict[str, Any]] = []
    last_command: str | None = None

    for step in range(max_steps):
        terminal_state = session.get_incremental_output()
        prompt = build_step_prompt(
            baseline_id=baseline_id,
            instruction=instruction,
            terminal_state=terminal_state,
            step=step,
            max_steps=max_steps,
            history=history,
        )
        text, _meta, latency_ms = client.complete(prompt, module_id=f"tb_shell_step_{step}")
        parsed = parse_step_response(text)

        if not parsed.commands and parsed.parse_status in {"truncated_json", "empty", "prose_only"}:
            retry_prompt = (
                prompt
                + "\n\nYour last response had no executable commands. "
                "Reply with JSON only. Keep each command under 120 characters; "
                "split long writes into smaller steps.\n"
                f"Failed parse ({parsed.parse_status}). Next JSON response:"
            )
            text, _meta, latency_ms = client.complete(retry_prompt, module_id=f"tb_shell_step_{step}_retry")
            parsed = parse_step_response(text)

        step_record: dict[str, Any] = {
            "step": step,
            "latency_ms": latency_ms,
            "explanation": parsed.explanation,
            "commands": parsed.commands,
            "is_task_complete": parsed.is_task_complete,
            "parse_status": parsed.parse_status,
            "raw_response": text[:4000],
        }
        step_log.append(step_record)

        if not parsed.commands and parsed.is_task_complete:
            break

        if not parsed.commands:
            step_record["invalid_shell"] = parsed.parse_status
            continue

        for command in parsed.commands:
            if command == last_command:
                step_record.setdefault("skipped_duplicates", []).append(command)
                continue
            session.send_keys([command, "Enter"], block=True)
            output = session.capture_pane(capture_entire=False)
            history.append({"command": command, "output": output})
            last_command = command

        if parsed.is_task_complete:
            break

    usage_tokens = sum(
        call.get("usage", {}).get("total_tokens", 0)
        for call in client.calls
        if isinstance(call.get("usage"), dict)
    )
    return step_log, usage_tokens
