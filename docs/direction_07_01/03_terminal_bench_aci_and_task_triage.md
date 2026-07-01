# D03: Terminal-Bench ACI And Task Triage Brief

## Objective

Improve the Terminal-Bench agent-computer interface and decide which task subset is appropriate for architecture evaluation.

## Why This Matters

The full 7-task Terminal-Bench matrix produced only 3/35 passes. This is not enough to compare routing policies. The current bottleneck is likely long-horizon execution and task/environment handling, not sparse routing itself.

## Required Inputs

- `docs/deliverables/08/result_table_terminal_bench_full_steps12.md`
- `experiments/metrics/t3_full_steps12_summary.json`
- `experiments/terminal_bench/`
- raw `shell_steps.json` and `model_calls.json` under Terminal-Bench run dirs
- SWE-agent paper/design notes if available

## Research Questions

1. Which TB failures are environment/setup issues versus agent planning failures?
2. Does the shell loop expose enough observations for recovery?
3. Which tasks are too hard or unstable for current architecture evaluation?
4. Can a smaller stable TB subset produce meaningful comparisons?

## Failure Taxonomy

Classify each failed run:

- environment/bootstrap failure
- invalid shell command
- missing observation
- no test execution
- repeated/no-op command loop
- wrong file edit
- wrong server/process management
- timeout with progress
- timeout without progress
- benchmark oracle mismatch

## Suggested Experiments

### Experiment A: Run Log Audit

Manually or programmatically inspect all 35 runs from `t3_full_steps12_summary.json`.

Output:

- per-task failure profile
- whether the task is currently suitable for agent comparison
- ACI improvement needed

### Experiment B: ACI Microbenchmarks

Create tiny controlled terminal tasks that test:

- file read
- file edit
- run tests
- start server
- inspect process
- recover from failed command

These are not paper results; they are interface diagnostics.

### Experiment C: Stable TB Subset

Pre-register a subset of TB tasks that:

- does not require flaky external network;
- has reproducible setup;
- can be solved by a competent shell agent;
- provides meaningful multi-step pressure.

## Acceptance Criteria

`supports_direction` if:

- environment failures drop materially;
- agent failure taxonomy becomes clear;
- at least 5 stable TB tasks are identified.

`weak_or_inconclusive` if:

- ACI improves logs but pass rate does not change.

`falsified_or_blocked` if:

- Docker/TB environment remains unstable;
- tasks cannot be reproduced enough for matched comparisons.

## Deliverables

- `docs/direction_07_01/reports/D03_terminal_bench_aci_and_task_triage.md`
- per-run failure taxonomy table
- stable TB subset manifest proposal
- recommended ACI changes

## Guardrails

- Do not report TB architecture wins from N <= 7.
- Do not mix environment failures into agent performance without labeling.
- Do not scale to 20+ TB tasks until stable subset pass rate is non-trivial.
