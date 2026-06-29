#!/usr/bin/env python3
"""Check local/API LLM environment for real benchmark runs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402

load_project_env(start=ROOT)


def read_mem_gb() -> float | None:
    try:
        with Path("/proc/meminfo").open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / (1024 * 1024), 2)
    except OSError:
        return None
    return None


def gpu_info() -> dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        return {"available": False, "devices": []}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        devices = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return {"available": bool(devices), "devices": devices}
    except (subprocess.SubprocessError, OSError):
        return {"available": False, "devices": []}


def ollama_probe(base_url: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "base_url": base_url,
        "reachable": False,
        "models": [],
        "cli_in_path": shutil.which("ollama") is not None,
    }
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
        info["reachable"] = True
        info["models"] = [item.get("name") for item in response.json().get("models", []) if item.get("name")]
    except requests.RequestException as error:
        info["error"] = str(error)
    except OSError as error:
        info["error"] = str(error)
    return info


def openai_probe() -> dict[str, Any]:
    return {
        "api_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "default_model": os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL"),
    }


def recommend_profile(models: list[str], mem_gb: float | None, gpu: dict[str, Any]) -> dict[str, Any]:
    has_model = bool(models)
    cpu_only = not gpu.get("available")
    low_ram = mem_gb is not None and mem_gb < 12
    if not has_model:
        return {
            "recommended_provider": None,
            "recommended_model": None,
            "recommended_limit": 0,
            "notes": ["No Ollama models found. Pull a model or configure OPENAI_API_KEY."],
        }
    model = os.environ.get("LLM_MODEL") or (models[0] if models else None)
    notes: list[str] = []
    if cpu_only:
        notes.append("No GPU detected — expect slow CPU inference.")
    if low_ram:
        notes.append(f"System RAM {mem_gb}GB is tight for 7B+ models; prefer Q4 quants and small batch sizes.")
    limit = 5 if cpu_only or low_ram else 20
    return {
        "recommended_provider": "ollama" if has_model else "openai",
        "recommended_model": model,
        "recommended_limit": limit,
        "notes": notes,
    }


def optional_chat_probe(provider: str, model: str) -> dict[str, Any]:
    from experiments.real_benchmarks.run_gsm8k_llm import model_call

    prompt = "Reply with exactly: OK"
    started = time.time()
    try:
        text, metadata = model_call(provider, model, prompt, max_tokens=8, temperature=0.0)
        return {
            "ok": True,
            "latency_ms": int((time.time() - started) * 1000),
            "output_preview": text[:120],
            "metadata": metadata,
        }
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "error": str(error)}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Check LLM environment for real benchmarks.")
    parser.add_argument("--probe-chat", action="store_true", help="Run one tiny model call.")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "ollama"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL"))
    parser.add_argument("--json-output", default=None)
    args = parser.parse_args()

    mem_gb = read_mem_gb()
    gpu = gpu_info()
    ollama = ollama_probe(os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    openai_info = openai_probe()
    recommendation = recommend_profile(ollama.get("models", []), mem_gb, gpu)

    report: dict[str, Any] = {
        "scope": "Real LLM benchmark environment check",
        "cpu_count": os.cpu_count(),
        "mem_total_gb": mem_gb,
        "gpu": gpu,
        "ollama": ollama,
        "openai_compatible": openai_info,
        "recommendation": recommendation,
        "can_run_local_ollama": bool(ollama.get("reachable") and ollama.get("models")),
        "needs_remote_api": not bool(ollama.get("reachable") and ollama.get("models")) and not openai_info["api_key_set"],
    }

    model = args.model or recommendation.get("recommended_model")
    if args.probe_chat and model and report["can_run_local_ollama"] and args.provider == "ollama":
        report["chat_probe"] = optional_chat_probe("ollama", model)
    elif args.probe_chat and openai_info["api_key_set"] and model:
        report["chat_probe"] = optional_chat_probe("openai", model)

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json_output:
        Path(args.json_output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
