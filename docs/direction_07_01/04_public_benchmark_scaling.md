# D04: Public Benchmark Scaling Brief

## Objective

Decide how to move from local executable fixtures toward public benchmark evidence without wasting compute on unstable evaluations.

## Why This Matters

The current positive result is local and small. A main-track paper needs public or larger benchmark evidence. However, Terminal-Bench is currently too weak and SWE-bench may be too heavy for the local environment.

## Required Inputs

- `docs/publication_gap_assessment.md`
- `docs/deliverables/08/result_table_code_suite_matrix.md`
- `docs/deliverables/08/result_table_terminal_bench_full_steps12.md`
- `docs/direction_07_01/03_terminal_bench_aci_and_task_triage.md`
- official benchmark docs for Terminal-Bench, SWE-bench Lite, HumanEval/MBPP if used

## Candidate Paths

### Path A: Terminal-Bench Stable Subset

Best aligned with terminal/code agent architecture. Highest relevance, but currently unstable.

Minimum credible step:

- 10 stable tasks
- 4 baselines
- matched budgets
- clear environment-vs-agent failure labels

### Path B: SWE-bench Lite / Verified Micro-Subset

Strong public benchmark signal, but environment and runtime cost may be high.

Minimum credible step:

- 5-10 verified tasks
- one strong baseline and one cascade policy
- exact patch verifier

### Path C: HumanEval/MBPP Repair-Style Controlled Benchmark

Lower environment cost, easier to scale. Less agentic than TB/SWE-bench.

Minimum credible step:

- 50+ tasks
- executable scoring
- cascade vs ReAct/MoA

### Path D: Expanded Local Fixtures

Fastest iteration path. Not enough for main-track alone.

Minimum credible step:

- 50-100 tasks
- train/test split
- no answer leakage
- multiple task families

## Research Questions

1. Which path gives the best evidence-per-compute ratio?
2. Which path stresses routing rather than one-shot patching?
3. Which path can be reproduced by another researcher?
4. Which path allows enough tasks for confidence intervals?

## Acceptance Criteria

`supports_direction` if:

- one public benchmark path has a concrete setup and pilot result;
- expected compute is feasible;
- task subset is pre-registered.

`weak_or_inconclusive` if:

- setup works but task count or pass rate is too low.

`falsified_or_blocked` if:

- environment instability makes matched comparisons impossible.

## Deliverables

- `docs/direction_07_01/reports/D04_public_benchmark_scaling.md`
- benchmark path recommendation
- estimated cost/time table
- pre-registered task subset proposal
- exact smoke command

## Guardrails

- Do not use local fixtures as a substitute for public benchmark evidence in main-track claims.
- Do not start full benchmark runs before smoke validation.
- Do not compare baselines on different subsets or budgets.
