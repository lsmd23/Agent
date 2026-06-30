"""Faithful Agent-Attention baseline as a Terminal-Bench custom agent."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.real_benchmarks.llm_client import LLMClient
from experiments.real_benchmarks.load_env import load_project_env
from experiments.terminal_bench.tb_shell_loop import run_shell_loop

load_project_env(start=ROOT)

try:
    from terminal_bench.agents.base_agent import AgentResult, BaseAgent
    from terminal_bench.agents.failure_mode import FailureMode
    from terminal_bench.terminal.tmux_session import TmuxSession
except ImportError as error:  # pragma: no cover - exercised when TB installed
    raise ImportError("terminal-bench package required for FaithfulTBAgent") from error


class FaithfulTBAgent(BaseAgent):
    """Multi-step shell ReAct agent with baseline-specific prompting."""

    SUPPORTED_BASELINES = {
        "single_react_llm_agent",
        "fixed_workflow_llm_agent",
        "agent_attention_llm_tuned",
        "retrieval_memory_llm_agent",
        "moa_style_llm_agent",
    }

    def __init__(
        self,
        *,
        baseline_id: str = "single_react_llm_agent",
        provider: str | None = None,
        model_name: str | None = None,
        max_tokens: int = 512,
        max_shell_steps: int = 8,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if baseline_id not in self.SUPPORTED_BASELINES:
            raise ValueError(f"Unsupported baseline_id={baseline_id!r}")
        self.baseline_id = baseline_id
        self.provider = provider or os.environ.get("LLM_PROVIDER", "openai")
        self.model_name = model_name or os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL")
        self.max_tokens = max_tokens
        self.max_shell_steps = max_shell_steps

    @staticmethod
    def name() -> str:
        return "faithful_tb_agent"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        started = time.time()
        client = LLMClient(
            provider=self.provider,
            model=self.model_name or "gpt-4o-mini",
            max_tokens=self.max_tokens,
            temperature=0.0,
        )
        step_log, usage_tokens = run_shell_loop(
            baseline_id=self.baseline_id,
            instruction=instruction,
            session=session,
            client=client,
            max_steps=self.max_shell_steps,
        )

        if logging_dir is not None:
            logging_dir.mkdir(parents=True, exist_ok=True)
            (logging_dir / "instruction.txt").write_text(instruction, encoding="utf-8")
            (logging_dir / "shell_steps.json").write_text(
                json.dumps(step_log, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (logging_dir / "model_calls.json").write_text(
                json.dumps(client.calls, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        return AgentResult(
            total_input_tokens=usage_tokens,
            total_output_tokens=0,
            failure_mode=FailureMode.NONE,
            timestamped_markers=[(time.time() - started, "faithful_tb_agent_complete")],
        )
