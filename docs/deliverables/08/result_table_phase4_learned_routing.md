# Phase 4 Learned Routing Results

> From `experiments/metrics/phase4_learned_routing_summary.json` on 2026-06-26.

## Router Comparison (12 tasks, P2 tuned base)

| Router | Success | Cost-Norm | Proxy Regret | Oracle Regret |
|--------|---------|-----------|--------------|---------------|
| aa_lexical_router (control) | 66.7% | 0.207 | 0.344 | 0.317 |
| aa_rule_router | 41.7% | 0.131 | 0.375 | 0.604 |
| **aa_learned_router_replay** | **75.0%** | **0.222** | 0.432 | **0.221** |
| aa_oracle_router (upper bound) | 91.7% | 0.278 | 0.581 | 0.0 |

## Interpretation

Learned replay router **beats lexical tuned control** on success (+8.3pp) and **oracle regret** (0.221 vs 0.317) on the toy suite. Still below oracle upper bound and Phase 1 ReAct (91.7%).

Training used oracle labels plus Phase 1 faithful trajectories (1523 rows, 79.3% train accuracy).

## Reproduce

```bash
python3 experiments/phase4/phase4_learned_routing_runner.py
```
