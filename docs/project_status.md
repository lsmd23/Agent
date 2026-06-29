# Project Status

Last updated: 2026-06-26

## Milestone: Executable Code Verifier (Phase A)

Phase1 **code tasks** now have pytest fixtures + end-task scoring. Real-LLM matrix from prior milestone remains on route-proxy for non-code tasks.

## What Works

### Runtime & toy experiments

| Phase | Scope | Key result |
|-------|-------|------------|
| Phase 1 | 6 faithful baselines × 12 tasks | ReAct 91.7%; AA default 25% → tuned 66.7% |
| Phase 2 | 6 memory ablations | no-memory 75% > control 66.7% |
| Phase 3 | 4 failure attributions | 3/4 replay fix, all quarantined |
| Phase 4 | 4 router variants | learned replay 75% > lexical 66.7% |

Metrics: `experiments/metrics/phase{1,2,3,4}_*_summary.json`

### Executable code verifier (new)

| Component | Path |
|-----------|------|
| 5 fixtures (6 code tasks) | `experiments/fixtures/code/` |
| Verifier | `experiments/real_benchmarks/code_verifier.py` |
| Task oracles | `experiments/real_benchmarks/task_oracles.py` |
| Fixture validator | `experiments/real_benchmarks/validate_code_fixtures.py` |

Code tasks in `experiments/tasks/phase1_tasks.jsonl` use `success_oracle.oracle_type: pytest_passes`. Real-LLM code prompts inject fixture repo snapshot + failing unittest output; models must return a `# file:` python block.

Latest executable eval (6 code tasks × 7 baselines): `experiments/metrics/real_llm_phase1_code_executable_v2.json` — end-task accuracy 0% → **88–100%** per baseline after fixture-aware prompts (prior v1: all 0%).

```bash
python3 experiments/real_benchmarks/validate_code_fixtures.py
python3 -m unittest tests.test_code_verifier -v
```

### Real LLM (Qwen3-30B via Paratera)

| Suite | Runs | Primary metric |
|-------|------|----------------|
| GSM8K multi-baseline | 60 | exact-match (direct 95%, ReAct/AA-tuned 100%) |
| GSM8K faithful full | 140 | exact-match (AA-tuned 90%, MoA 100%) |
| Phase1 faithful/memory/router | 204 | route-proxy (AA-tuned pass 75%) |

Comparison vs toy: `experiments/metrics/real_vs_toy_comparison.json`

## Known Limitations

1. Phase1 **search/research** tasks still use route-proxy or rubric placeholders.
2. GSM8K does not stress routing; good sanity check only.
3. Real-LLM Phase1 code runs scored with executable oracle v2 (88–100% end-task pass); v1 trajectories lacked fixture context.
4. Trajectories gitignored; regenerate with `run_real_llm_eval.py`.

## Next Iteration

1. Re-run real LLM on 6 code tasks with executable end-task scoring. **Done (v2): fixture-aware prompts; see `real_llm_phase1_code_executable_v2.json`.**
2. Expand task count per family (≥50) + bootstrap CI.
3. **Cost–quality Pareto** figure (matched token budget).
4. Search/research rubric oracles.
5. Publication gap audit: `docs/publication_gap_assessment.md`.

## Tests

```bash
python3 -m unittest discover -s tests   # 57 passing
```

## Key Docs

- `docs/decision_log.md` — decisions
- `docs/deliverables/08/result_table_real_vs_toy.md` — toy vs real LLM
- `docs/deliverables/08/result_table_real_llm_eval.md` — baseline registry
- `.env.example` — API config template (never commit `.env`)
