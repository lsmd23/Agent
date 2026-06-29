# Phase 2 Memory Ablation Results

> From `experiments/metrics/phase2_memory_ablation_summary.json` on 2026-06-26.

## Control vs Ablations (12 tasks, tuned Agent-Attention)

| Ablation | Success | Cost-Norm | Harmful Reads | Neg. Transfer |
|----------|---------|-----------|---------------|---------------|
| aa_tuned_control | 66.7% | 0.207 | 0 | 0 |
| **aa_no_memory** | **75.0%** | **0.242** | 0 | 0 |
| aa_memory_read_only | 66.7% | 0.207 | 0 | 0 |
| aa_success_only_memory_write | 66.7% | 0.207 | 0 | 0 |
| aa_unfiltered_memory | 66.7% | 0.207 | 4 | 12 |
| aa_quarantine_aware | 66.7% | 0.207 | 0 | 0 |

## Counterexample

**`aa_no_memory` beats `aa_tuned_control`** on success and cost-normalized success — memory does not help on this toy suite.

## Negative-Memory Probe

`aa_unfiltered_memory` logs harmful reads; `aa_quarantine_aware` blocks them with identical success/cost to control.
