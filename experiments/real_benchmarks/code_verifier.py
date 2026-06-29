"""Executable pytest verifier for Phase1 code tasks."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "code"
PYTHON_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
FILE_HINT_RE = re.compile(r"^#\s*(?:file|path)\s*:\s*(.+)$", re.MULTILINE)


@dataclass
class PytestResult:
    passed: bool
    fixture_id: str
    returncode: int
    stdout: str
    stderr: str
    applied_files: list[str]
    apply_mode: str


def list_fixture_dirs() -> list[Path]:
    if not FIXTURES_ROOT.exists():
        return []
    return sorted(path for path in FIXTURES_ROOT.iterdir() if path.is_dir() and (path / "manifest.json").exists())


def load_manifest(fixture_dir: Path) -> dict[str, Any]:
    return json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))


def fixture_dir_for_task(task_id: str) -> Path | None:
    for fixture_dir in list_fixture_dirs():
        manifest = load_manifest(fixture_dir)
        if task_id in manifest.get("task_ids", []):
            return fixture_dir
    return None


def fixture_id_for_task(task_id: str) -> str | None:
    fixture_dir = fixture_dir_for_task(task_id)
    if fixture_dir is None:
        return None
    return load_manifest(fixture_dir).get("fixture_id")


def extract_python_blocks(text: str) -> list[tuple[str | None, str]]:
    blocks: list[tuple[str | None, str]] = []
    for match in PYTHON_BLOCK_RE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        hint = None
        hint_match = FILE_HINT_RE.search(body)
        if hint_match:
            hint = hint_match.group(1).strip()
        blocks.append((hint, body))
    return blocks


def agent_text_from_state(state: Any) -> str:
    parts: list[str] = []
    final_answer = getattr(state, "final_answer", None)
    if final_answer:
        parts.append(str(final_answer))
    for obs in getattr(state, "observations", []) or []:
        if isinstance(obs, str):
            parts.append(obs)
    return "\n\n".join(parts)


def _copy_repo(fixture_dir: Path, dest: Path) -> None:
    shutil.copytree(fixture_dir / "repo", dest, dirs_exist_ok=True)


def _apply_fix_file(repo_root: Path, fixture_dir: Path, fix_spec: dict[str, Any], agent_text: str) -> tuple[bool, str]:
    rel_path = fix_spec["path"]
    target = repo_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    golden_path = fixture_dir / fix_spec["golden"]

    markers = fix_spec.get("markers", [])
    if any(marker in agent_text for marker in markers):
        target.write_text(golden_path.read_text(encoding="utf-8"), encoding="utf-8")
        return True, "marker_match"

    golden_text = golden_path.read_text(encoding="utf-8").strip()
    for _hint, block in extract_python_blocks(agent_text):
        if block.strip() == golden_text or block.strip() in golden_text or golden_text in block:
            target.write_text(block if block.endswith("\n") else block + "\n", encoding="utf-8")
            return True, "golden_code_block"

    blocks = extract_python_blocks(agent_text)
    hinted = [(hint, block) for hint, block in blocks if hint and hint.replace("\\", "/").endswith(rel_path.replace("\\", "/"))]
    if hinted:
        _, block = hinted[-1]
        target.write_text(block if block.endswith("\n") else block + "\n", encoding="utf-8")
        return True, "hinted_code_block"

    if fix_spec.get("_single_block_only", False) and len(blocks) == 1:
        _, block = blocks[0]
        target.write_text(block if block.endswith("\n") else block + "\n", encoding="utf-8")
        return True, "single_code_block"

    return False, "not_applied"


def apply_agent_patch(fixture_dir: Path, agent_text: str) -> tuple[Path, list[str], str]:
    manifest = load_manifest(fixture_dir)
    temp_root = Path(tempfile.mkdtemp(prefix="aa_code_fixture_"))
    repo_root = temp_root / "repo"
    _copy_repo(fixture_dir, repo_root)

    fix_files = manifest.get("fix_files", [])
    if len(fix_files) == 1:
        fix_files = [{**fix_files[0], "_single_block_only": True}]

    applied: list[str] = []
    modes: list[str] = []
    for fix_spec in fix_files:
        ok, mode = _apply_fix_file(repo_root, fixture_dir, fix_spec, agent_text)
        if ok:
            applied.append(fix_spec["path"])
            modes.append(mode)

    apply_mode = modes[-1] if modes else "none"
    return repo_root, applied, apply_mode


def run_tests(repo_root: Path, *, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing else f"{repo_root}{__import__('os').pathsep}{existing}"
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=env,
    )


def run_pytest(repo_root: Path, *, timeout_s: int = 30) -> subprocess.CompletedProcess[str]:
    """Backward-compatible alias; uses stdlib unittest discover."""
    return run_tests(repo_root, timeout_s=timeout_s)


def verify_code_task(task_id: str, agent_text: str) -> PytestResult:
    fixture_dir = fixture_dir_for_task(task_id)
    if fixture_dir is None:
        return PytestResult(
            passed=False,
            fixture_id="unknown",
            returncode=127,
            stdout="",
            stderr=f"No fixture registered for task_id={task_id}",
            applied_files=[],
            apply_mode="missing_fixture",
        )

    manifest = load_manifest(fixture_dir)
    fixture_id = str(manifest.get("fixture_id", fixture_dir.name))
    repo_root, applied_files, apply_mode = apply_agent_patch(fixture_dir, agent_text)

    try:
        if not applied_files:
            proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="No patch applied from agent output.")
        else:
            proc = run_pytest(repo_root)
    finally:
        shutil.rmtree(repo_root.parent, ignore_errors=True)

    return PytestResult(
        passed=proc.returncode == 0,
        fixture_id=fixture_id,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        applied_files=applied_files,
        apply_mode=apply_mode,
    )


def verify_golden_fixture(fixture_id: str) -> PytestResult:
    fixture_dir = FIXTURES_ROOT / fixture_id
    manifest = load_manifest(fixture_dir)
    marker = manifest["fix_files"][0]["markers"][0]
    return verify_code_task(manifest["task_ids"][0], marker)


def broken_repo_fails(fixture_id: str) -> bool:
    fixture_dir = FIXTURES_ROOT / fixture_id
    temp_root = Path(tempfile.mkdtemp(prefix="aa_broken_"))
    repo_root = temp_root / "repo"
    _copy_repo(fixture_dir, repo_root)
    try:
        return run_pytest(repo_root).returncode != 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def golden_repo_passes(fixture_id: str) -> bool:
    fixture_dir = FIXTURES_ROOT / fixture_id
    manifest = load_manifest(fixture_dir)
    return verify_code_task(manifest["task_ids"][0], manifest["fix_files"][0]["markers"][0]).passed
