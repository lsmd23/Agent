# Phase 1 Faithful Baseline Results

> Generated from `experiments/metrics/phase1_faithful_matrix_by_baseline.json` on 2026-06-26.
> Task set: `phase1_mixed` — 12 tasks (4 code, 4 search, 4 mini-research) from `experiments/tasks/phase1_tasks.jsonl`.
> **Evidence level**: experiment-observed on faithful toy control policies; not real LLM.

## Baseline Matrix (Equal Budget)

| System | Task Set | Runs | Success | Cost-Normalized Success | Cost | Module Calls | Repeated Ratio | Premature Halt | Memory Reuse | Negative Transfer | Route Entropy | Proxy Regret | Known Deviations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `single_react_agent` | `phase1_mixed` | 12 | 0.917 | 0.348 | 1.60 | 3.83 | 0.208 | 0.000 | N/A | 0 | 1.514 | 0.463 | toy runtime, proxy regret |
| `fixed_workflow_agent` | `phase1_mixed` | 12 | 0.917 | 0.316 | 1.90 | 4.17 | 0.275 | 0.083 | N/A | 0 | 1.504 | 0.377 | toy runtime, proxy regret |
| `full_history_agent` | `phase1_mixed` | 12 | 0.917 | 0.348 | 1.60 | 3.83 | 0.208 | 0.000 | N/A | 0 | 1.514 | 0.463 | toy runtime, proxy regret |
| `retrieval_memory_agent` | `phase1_mixed` | 12 | 0.833 | 0.318 | 1.60 | 3.83 | 0.208 | 0.000 | 40 reads | 0 | 1.514 | 0.463 | toy runtime, proxy regret |
| `moa_style_agent` | `phase1_mixed` | 12 | 0.083 | 0.017 | 3.10 | 6.08 | 0.283 | 0.417 | N/A | 0 | 2.017 | 0.718 | toy runtime, proxy regret |
| `agent_attention_agent` | `phase1_mixed` | 12 | 0.250 | 0.066 | 2.93 | 7.42 | 0.458 | 0.000 | 39 reads | 0 | 1.843 | 0.225 | toy runtime, proxy regret |

## Interpretation (No Architecture Win Claim)

1. **Single ReAct / full-history / fixed workflow** tie at ~92% success with lowest cost (~1.6–1.9 activation cost).
2. **Agent-Attention (lexical top-k=2)** has **lowest proxy route regret (0.225)** but **worst success (25%)** and high budget exhaustion (83%) — sparse multi-module activation is expensive on toy tasks.
3. **MoA-style** fails under equal budget (8% success) — parallel proposer cost dominates.
4. **Retrieval-memory** slightly below ReAct (83% vs 92%) with same cost — memory reads do not improve toy oracle labels yet.
5. **Negative transfer** not detected in scorer (0 cases) — harmful memory labeling still too optimistic.

## Counterexamples Observed

| Class | Observation |
| --- | --- |
| Proposed under-routes / overspends | `agent_attention_agent` loses to `single_react_agent` on success and cost-normalized success despite lower proxy regret. |
| MoA raw cost loss | `moa_style_agent` high module calls (6.08) and budget exhaustion (50%) with 8% success. |
| Retrieval-only does not explain gain | `retrieval_memory_agent` does not beat `single_react_agent`. |

## Reproduce

```bash
python3 experiments/phase1/phase1_faithful_runner.py
python3 docs/deliverables/07/scoring_script.py \
  experiments/trajectories/phase1_faithful_matrix/*.json \
  --output experiments/metrics/phase1_faithful_matrix_metrics.json
```

## Next Steps

- Phase 2 memory ablations (`aa_no_memory`, quarantine on `phase0_seed_negative_memory_001`).
- Tune Agent-Attention budget/top-k or adaptive activation before claiming routing wins.
- Replace toy oracle success labels with executable verifiers for code tasks.
