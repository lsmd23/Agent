# T4: Statistics And Pareto Analysis

Suggested agent: Noether

## Objective

Turn raw benchmark rows into statistically interpretable tables and plots for a paper.

## Dependencies

- Requires T3.

## Required Reads

- `docs/deliverables/07/metrics_definitions.md`
- `docs/deliverables/08/result_table_template.md`
- T3 summary outputs

## Required Work

1. Implement or extend scoring utilities to compute:

- success rate
- bootstrap confidence intervals over tasks
- paired baseline deltas
- mean/median model calls
- mean/median latency
- timeout rate
- cost-normalized success

2. Produce cost-quality Pareto tables.
3. Separate environment failures from agent failures.
4. Add a per-task paired table for significance and debugging.

## Suggested File Targets

- `experiments/analysis/`
- `experiments/analysis/bootstrap_metrics.py`
- `experiments/metrics/*_with_ci.json`
- `docs/deliverables/08/result_table_cost_quality_pareto.md`

## Deliverables

- Script for CI/Pareto computation.
- JSON summary with confidence intervals.
- Markdown table suitable for paper drafting.
- `docs/next_iteration/reports/T4_statistics_and_pareto.md`

## Acceptance Criteria

- Results can be regenerated from saved per-task rows.
- Confidence intervals are computed by task bootstrap, not by treating model calls as independent samples.
- The report identifies whether Agent-Attention has a credible win, loss, or inconclusive result.

## Failure Modes

- Overstating small differences from tiny samples.
- Ignoring cost or timeout.
- Combining proxy and end-task metrics in one headline number.
