# P2 Agent-Attention Tuning Experiment Memo

Date: 2026-06-26  
Evidence level: experiment-observed (toy runtime, faithful control policy)

## Tuning Changes

Implemented in `src/agent_attention_runtime.py`, exposed via `agent_attention_agent_tuned`:

| Parameter | Default | Tuned |
|-----------|---------|-------|
| `adaptive_top_k_enabled` | false | **true** |
| `max_top_k` | — | 3 |
| `strong_budget_gate` | false | **true** |
| `budget_cost_fraction` | — | 0.30 |
| `cost_quality_epsilon` | — | 0.05 |

### Adaptive top-k policy

- k=1 when uncertainty/risk low and budget tight
- k=2 on failure signals or low confidence
- k=3 on high risk when budget permits
- k→1 when repeated action ratio > 0.35 or remaining budget < 1.0

### Strong budget gate

Block module activation when `module.cost > 30% * remaining_budget`, unless high risk, verifier required, or recovery after failure.

## Results (12 tasks, default vs tuned)

| Metric | Default | Tuned | Δ |
|--------|---------|-------|---|
| Success | 25.0% | **66.7%** | **+41.7pp** |
| Cost-normalized success | 0.066 | **0.207** | **+0.141** |
| Mean activation cost | 2.93 | **2.03** | **−0.90** |
| Budget exhaustion rate | 83.3% | **0.0%** | **−83.3pp** |
| Proxy route regret | 0.225 | 0.344 | +0.119 |
| Module calls | 7.42 | 7.42 | 0 |

## Comparison to Best Baseline (Phase 1 faithful matrix)

| System | Success | Cost-Norm Success |
|--------|---------|-------------------|
| single_react_agent | 91.7% | 0.348 |
| **agent_attention_tuned** | **66.7%** | **0.207** |
| agent_attention_default | 25.0% | 0.066 |

Tuned Agent-Attention **closes much of the gap** but still trails ReAct on toy oracle labels.

## Claims We Can Make

- Adaptive top-k + strong budget gate ** materially improves** Agent-Attention on equal-budget toy tasks.
- Budget exhaustion was the primary failure mode for default Agent-Attention (83% → 0%).
- Lower proxy regret does not guarantee higher success; tuned variant accepts slightly higher regret for better cost discipline.

## Claims We Cannot Make

- Tuned Agent-Attention beats single ReAct (still 66.7% vs 91.7%).
- Tuning generalizes to real LLM tasks.
- Proxy regret increase is acceptable without oracle route labels.

## Reproduce

```bash
python3 experiments/phase1/phase1_tuned_comparison.py
cat experiments/metrics/phase1_tuned_comparison_summary.json
```

## Next Steps

1. Re-run full faithful matrix with `agent_attention_agent_tuned` as proposed row.
2. Phase 2 memory ablation on tuned control.
3. Per-task-family breakdown (code vs search vs research).
