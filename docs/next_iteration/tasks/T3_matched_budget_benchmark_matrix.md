# T3: Matched-Budget Benchmark Matrix

Suggested agent: Curie

## Objective

Run the first publication-relevant benchmark matrix under matched budgets.

## Dependencies

- Requires T2.
- May consume T5 local code-suite expansion if Terminal-Bench remains blocked.

## Required Reads

- `docs/next_iteration/reports/T2_terminal_bench_smoke_matrix.md`
- `docs/deliverables/08/ablation_matrix.md`
- `docs/deliverables/08/baseline_specs.md`
- `docs/deliverables/07/metrics_definitions.md`

## Required Work

1. Choose the evaluation set:

- preferred: Terminal-Bench full or 20-30 task pre-registered subset
- fallback: SWE-bench Lite/Verified subset
- fallback: expanded local executable fixture suite

2. Run at least 4 baselines:

- `single_react_llm_agent`
- `fixed_workflow_llm_agent`
- `retrieval_memory_llm_agent`
- `moa_style_llm_agent`
- `agent_attention_llm_tuned`

3. Use matched budgets and record:

- model name and provider
- max calls
- timeout
- token limits if available
- tool permissions
- retries

4. Store only durable summaries in git-trackable paths. Keep raw trajectories regenerable.

## Deliverables

- `experiments/metrics/terminal_bench_matrix_summary.json` or benchmark-specific equivalent
- `experiments/tasks/terminal_bench_subset_manifest.json`
- `docs/deliverables/08/result_table_terminal_bench_matrix.md`
- `docs/next_iteration/reports/T3_matched_budget_benchmark_matrix.md`

## Acceptance Criteria

- Same tasks for all baselines.
- Same model and budget for all baselines.
- End-task success comes from benchmark verifier, not route proxy.
- At least 20 tasks if feasible; otherwise explain why the run remains pilot-only.

## Failure Modes

- Mixing task subsets across baselines.
- Counting environment setup failures as model failures without labeling.
- Reporting no confidence intervals; T4 must have enough per-task rows.
