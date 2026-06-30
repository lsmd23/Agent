# T1: Terminal-Bench Adapter

Suggested agent: Bridger

## Objective

Build the first adapter that lets Agent-Attention baselines run against Terminal-Bench-style tasks and emit the project trajectory envelope.

## Dependencies

- Requires T0.
- If T0 says Docker/Harbor is blocked, create an adapter skeleton plus a local pytest fallback, then stop before claiming Terminal-Bench execution.

## Required Reads

- `docs/next_iteration/reports/T0_environment_report.md`
- `docs/next_iteration/reports/T0_benchmark_recon.md`
- `experiments/real_benchmarks/run_real_llm_eval.py`
- `experiments/real_benchmarks/faithful_llm_runners.py`
- `experiments/real_benchmarks/real_llm_envelope.py`
- `docs/deliverables/07/trajectory_schema.json`
- `docs/deliverables/08/baseline_specs.md`

## Required Work

1. Inspect the current official Terminal-Bench/Harbor interface.
2. Decide the lightest integration path:

- Wrap Agent-Attention as a Harbor-compatible agent, or
- Create a runner that invokes Terminal-Bench tasks and records equivalent outputs, or
- Produce a strict adapter skeleton if Harbor requires capabilities not yet available.

3. Implement support for at least these baselines:

- `single_react_llm_agent`
- `fixed_workflow_llm_agent`
- `agent_attention_llm_tuned`

4. Ensure every run emits:

- `benchmark_id`
- `task_id`
- `baseline_id`
- model/provider config without secrets
- final success label
- model calls
- latency
- timeout status
- error/failure type if failed
- path to raw benchmark logs if available

## Suggested File Targets

Create as needed:

- `experiments/terminal_bench/`
- `experiments/terminal_bench/run_terminal_bench_smoke.py`
- `experiments/terminal_bench/adapter.py`
- `tests/test_terminal_bench_adapter.py`

## Deliverables

- Runnable smoke adapter or explicit blocked skeleton.
- `docs/next_iteration/reports/T1_terminal_bench_adapter.md`
- One command that the T2 agent can run.

## Acceptance Criteria

- Unit tests pass.
- Adapter can list or select a small task subset, or documents the exact external blocker.
- No benchmark-wide performance claim is made.

## Failure Modes

- Losing benchmark logs, making failures impossible to audit.
- Comparing baselines with different budgets.
- Producing only route-proxy labels instead of end-task results.
