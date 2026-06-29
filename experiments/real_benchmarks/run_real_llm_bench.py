#!/usr/bin/env python3
"""Orchestrate real LLM benchmark profiles (probe / smoke / full)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.real_benchmarks.load_env import load_project_env  # noqa: E402

load_project_env(start=ROOT)

PROFILES = {
    "probe": {"limit": 1, "description": "Single-task connectivity and latency check."},
    "smoke": {"limit": 5, "description": "Small smoke set for quick accuracy sanity check."},
    "full": {"limit": 20, "description": "Full prepared GSM8K sample (20 tasks)."},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real LLM GSM8K benchmark profiles.")
    parser.add_argument("--profile", choices=list(PROFILES), default="smoke")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "ollama"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "llama3.1:8b"))
    parser.add_argument("--tasks", default="experiments/tasks/gsm8k_test_sample.jsonl")
    parser.add_argument("--skip-env-check", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = PROFILES[args.profile]
    limit = int(profile["limit"])
    output_dir = ROOT / "experiments/llm_runs/gsm8k" / args.profile
    summary = ROOT / "experiments/metrics" / f"gsm8k_llm_{args.profile}_summary.json"
    env_report = ROOT / "experiments/metrics/llm_environment_report.json"

    if not args.skip_env_check:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "experiments/real_benchmarks/check_llm_environment.py"),
                "--json-output",
                str(env_report),
            ],
            check=True,
            cwd=ROOT,
        )

    cmd = [
        sys.executable,
        str(ROOT / "experiments/real_benchmarks/run_gsm8k_llm.py"),
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--tasks",
        args.tasks,
        "--limit",
        str(limit),
        "--output-dir",
        str(output_dir),
        "--summary-output",
        str(summary),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)

    traj_paths = sorted(output_dir.glob("*.json"))
    if traj_paths:
        metrics_path = ROOT / "experiments/metrics" / f"gsm8k_llm_{args.profile}_scored.json"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "docs/deliverables/07/scoring_script.py"),
                *[str(path) for path in traj_paths],
                "--output",
                str(metrics_path),
            ],
            check=True,
            cwd=ROOT,
        )

    manifest = {
        "profile": args.profile,
        "description": profile["description"],
        "provider": args.provider,
        "model": args.model,
        "limit": limit,
        "summary": str(summary.relative_to(ROOT)),
        "trajectory_dir": str(output_dir.relative_to(ROOT)),
        "environment_report": str(env_report.relative_to(ROOT)) if env_report.exists() else None,
    }
    manifest_path = ROOT / "experiments/metrics" / f"gsm8k_llm_{args.profile}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
