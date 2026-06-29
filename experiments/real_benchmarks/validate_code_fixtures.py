#!/usr/bin/env python3
"""Validate all code fixtures: broken fails, golden marker passes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.real_benchmarks.code_verifier import (  # noqa: E402
    FIXTURES_ROOT,
    broken_repo_fails,
    golden_repo_passes,
    list_fixture_dirs,
    load_manifest,
)


def main() -> None:
    results = []
    for fixture_dir in list_fixture_dirs():
        manifest = load_manifest(fixture_dir)
        fixture_id = manifest["fixture_id"]
        results.append(
            {
                "fixture_id": fixture_id,
                "broken_fails": broken_repo_fails(fixture_id),
                "golden_passes": golden_repo_passes(fixture_id),
            }
        )
    print(json.dumps({"fixtures_root": str(FIXTURES_ROOT), "results": results}, indent=2))
    if not all(item["broken_fails"] and item["golden_passes"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
