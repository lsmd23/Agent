"""Terminal-Bench integration for Agent-Attention baselines."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import getpass
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.real_benchmarks.load_env import load_project_env

ROOT = Path(__file__).resolve().parents[2]
load_project_env(start=ROOT)
DEFAULT_DATASET_DIR = ROOT / "external" / "terminal-bench-core"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "llm_runs" / "terminal_bench"
FAITHFUL_TB_BASELINES = (
    "single_react_llm_agent",
    "fixed_workflow_llm_agent",
    "agent_attention_llm_tuned",
    "retrieval_memory_llm_agent",
    "moa_style_llm_agent",
)


@dataclass
class TBRunSpec:
    baseline_id: str
    task_id: str | None
    n_tasks: int
    dataset_path: Path
    output_path: Path
    run_id: str
    model: str
    provider: str
    n_concurrent: int = 1
    agent: str | None = None
    use_faithful_agent: bool = True
    max_shell_steps: int = 8


def docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    cmd = wrap_cmd_for_docker_group([docker, "info"])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def docker_python_sdk_available() -> bool:
    """True when the Linux docker Python SDK can reach /var/run/docker.sock."""
    sock = Path("/var/run/docker.sock")
    if not sock.exists():
        return False
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import docker; docker.from_env().ping()",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            env={
                **os.environ,
                "PYTHONPATH": "",
            },
        )
        if proc.returncode == 0:
            return True
    except (subprocess.SubprocessError, OSError):
        pass
    # tb CLI uses uv tool python with docker package installed
    tb = shutil.which("tb")
    if not tb:
        return False
    uv_python = Path.home() / ".local/share/uv/tools/terminal-bench/bin/python"
    if not uv_python.exists():
        return False
    py_cmd = [str(uv_python), "-c", "import docker; docker.from_env().ping()"]
    py_cmd = wrap_cmd_for_docker_group(py_cmd)
    try:
        proc = subprocess.run(
            py_cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def tb_cli_available() -> bool:
    return shutil.which("tb") is not None


def _collect_tb_log_text(run_dir: Path, stderr: str = "") -> str:
    chunks: list[str] = [stderr]
    if run_dir.is_dir():
        run_log = run_dir / "run.log"
        if run_log.exists():
            chunks.append(run_log.read_text(encoding="utf-8", errors="replace"))
        for post_test in run_dir.rglob("post-test.txt"):
            chunks.append(post_test.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks).lower()


def detect_tb_environment_failure(run_dir: Path, stderr: str = "") -> tuple[str | None, str | None]:
    """Return (failure_type, detail) when logs indicate infra/network issues, not agent quality."""
    text = _collect_tb_log_text(run_dir, stderr)
    checks: list[tuple[str, str]] = [
        ("docker_permission_denied", "permission denied"),
        ("docker_client_error", "error creating docker client"),
        ("docker_build_failed", "docker compose command failed"),
        ("docker_build_failed", "failed to solve"),
        ("registry_unreachable", "ghcr.io"),
        ("apt_mirror_failure", "502  bad gateway"),
        ("apt_mirror_failure", "failed to fetch http://archive.ubuntu.com"),
        ("test_setup_failed", "setup-uv-pytest.sh"),
        ("test_setup_failed", "uv: command not found"),
        ("llm_api_failure", "403 client error"),
        ("llm_api_failure", "401 client error"),
    ]
    for failure_type, needle in checks:
        if needle in text:
            if failure_type == "registry_unreachable" and "eof" not in text and "failed to resolve" not in text:
                continue
            return failure_type, needle
    return None, None


def classify_tb_failure(metrics: dict[str, Any], stderr: str = "", *, run_dir: Path | None = None) -> str:
    if metrics.get("timeout"):
        return "timeout"
    log_dir = run_dir or Path(metrics.get("raw_log_dir", ""))
    env_type, _ = detect_tb_environment_failure(log_dir, stderr) if log_dir else (None, None)
    if env_type:
        return "environment_failure"
    text = stderr.lower()
    if "permission denied" in text or "permissionerror" in text:
        return "environment_failure"
    if "error creating docker client" in text or "dockerexception" in text:
        return "environment_failure"
    if "docker compose command failed" in text or "failed to solve" in text:
        return "environment_failure"
    if "502  bad gateway" in text or "apt-get update" in text:
        return "environment_failure"
    if metrics.get("failure_type") in {
        "docker_permission_denied",
        "docker_client_error",
        "docker_build_failed",
        "registry_unreachable",
        "apt_mirror_failure",
        "test_setup_failed",
    }:
        return "environment_failure"
    if "fatal_llm_parse_error" in text or "parse" in text and "error" in text:
        return "parsing_failure"
    if "403 client error" in text or "401 client error" in text:
        return "llm_api_failure"
    if metrics.get("failure_type") == "tb_process_error":
        return "environment_failure"
    if metrics.get("end_task_success") is True:
        return "none"
    if metrics.get("end_task_success") is False:
        return "agent_failure"
    return "scoring_failure"


def needs_sg_docker() -> bool:
    """True when user is in docker group but the current session has not refreshed groups."""
    try:
        import grp

        if grp.getgrnam("docker").gr_gid in os.getgroups():
            return False
    except KeyError:
        return False
    proc = subprocess.run(["getent", "group", "docker"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False
    members = proc.stdout.strip().split(":")[-1]
    return getpass.getuser() in {member.strip() for member in members.split(",") if member.strip()}


def wrap_cmd_for_docker_group(cmd: list[str]) -> list[str]:
    if not needs_sg_docker() or not shutil.which("sg"):
        return cmd
    cmd_str = " ".join(shlex.quote(part) for part in cmd)
    return ["sg", "docker", "-c", cmd_str]


def dataset_path_exists(path: Path | None = None) -> bool:
    root = path or DEFAULT_DATASET_DIR
    if not root.exists():
        return False
    return any(root.rglob("task.toml")) or any(root.rglob("task.yaml"))


def list_task_ids(dataset_path: Path | None = None, *, limit: int | None = None) -> list[str]:
    root = dataset_path or DEFAULT_DATASET_DIR
    task_files = sorted(list(root.rglob("task.toml")) + list(root.rglob("task.yaml")))
    ids: list[str] = []
    for task_file in task_files:
        task_dir = task_file.parent
        ids.append(task_dir.name)
        if limit is not None and len(ids) >= limit:
            break
    return ids


def build_faithful_agent_import_path() -> str:
    return "experiments.terminal_bench.faithful_tb_agent:FaithfulTBAgent"


def build_tb_run_command(spec: TBRunSpec) -> list[str]:
    cmd = [
        "tb",
        "run",
        "--output-path",
        str(spec.output_path),
        "--run-id",
        spec.run_id,
        "--dataset-path",
        str(spec.dataset_path),
        "--n-concurrent",
        str(spec.n_concurrent),
        "--n-attempts",
        "1",
        "--no-upload-results",
    ]
    if spec.task_id:
        cmd.extend(["--task-id", spec.task_id])
    else:
        cmd.extend(["--n-tasks", str(spec.n_tasks)])

    if spec.use_faithful_agent:
        cmd.extend(["--agent-import-path", build_faithful_agent_import_path()])
        cmd.extend(
            [
                "--agent-kwarg",
                f"baseline_id={spec.baseline_id}",
                "--agent-kwarg",
                f"provider={spec.provider}",
            ]
        )
        if spec.model:
            cmd.extend(
                [
                    "--agent-kwarg",
                    f"model_name={spec.model}",
                    "--agent-kwarg",
                    f"max_shell_steps={spec.max_shell_steps}",
                    "--model",
                    spec.model,
                ]
            )
    elif spec.agent:
        cmd.extend(["--agent", spec.agent])
        if spec.model:
            cmd.extend(["--model", spec.model])
    return cmd


def run_subprocess(cmd: list[str], *, env: dict[str, str] | None = None, timeout_s: int | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = str(ROOT) if "PYTHONPATH" not in merged else f"{ROOT}{os.pathsep}{merged['PYTHONPATH']}"
    if env:
        merged.update(env)
    cmd = wrap_cmd_for_docker_group(cmd)
    return subprocess.run(
        cmd,
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def parse_tb_success(run_dir: Path) -> bool | None:
    for name in ("results.json", "summary.json", "run.json"):
        candidate = run_dir / name
        if not candidate.exists():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            if "n_resolved" in payload and "n_unresolved" in payload:
                if payload.get("n_resolved", 0) > 0 and payload.get("n_unresolved", 0) == 0:
                    return True
                if payload.get("n_unresolved", 0) > 0 and payload.get("n_resolved", 0) == 0:
                    return False
            if "success" in payload:
                return bool(payload["success"])
            if "passed" in payload:
                return bool(payload["passed"])
            tasks = payload.get("tasks") or payload.get("results")
            if isinstance(tasks, list) and tasks:
                first = tasks[0]
                if isinstance(first, dict):
                    if first.get("is_resolved") is True:
                        return True
                    if first.get("is_resolved") is False:
                        return False
                    if "success" in first:
                        return bool(first["success"])
                    if "is_resolved" in first and first["is_resolved"] is None:
                        return False
    return None


def envelope_from_tb_run(
    *,
    baseline_id: str,
    task_id: str,
    run_dir: Path,
    provider: str,
    model: str,
    proc: subprocess.CompletedProcess[str],
    timeout: bool = False,
) -> dict[str, Any]:
    end_success = parse_tb_success(run_dir)
    if end_success is True:
        label = "pass"
    elif end_success is False:
        label = "fail"
    else:
        label = "fail" if proc.returncode != 0 else "partial"

    failure_type = None
    failure_category = "none"
    if timeout:
        failure_type = "timeout"
        failure_category = "timeout"
    elif proc.returncode != 0:
        failure_type = "tb_process_error"
        failure_category = "environment_failure"
    elif label == "fail":
        failure_type = "end_task_failed"
        failure_category = "agent_failure"

    stderr = proc.stderr or ""
    env_type, env_detail = detect_tb_environment_failure(run_dir, stderr)
    if env_type:
        failure_type = env_type
        failure_category = "environment_failure"
        label = "fail"
    elif "Permission denied" in stderr or "PermissionError" in stderr:
        failure_type = "docker_permission_denied"
        failure_category = "environment_failure"
        label = "fail"
    elif "Error creating docker client" in stderr:
        failure_type = "docker_client_error"
        failure_category = "environment_failure"
        label = "fail"

    return {
        "schema_version": "agent_attention.benchmark_trajectory.v0.1",
        "run_id": run_dir.name,
        "task_id": task_id,
        "benchmark_id": "terminal_bench",
        "baseline_id": baseline_id,
        "runtime_config": {
            "provider": provider,
            "model": model,
            "harness": "terminal-bench",
            "dataset_path": str(run_dir.parent.parent / "dataset") if False else None,
        },
        "final_success_label": label,
        "failure_reason": failure_type,
        "known_deviations": [
            "terminal_bench_harness",
            "faithful_tb_agent_shell_bridge",
        ],
        "metrics_summary": {
            "oracle_type": "terminal_bench_end_task",
            "end_task_success": end_success if end_success is not None else label == "pass",
            "tb_returncode": proc.returncode,
            "timeout": timeout,
            "failure_type": failure_type,
            "failure_category": failure_category,
            "raw_log_dir": str(run_dir),
            "model_calls": None,
            "latency_ms": None,
        },
        "events": [],
    }


def run_local_code_fallback(
    *,
    baseline_id: str,
    tasks_path: Path,
    limit: int = 1,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    from experiments.real_benchmarks.faithful_llm_runners import run_faithful_llm
    from experiments.real_benchmarks.llm_client import LLMClient
    from experiments.real_benchmarks.load_env import load_project_env
    from experiments.real_benchmarks.run_gsm8k_llm import load_jsonl

    load_project_env(start=ROOT)
    tasks = load_jsonl(tasks_path, limit)
    output_root = output_dir or (DEFAULT_OUTPUT_DIR / "local_fallback")
    output_root.mkdir(parents=True, exist_ok=True)
    trajectories: list[dict[str, Any]] = []
    for task in tasks:
        client = LLMClient(
            provider=os.environ.get("LLM_PROVIDER", "openai"),
            model=os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini",
        )
        traj = run_faithful_llm(baseline_id, task, client)
        traj["metrics_summary"]["failure_type"] = None if traj["final_success_label"] == "pass" else "end_task_failed"
        traj["metrics_summary"]["raw_log_dir"] = str(output_root / baseline_id)
        target = output_root / baseline_id / f"{traj['run_id']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(traj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        trajectories.append(traj)
    return {
        "mode": "local_code_fallback",
        "baseline_id": baseline_id,
        "tasks": len(tasks),
        "trajectories": trajectories,
    }


def run_tb_smoke(
    *,
    baseline_id: str = "single_react_llm_agent",
    task_id: str | None = None,
    n_tasks: int = 1,
    dataset_path: Path | None = None,
    output_dir: Path | None = None,
    provider: str | None = None,
    model: str | None = None,
    use_oracle_agent: bool = False,
    timeout_s: int = 900,
    max_shell_steps: int = 8,
) -> dict[str, Any]:
    dataset = dataset_path or DEFAULT_DATASET_DIR
    output_root = output_dir or (DEFAULT_OUTPUT_DIR / "smoke")
    run_id = f"tb_smoke__{baseline_id}__{int(time.time())}"
    provider = provider or os.environ.get("LLM_PROVIDER", "openai")
    model = model or os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    if not docker_available():
        return {
            "mode": "blocked",
            "blocker": "docker_unavailable",
            "message": "Docker not reachable from WSL PATH.",
        }
    if not tb_cli_available():
        return {"mode": "blocked", "blocker": "tb_cli_missing", "message": "tb CLI not on PATH."}
    if not dataset_path_exists(dataset):
        return {
            "mode": "blocked",
            "blocker": "dataset_missing",
            "message": f"Dataset not found at {dataset}. Run tb datasets download first.",
            "suggested_command": (
                f"tb datasets download -d terminal-bench-core==0.1.1 "
                f"--output-dir {DEFAULT_DATASET_DIR}"
            ),
        }

    selected_task = task_id or (list_task_ids(dataset, limit=1)[0] if list_task_ids(dataset, limit=1) else None)
    spec = TBRunSpec(
        baseline_id=baseline_id,
        task_id=selected_task,
        n_tasks=n_tasks,
        dataset_path=dataset,
        output_path=output_root,
        run_id=run_id,
        model=model,
        provider=provider,
        use_faithful_agent=not use_oracle_agent,
        agent="oracle" if use_oracle_agent else None,
        max_shell_steps=max_shell_steps,
    )
    cmd = build_tb_run_command(spec)
    started = time.time()
    try:
        proc = run_subprocess(cmd, timeout_s=timeout_s)
        timed_out = False
    except subprocess.TimeoutExpired as error:
        proc = error
        timed_out = True

    run_dir = output_root / run_id
    envelope = envelope_from_tb_run(
        baseline_id=baseline_id,
        task_id=selected_task or "unknown",
        run_dir=run_dir,
        provider=provider,
        model=model,
        proc=proc if isinstance(proc, subprocess.CompletedProcess) else subprocess.CompletedProcess(cmd, 124, "", "timeout"),
        timeout=timed_out,
    )
    envelope_path = output_root / f"{run_id}__envelope.json"
    envelope_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "mode": "terminal_bench",
        "command": cmd,
        "returncode": proc.returncode if isinstance(proc, subprocess.CompletedProcess) else 124,
        "stdout_tail": (proc.stdout[-4000:] if isinstance(proc, subprocess.CompletedProcess) and proc.stdout else ""),
        "stderr_tail": (proc.stderr[-4000:] if isinstance(proc, subprocess.CompletedProcess) and proc.stderr else ""),
        "envelope_path": str(envelope_path),
        "run_dir": str(run_dir),
        "elapsed_s": round(time.time() - started, 2),
        "envelope": envelope,
    }


def run_adapter_smoke(*, prefer_tb: bool = True, fallback_limit: int = 1) -> dict[str, Any]:
    if prefer_tb:
        tb_result = run_tb_smoke(use_oracle_agent=True)
        if tb_result.get("mode") != "blocked":
            return tb_result
        tb_result["fallback"] = run_local_code_fallback(
            baseline_id="single_react_llm_agent",
            tasks_path=ROOT / "experiments" / "tasks" / "phase1_code_tasks.jsonl",
            limit=fallback_limit,
        )
        return tb_result
    return run_local_code_fallback(
        baseline_id="single_react_llm_agent",
        tasks_path=ROOT / "experiments" / "tasks" / "phase1_code_tasks.jsonl",
        limit=fallback_limit,
    )


def compress_observation(text: str, *, max_chars: int = 2400, tail_lines: int = 40) -> str:
    """Tail-preserving compression for terminal observations (SWE-agent-style)."""
    if not text or len(text) <= max_chars:
        return text
    lines = text.splitlines()
    error_lines = [ln for ln in lines if re.search(r"(?i)error|failed|traceback|permission denied|not found", ln)]
    tail = lines[-tail_lines:] if len(lines) > tail_lines else lines
    head_budget = max(200, max_chars // 4)
    tail_text = "\n".join(tail)
    if len(tail_text) > max_chars - head_budget:
        tail_text = tail_text[-(max_chars - head_budget) :]
    parts = [f"[observation truncated: {len(lines)} lines total]"]
    if error_lines:
        err_text = "\n".join(error_lines[-8:])
        parts.append(f"[recent errors]\n{err_text}")
    parts.append(f"[tail]\n{tail_text}")
    merged = "\n".join(parts)
    return merged[:max_chars]


def extract_file_patch_commands(text: str) -> list[str]:
    """Convert `# file: path` code blocks into shell heredoc write commands."""
    commands: list[str] = []
    for match in re.finditer(
        r"```(?:python|py|bash|sh|text)?\s*\n(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block = match.group(1)
        file_match = re.match(r"^\s*#\s*file:\s*(\S+)\s*\n", block)
        if not file_match:
            continue
        rel_path = file_match.group(1)
        body = block[file_match.end() :].rstrip("\n")
        if not body:
            continue
        parent = str(Path(rel_path).parent)
        if parent and parent not in {".", ""}:
            commands.append(f"mkdir -p {shlex.quote(parent)}")
        delimiter = "EOF_PATCH"
        while delimiter in body:
            delimiter = f"EOF_{delimiter}"
        commands.append(f"cat > {shlex.quote(rel_path)} <<'{delimiter}'\n{body}\n{delimiter}")
    return _sanitize_shell_commands(commands)


def _extract_commands_from_partial_json(text: str) -> list[str]:
    """Recover commands when model output truncates mid-JSON (common at max_tokens=512)."""
    match = re.search(r'"commands"\s*:\s*\[(.*?)(?:\]|$)', text, flags=re.DOTALL)
    if not match:
        return []
    inner = match.group(1)
    recovered: list[str] = []
    for item in re.finditer(r'"((?:\\.|[^"\\])*)"', inner):
        try:
            recovered.append(json.loads(f'"{item.group(1)}"'))
        except json.JSONDecodeError:
            continue
    return _sanitize_shell_commands(recovered)


def extract_shell_commands(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(
        r"```(?:bash|sh|shell)\s*\n(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        block = match.group(1).strip()
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append(line)
    if commands:
        return _sanitize_shell_commands(commands)

    patch_cmds = extract_file_patch_commands(text)
    if patch_cmds:
        return patch_cmds

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|bash|sh|shell)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict) and isinstance(payload.get("commands"), list):
            return _sanitize_shell_commands([str(item) for item in payload["commands"]])
    except json.JSONDecodeError:
        partial = _extract_commands_from_partial_json(cleaned)
        if partial:
            return partial
    return []


_SHELL_CMD_RE = re.compile(
    r"^(?:[a-zA-Z0-9_./-]+(?:\s|$)|sudo\s|chmod\s|ls\s|cat\s|echo\s|python3?\s|bash\s|sh\s|"
    r"grep\s|find\s|sed\s|awk\s|curl\s|wget\s|mkdir\s|rm\s|cp\s|mv\s|touch\s|head\s|tail\s|"
    r"cd\s|export\s|git\s|tee\s|pip3?\s|uv\s|npm\s|nohup\s|systemctl\s|service\s|"
    r"apt-get\s|apt\s|pip\s|kill\s|ps\s|sleep\s|test\s|which\s|file\s|./)"
)


def _sanitize_shell_commands(commands: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in commands:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":") and " " not in line:
            continue
        if re.match(r"^(If|When|Then|Without|Now,|Corrected|Ensure|But)\b", line):
            continue
        if not _SHELL_CMD_RE.match(line):
            continue
        cleaned.append(line)
    return cleaned
