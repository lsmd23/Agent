# Phase 3 Textual Backprop Results

> From `experiments/metrics/phase3_backprop_summary.json` on 2026-06-26.

## Lifecycle Decisions (4 aa_tuned_control failures)

| Task | Confidence | Replay Improved | Decision |
|------|------------|-----------------|----------|
| phase0_seed_negative_memory_001 | 0.68 | no | reject |
| phase1_code_doc_001 | 0.68 | yes (+1.0 success) | quarantine |
| phase1_code_import_001 | 0.68 | yes (+1.0 success) | quarantine |
| phase1_search_conflict_001 | 0.68 | yes (+1.0 success) | quarantine |

## Aggregate

| Metric | Value |
|--------|-------|
| Accept rate | 0% |
| Quarantine rate | 75% |
| Reject rate | 25% |
| Replay improvement rate | 75% |

## Interpretation

Updates that **repair replay** can still be **quarantined** when confidence stays below the `0.70` accept gate. No auto-apply occurred — consistent with conservative Subtask 05 policy.
