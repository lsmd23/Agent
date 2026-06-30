# T2: Terminal-Bench Smoke Matrix

Suggested agent: Faraday

## Objective

Run a tiny real benchmark matrix to prove the adapter, baselines, model endpoint, logging, and scoring all work end to end.

## Dependencies

- Requires T1.

## Required Reads

- `docs/next_iteration/reports/T1_terminal_bench_adapter.md`
- `docs/publication_gap_assessment.md`
- `docs/deliverables/08/result_table_real_llm_eval.md`
- Any new files under `experiments/terminal_bench/`

## Required Work

1. Select 5-10 tasks.
2. Run at least 3 baselines:

- ReAct-style baseline
- fixed workflow baseline
- Agent-Attention tuned baseline

3. Enforce matched budgets:

- same model
- same max model calls
- same token or response limit where available
- same task timeout
- same tool permissions

4. Produce compact metrics:

- success rate
- mean model calls
- mean latency
- timeout rate
- failure category

## Deliverables

- `experiments/metrics/terminal_bench_smoke_summary.json`
- `docs/next_iteration/reports/T2_terminal_bench_smoke_matrix.md`
- Regeneration command

## Acceptance Criteria

- At least one task runs end to end for every baseline.
- Failures are classified as agent failure, environment failure, timeout, parsing failure, or scoring failure.
- The report states whether moving to T3 is justified.

## Failure Modes

- Spending a large API budget before the smoke path is stable.
- Cherry-picking only successful tasks.
- Treating smoke accuracy as a research result.
