# Project Status

Last updated: 2026-06-29

## Milestone: Instrumentation + Real LLM Matrix Complete

Path A (instrumentation-first) through Phase 4 on **toy runtime**, plus **344 real-LLM runs** across 19 baselines. Ready to iterate toward **publication-grade end-task evaluation**.

## What Works (committed evidence)

### Runtime & toy experiments (route-proxy)

| Phase | Scope | Key result |
|-------|-------|------------|
| Phase 1 | 6 faithful baselines × 12 tasks | ReAct 91.7%; AA default 25% → tuned 66.7% |
| Phase 2 | 6 memory ablations | no-memory 75% > control 66.7% |
| Phase 3 | 4 failure attributions | 3/4 replay fix, all quarantined |
| Phase 4 | 4 router variants | learned replay 75% > lexical 66.7% |

Metrics: `experiments/metrics/phase{1,2,3,4}_*_summary.json`

### Real LLM (Qwen3-30B via Paratera)

| Suite | Runs | Primary metric |
|-------|------|----------------|
| GSM8K multi-baseline | 60 | exact-match (direct 95%, ReAct/AA-tuned 100%) |
| GSM8K faithful full | 140 | exact-match (AA-tuned 90%, MoA 100%) |
| Phase1 faithful/memory/router | 204 | route-proxy (AA-tuned pass 75%) |

Comparison vs toy: `experiments/metrics/real_vs_toy_comparison.json`

## Known Limitations (not bugs — scope boundaries)

1. Phase1 success = **route-proxy**, not executable task completion.
2. GSM8K does not stress routing; good sanity check only.
3. Real-LLM Pass vs Partial splits understate ReAct (Pass+Partial ≈ toy).
4. Trajectories gitignored; regenerate with `run_real_llm_eval.py`.

## Next Iteration (publication path)

1. **Executable code verifier** for Phase1 code tasks (pytest sandbox).
2. Expand task count per family (≥50) + bootstrap CI.
3. **Cost–quality Pareto** figure (matched token budget).
4. Demote route-proxy to mechanism appendix; promote end-task to Table 1.

## Tests

```bash
python3 -m unittest discover -s tests   # 49 passing
```

## Key Docs

- `docs/decision_log.md` — decisions
- `docs/deliverables/08/result_table_real_vs_toy.md` — toy vs real LLM
- `docs/deliverables/08/result_table_real_llm_eval.md` — baseline registry
- `.env.example` — API config template (never commit `.env`)
