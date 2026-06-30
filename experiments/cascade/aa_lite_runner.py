"""AA lite escalation stage for cascade policies (Brief C / Wave 3)."""

from __future__ import annotations

from typing import Any

from experiments.ablations.aa_ablation_llm import run_aa_ablation_llm
from experiments.cascade.cascade_policy import STAGE_AA_LITE
from experiments.real_benchmarks.llm_client import LLMClient

AA_LITE_ABLATION_ID = "aa_lite_escalation"


def run_aa_lite_llm(task: dict[str, Any], client: LLMClient) -> dict[str, Any]:
    """Run escalation-slot AA: no verifier, no memory, fixed top-k=2."""
    return run_aa_ablation_llm(
        AA_LITE_ABLATION_ID,
        task,
        client,
        report_baseline_id=STAGE_AA_LITE,
    )
