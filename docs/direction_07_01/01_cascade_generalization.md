# D01: Cascade Generalization Brief

## Objective

Determine whether `cascade_react_aa_lite_llm` is a robust routing principle or a policy that overfits the current 26 local code fixtures.

## Why This Matters

The cascade is the project's first positive end-task result. Before adding complexity, future agents should test whether this result survives task expansion, model changes, prompt perturbations, and budget changes.

## Required Inputs

- `experiments/metrics/code_cascade_wave3_summary.json`
- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/metrics/t4_pareto_summary.json`
- `experiments/real_benchmarks/run_real_llm_eval.py`
- cascade implementation files under `experiments/`
- `docs/deliverables/08/result_table_code_suite_matrix.md`

## Research Questions

1. Does cascade AA lite remain on the Pareto frontier when task count grows?
2. Which tasks trigger escalation, and are those triggers justified?
3. Does the cascade still win under stricter call or token budgets?
4. Does the policy survive prompt wording changes?
5. Does it survive a second model/provider?

## Suggested Experiments

### Experiment A: Task Expansion Replay

Run cascade policies on any newly added local executable tasks. Compare:

- `single_react_llm_agent`
- `moa_style_llm_agent`
- `cascade_react_aa_lite_llm`
- `cascade_react_aa_moa_llm`

Metrics:

- raw success
- mean calls
- total tokens
- cost per rescued task
- escalation precision
- escalation recall

### Experiment B: Budget Sweep

Evaluate cascade under:

- strict: max escalation once
- default: current policy
- loose: allow MoA fallback

Report whether extra budget buys success or only latency.

### Experiment C: Trigger Audit

For each escalated task, classify:

- direct failed, escalation rescued
- direct failed, escalation failed
- direct would have succeeded, escalation unnecessary
- verifier/prompt parse caused false escalation

## Acceptance Criteria

`supports_direction` if:

- cascade remains Pareto-relevant on expanded or perturbed tasks;
- escalation rescues at least some tasks that ReAct misses;
- average cost stays materially below MoA.

`weak_or_inconclusive` if:

- cascade still works but confidence intervals overlap heavily;
- improvement depends on one or two tasks.

`falsified_or_blocked` if:

- cascade no longer beats ReAct on cost-quality;
- cascade collapses into MoA-like cost;
- triggers are mostly unnecessary.

## Deliverables

- `docs/direction_07_01/reports/D01_cascade_generalization.md`
- updated or new metrics JSON under `experiments/metrics/`
- regeneration command
- concise table comparing cascade vs ReAct/MoA

## Guardrails

- Do not tune cascade thresholds on the test subset and report it as held-out.
- Do not claim generality from local fixtures alone.
- Keep raw success and cost separate in all tables.
