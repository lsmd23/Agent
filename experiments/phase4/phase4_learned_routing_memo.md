# Phase 4 Learned Routing Experiment Memo

Date: 2026-06-26  
Control: `aa_lexical_router` (P2 tuned + lexical semantic_match)  
Evidence level: experiment-observed (toy runtime)

## Router Variants

| Router ID | Strategy | Purpose |
|-----------|----------|---------|
| `aa_lexical_router` | lexical | Phase 0–2 control |
| `aa_rule_router` | rule | Deterministic intent rules |
| `aa_learned_router_replay` | learned | Logistic router trained on oracle labels + Phase 1 trajectories |
| `aa_oracle_router` | oracle upper bound | Offline utility matrix (calibration only) |

Training: 1523 rows, 79.3% train accuracy. Policy saved to `experiments/phase4/learned_router_policy.json`.

## Results (12 tasks, tuned Agent-Attention)

| Router | Success | Cost-Norm Success | Cost | Proxy Regret | Oracle Regret |
|--------|---------|-------------------|------|--------------|---------------|
| aa_lexical_router | 66.7% | 0.207 | 2.03 | 0.344 | 0.317 |
| aa_rule_router | 41.7% | 0.131 | 1.84 | 0.375 | 0.604 |
| **aa_learned_router_replay** | **75.0%** | **0.222** | 2.34 | 0.432 | **0.221** |
| aa_oracle_router | 91.7% | 0.278 | 2.30 | 0.581 | 0.0 |

## Key Findings

1. **Learned router improves success over lexical control** (+8.3pp to 75%) on toy suite — first routing variant to beat tuned lexical on aggregate success.
2. **Oracle regret decreases** (0.221 vs 0.317) while proxy regret rises slightly — learned policy aligns better with offline oracle utilities but not proxy heuristics.
3. **Rule router underperforms lexical** on this suite (41.7%) — task-family signals need top-k/budget context, not semantic_match alone.
4. **Oracle upper bound ~92%** — matches ReAct-tier performance; gap to learned (75%) shows remaining headroom.

## Claims We Can Make

- Trajectory + oracle replay training produces a **deployable lightweight router** that improves toy success vs lexical tuned control.
- Offline oracle matrix enables **true oracle regret** reporting alongside proxy regret.
- Learned routing is **not a win over ReAct** (91.7% oracle bound / 91.7% single_react from Phase 1).

## Claims We Cannot Make

- Learned router generalizes beyond 12 toy tasks (train includes same task oracle labels).
- Embedding or bandit routers are unnecessary (not tested head-to-head here).
- Success gains transfer to real LLM execution.

## Reproduce

```bash
python3 experiments/phase4/phase4_learned_routing_runner.py
python3 -m unittest tests.test_learned_routing -v
```

Artifacts:
- `experiments/metrics/phase4_learned_routing_summary.json`
- `experiments/phase4/oracle_matrix.json`
- `experiments/trajectories/phase4_learned_routing/` (48 runs)
