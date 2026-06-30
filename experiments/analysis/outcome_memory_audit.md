# Outcome Memory Audit (Brief D)

## Scope

Outcome-memory router on the 26-task code suite matrix (5 baselines, no new LLM calls).
Memory stores **verified route outcomes** keyed by task family + error signature — not task answers.

## Inputs Read

- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/metrics/oracle_route_matrix.json`
- `experiments/tasks/phase1_code_all.jsonl`
- `experiments/llm_runs/code_full_matrix/code_all` (react trajectories for pytest error signatures)
- `docs/deliverables/04/memory_policy.md`
- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief D)

## Method

### Memory schema

- Key: `task_family` + `error_signature`
- Value: `route_outcomes` → success/cost aggregates per route
- Leakage guards reject patch bodies, answers, raw pytest output, and task-id keys.

### Retrieval policy

- exact match on task_family + error_signature
- static override only when memory attempts>=2 and success_rate>=0.5 beats default reward
- cascade escalation ranks rescue routes by observed success_rate then route_reward

### Replay evaluation

- **Primary:** leave-one-out cascade replay — react first, memory-ranked escalation on failure.
- **No-memory baseline:** fixed react→AA→MoA cascade (same stages, default order).
- **Reference baselines:** always-ReAct and retrieval-memory static routes.
- Regret = oracle route reward − selected route reward (Brief A weights).

## Commands Run

```bash
python3 experiments/analysis/outcome_memory_router.py
```

## Artifacts Created

- `experiments/metrics/outcome_memory_diagnostic.json`
- `experiments/analysis/outcome_memory_audit.md`

## Results

| Policy | Accuracy | Mean regret vs oracle |
|--------|----------|------------------------|
| Fixed cascade (no memory) | 100.0% | 0.0649 |
| Outcome memory (LOO cascade) | 100.0% | 0.0640 |
| ReAct only (reference) | — | 0.1396 |
| Transcript memory (reference) | — | 0.1945 |

- **Δ regret vs fixed cascade (primary):** +0.0010 (positive = outcome memory lower regret)
- **Δ regret vs ReAct only:** +0.0757
- **Δ regret vs transcript memory:** +0.1305
- Memory hit rate (LOO cascade): 15.4%
- Unique error signatures: 12

### Leakage audit

- Passed: **True**
- No patch/answer leakage detected in stored memory entries.

### Alternate eval: LOO static route override

- Mean regret: 0.2029
- Memory hit rate: 19.2%

## Interpretation

Schema, retrieval, and leakage guards are in place, but at N=26 the memory rarely changes routing vs fixed react→AA→MoA cascade. Treat as diagnostic infrastructure; expand task families or failure diversity before claiming memory-driven routing gains.

**Evidence outcome:** `weak_or_inconclusive`

## Next Questions

- Expand failure-class diversity so memory keys accumulate ≥3 observations per signature.
- Brief E: can cheap features predict escalation route when outcome memory is cold-start?
- Gate transcript memory off in escalation slot; A/B outcome-only vs no-memory live.
