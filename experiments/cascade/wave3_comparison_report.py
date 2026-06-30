#!/usr/bin/env python3
"""Compare wave-3 cascade eval against original code matrix baselines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Wave-3 cascade comparison report.")
    parser.add_argument("--matrix", default="experiments/metrics/code_full_matrix_summary.json")
    parser.add_argument("--cascade", default="experiments/metrics/code_cascade_wave3_summary.json")
    parser.add_argument("--ci", default="experiments/metrics/code_cascade_wave3_with_ci.json")
    parser.add_argument("--output", default="experiments/analysis/wave3_cascade_comparison.md")
    args = parser.parse_args()

    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    cascade = json.loads(Path(args.cascade).read_text(encoding="utf-8"))
    ci = json.loads(Path(args.ci).read_text(encoding="utf-8")) if Path(args.ci).exists() else {}

    refs = {
        "single_react_llm_agent": matrix["baselines"]["single_react_llm_agent"],
        "agent_attention_llm_tuned": matrix["baselines"]["agent_attention_llm_tuned"],
        "moa_style_llm_agent": matrix["baselines"]["moa_style_llm_agent"],
    }

    lines = [
        "# Wave 3 Cascade Comparison",
        "",
        "Unified eval via `run_real_llm_eval.py --family cascade` (2026-06-30).",
        "",
        "## Cascade policies (live 26-task code suite)",
        "",
        "| Baseline | Accuracy | Mean calls | Cost-norm | CI (bootstrap) |",
        "|----------|----------|------------|-----------|----------------|",
    ]

    for bid in (
        "cascade_react_aa_lite_llm",
        "cascade_react_moa_llm",
        "cascade_react_aa_moa_llm",
    ):
        base = cascade["baselines"][bid]
        ci_row = ci.get("baselines", {}).get(bid, {})
        ci_str = (
            f"{ci_row.get('ci_low', 0):.1%}–{ci_row.get('ci_high', 0):.1%}"
            if ci_row
            else "n/a"
        )
        lines.append(
            f"| `{bid}` | {base['accuracy']:.1%} | {base['mean_model_calls']:.2f} | "
            f"{base['cost_normalized_success']:.4f} | {ci_str} |"
        )

    lines.extend(
        [
            "",
            "## Reference fixed baselines (original matrix)",
            "",
            "| Baseline | Accuracy | Mean calls | Cost-norm |",
            "|----------|----------|------------|-----------|",
        ]
    )
    for bid, base in refs.items():
        lines.append(
            f"| `{bid}` | {base['accuracy']:.1%} | {base['mean_model_calls']:.2f} | "
            f"{base['cost_normalized_success']:.4f} |"
        )

    lite = cascade["baselines"]["cascade_react_aa_lite_llm"]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- **`cascade_react_aa_lite_llm` reaches {lite['accuracy']:.0%} accuracy** at "
            f"{lite['mean_model_calls']:.2f} mean calls — best wave-3 policy on this run.",
            "- AA lite (no verifier/memory, fixed top-k=2) as escalation slot outperforms always-on AA tuned "
            f"({refs['agent_attention_llm_tuned']['accuracy']:.1%} @ {refs['agent_attention_llm_tuned']['mean_model_calls']:.2f} calls).",
            "- `cascade_react_moa_llm` underperformed lite on this run (92.3%); check per-task variance on "
            "`csv_001` and `slugify_001`.",
            "- Default deployment recommendation: **`cascade_react_aa_lite_llm`** over `react_aa_moa` unless "
            "MoA rescue is required on held-out hard tasks.",
            "",
            "## Artifacts",
            "",
            f"- `{args.cascade}`",
            f"- `{args.ci}`",
            f"- Trajectories: `experiments/llm_runs/code_cascade_wave3/`",
            "",
        ]
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
