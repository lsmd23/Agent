# T7: Real-Task Router, Memory, And Textual-Backprop Ablations

Suggested agent: Hopper

## Objective

Move router, memory, and textual-backprop claims from toy/proxy replay toward real-task evidence.

## Dependencies

- Requires T3 per-task trajectories.
- Benefits from T5 local executable suite.

## Required Reads

- `experiments/phase2/phase2_memory_ablation_runner.py`
- `experiments/phase3/phase3_backprop_runner.py`
- `experiments/phase4/phase4_learned_routing_runner.py`
- `docs/deliverables/04/memory_policy.md`
- `docs/deliverables/05/textual_gradient_policy.md`
- `docs/deliverables/03/router_design.md`

## Required Work

1. Router ablations on real or executable tasks:

- lexical/rule router
- learned router
- oracle upper bound where computable
- random or cheap-router lower bound if useful

2. Memory ablations:

- no memory
- read-only
- success-only write
- unfiltered memory
- quarantine-aware memory

3. Textual-backprop experiment:

- collect real failures
- attribute component
- propose update
- replay on failed case
- test held-out cases for regression

4. Report not only success but negative transfer and cost.

## Deliverables

- `experiments/metrics/real_task_router_ablation_summary.json`
- `experiments/metrics/real_task_memory_ablation_summary.json`
- `experiments/metrics/real_task_backprop_summary.json`
- `docs/deliverables/08/result_table_real_task_ablations.md`
- `docs/next_iteration/reports/T7_real_task_ablations.md`

## Acceptance Criteria

- Uses end-task executable outcomes where possible.
- Train/test split prevents memory leakage.
- Learned router is evaluated out-of-sample.
- Any improvement claim includes cost and confidence intervals if enough tasks exist.

## Failure Modes

- Training and testing the router on the same failures.
- Letting memory store benchmark answers.
- Treating a replay fix as evidence of general learning.
