#!/usr/bin/env python3
"""Merge cascade baseline summaries and compute bootstrap CIs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def merge_summaries(paths: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] | None = None
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if merged is None:
            merged = {
                "scope": "Merged cascade wave-3 eval summaries.",
                "suite": payload.get("suite"),
                "tasks": payload.get("tasks"),
                "model": payload.get("model"),
                "provider": payload.get("provider"),
                "baselines": {},
                "per_task": [],
            }
        merged["baselines"].update(payload.get("baselines", {}))
        merged["per_task"].extend(payload.get("per_task", []))
    if merged is None:
        raise ValueError("No summaries to merge")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize cascade wave-3 metrics.")
    parser.add_argument("--summary", action="append", required=True)
    parser.add_argument("--output", default="experiments/metrics/code_cascade_wave3_summary.json")
    parser.add_argument("--ci-output", default="experiments/metrics/code_cascade_wave3_with_ci.json")
    args = parser.parse_args()

    merged = merge_summaries([Path(p) for p in args.summary])
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from experiments.analysis.bootstrap_metrics import analyze

    ci = analyze(merged)
    ci["source_summary"] = str(out)
    ci_path = Path(args.ci_output)
    ci_path.write_text(json.dumps(ci, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(out), "ci": str(ci_path), "baselines": list(merged["baselines"])}, indent=2))


if __name__ == "__main__":
    main()
