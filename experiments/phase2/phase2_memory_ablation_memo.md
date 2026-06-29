# Phase 2 Memory Ablation Experiment Memo

Date: 2026-06-26  
Control: `aa_tuned_control` (P2 tuned Agent-Attention)  
Evidence level: experiment-observed (toy runtime)

## Ablations Run

| Ablation ID | Single change |
|-------------|---------------|
| `aa_tuned_control` | Full memory read/write, load-time quarantine |
| `aa_no_memory` | Memory disabled |
| `aa_memory_read_only` | Reads on, writes off |
| `aa_success_only_memory_write` | Write only on success |
| `aa_unfiltered_memory` | Load harmful memory, no read-time quarantine |
| `aa_quarantine_aware` | Load harmful memory, filter harmful at retrieval |

72 runs = 12 tasks × 6 ablations.

## Full Matrix Results (12 tasks)

| Ablation | Success | Cost-Norm Success | Cost | Memory Reads | Harmful Reads | Neg. Transfer |
|----------|---------|-------------------|------|--------------|---------------|---------------|
| aa_tuned_control | 66.7% | 0.207 | 2.03 | 40 | 0 | 0 |
| **aa_no_memory** | **75.0%** | **0.242** | 1.98 | 0 | 0 | 0 |
| aa_memory_read_only | 66.7% | 0.207 | 2.03 | 40 | 0 | 0 |
| aa_success_only_memory_write | 66.7% | 0.207 | 2.03 | 40 | 0 | 0 |
| aa_unfiltered_memory | 66.7% | 0.207 | 2.03 | 44 | **4** | **12** |
| aa_quarantine_aware | 66.7% | 0.207 | 2.03 | 40 | 0 | 0 |

## Negative-Memory Probe (`phase0_seed_negative_memory_001`)

| Ablation | Success | Harmful Reads | Neg. Transfer |
|----------|---------|---------------|---------------|
| aa_tuned_control | 0% | 0 | 0 |
| aa_no_memory | 0% | 0 | 0 |
| aa_unfiltered_memory | 0% | **4** | **12** |
| aa_quarantine_aware | 0% | **0** | **0** |

## Key Findings

1. **No-memory beats control on aggregate success (75% vs 66.7%)** — memory adds overhead without improving toy oracle labels on this suite.
2. **Quarantine-aware retrieval works** — `aa_quarantine_aware` matches control metrics while `aa_unfiltered_memory` logs harmful reads and negative-transfer cases.
3. **Read-only / success-only write** — no measurable difference from control on 12 tasks (writes may not affect single-run toy tasks).
4. **Negative-memory task** — all variants fail success oracle; unfiltered exposes harmful memory in logs; quarantine prevents harmful reads.

## Claims We Can Make

- Memory is not uniformly beneficial; **disabling memory improves success** on current toy suite.
- Read-time quarantine **blocks harmful memory reads** while load-time quarantine alone is insufficient when harmful entries are loaded.
- Scorer can now detect **harmful reads and negative transfer** when harmful memory is retrieved.

## Claims We Cannot Make

- Memory improves cross-task transfer (not demonstrated).
- Quarantine improves success rate on negative-memory probe (success still 0% for all).
- Results transfer to real LLM / executable tasks.

## Reproduce

```bash
python3 experiments/phase2/phase2_memory_ablation_runner.py
cat experiments/metrics/phase2_memory_ablation_summary.json
```

## Next Steps

1. Phase 3 textual backprop replay on failed trajectories.
2. Per-task-family memory analysis.
3. Executable verifier for code tasks.
