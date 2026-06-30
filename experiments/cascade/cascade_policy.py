"""Cascade routing policies (Brief B / Track 1)."""

from __future__ import annotations

from typing import Any

# LLM baseline ids used by faithful_llm_runners / run_real_llm_eval.
STAGE_REACT = "single_react_llm_agent"
STAGE_AA = "agent_attention_llm_tuned"
STAGE_AA_LITE = "agent_attention_llm_lite"
STAGE_MOA = "moa_style_llm_agent"

CASCADE_POLICIES: dict[str, dict[str, Any]] = {
    "react_aa_moa": {
        "policy_id": "react_aa_moa",
        "label": "direct → AA → MoA",
        "stages": [STAGE_REACT, STAGE_AA, STAGE_MOA],
        "description": "FrugalGPT-style escalation on pytest failure.",
    },
    "react_moa": {
        "policy_id": "react_moa",
        "label": "direct → MoA rescue",
        "stages": [STAGE_REACT, STAGE_MOA],
        "description": "Skip AA; escalate only to MoA on cheap-route failure.",
    },
    "react_aa_lite": {
        "policy_id": "react_aa_lite",
        "label": "direct → AA lite → MoA",
        "stages": [STAGE_REACT, STAGE_AA_LITE, STAGE_MOA],
        "description": "Escalate to lite AA (no verifier/memory) before MoA rescue.",
    },
}

ESCALATION_TRIGGER_TABLE: list[dict[str, str]] = [
    {
        "stage": "1 → 2",
        "from": STAGE_REACT,
        "to": STAGE_AA,
        "trigger": "executable_pytest end-task label == fail",
        "future": "verifier confidence < threshold OR repeated patch apply failure",
    },
    {
        "stage": "2 → 3",
        "from": STAGE_AA,
        "to": STAGE_MOA,
        "trigger": "executable_pytest end-task label == fail after AA attempt",
        "future": "low aggregator confidence OR critic failure signal",
    },
    {
        "stage": "1 → 2 (react_moa only)",
        "from": STAGE_REACT,
        "to": STAGE_MOA,
        "trigger": "executable_pytest end-task label == fail",
        "future": "same as react_aa_moa stage-1 trigger",
    },
    {
        "stage": "1 → 2 (react_aa_lite)",
        "from": STAGE_REACT,
        "to": STAGE_AA_LITE,
        "trigger": "executable_pytest end-task label == fail",
        "future": "fail-only; no preemptive AA on pass",
    },
    {
        "stage": "2 → 3 (react_aa_lite)",
        "from": STAGE_AA_LITE,
        "to": STAGE_MOA,
        "trigger": "executable_pytest end-task label == fail after AA lite",
        "future": "same as react_aa_moa stage-2 trigger",
    },
]


def policy_for(policy_id: str) -> dict[str, Any]:
    if policy_id not in CASCADE_POLICIES:
        raise ValueError(f"Unknown cascade policy_id={policy_id!r}")
    return CASCADE_POLICIES[policy_id]


def cascade_baseline_id(policy_id: str) -> str:
    return f"cascade_{policy_id}_llm"


CASCADE_LLM_BASELINE_IDS = tuple(cascade_baseline_id(policy_id) for policy_id in CASCADE_POLICIES)
POLICY_BY_BASELINE: dict[str, str] = {
    cascade_baseline_id(policy_id): policy_id for policy_id in CASCADE_POLICIES
}


def policy_id_from_baseline_id(baseline_id: str) -> str:
    if baseline_id not in POLICY_BY_BASELINE:
        raise ValueError(f"Unknown cascade baseline_id={baseline_id!r}")
    return POLICY_BY_BASELINE[baseline_id]


def cascade_config_for(policy_id: str) -> dict[str, Any]:
    policy = policy_for(policy_id)
    cfg = {
        "controller_policy": "cascade",
        "routing_policy": "direct_first_escalation",
        "cascade_policy_id": policy_id,
        "cascade_stages": list(policy["stages"]),
        "escalation_trigger": "executable_pytest_fail",
        "label": policy["label"],
        "note": policy.get("description", ""),
    }
    if STAGE_AA_LITE in policy["stages"]:
        cfg["aa_lite_ablation_id"] = "aa_lite_escalation"
    return cfg
