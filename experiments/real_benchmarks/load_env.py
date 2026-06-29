"""Load project .env into os.environ without external dependencies."""

from __future__ import annotations

import os
from pathlib import Path


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(path: Path, *, override: bool = False) -> int:
    """Load KEY=VALUE pairs from path. Returns count of variables applied."""
    if not path.is_file():
        return 0

    applied = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = _strip_quotes(value.strip())
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
            applied += 1
    return applied


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".env").is_file():
            return candidate
        if (candidate / "experiments" / "real_benchmarks").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def load_project_env(*, start: Path | None = None, override: bool = False) -> Path | None:
    """Load .env from project root if present. Returns path loaded or None."""
    root = find_project_root(start)
    env_path = root / ".env"
    if load_env_file(env_path, override=override) >= 0 and env_path.is_file():
        return env_path
    return None
