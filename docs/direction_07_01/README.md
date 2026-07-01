# Direction 2026-07-01: Subagent Exploration Pack

Date: 2026-07-01

This folder is the next dispatch pack after the Wave 2 / Wave 3 exploration. It is not a linear task list. It is a set of focused exploration briefs that can be assigned to future subagents.

## Current Interpretation

The project has reached a useful but narrow positive result:

- `cascade_react_aa_lite_llm` reaches 26/26 on the local executable code suite with 1.50 mean model calls.
- Always-on `agent_attention_llm_tuned` is not a good default policy.
- Oracle route analysis shows route opportunity exists on the 26-task code suite.
- Terminal-Bench is running end to end, but the 7-task full matrix remains weak at 3/35 pass.
- Current "experts" are not sufficiently heterogeneous; Brief H found 96% redundant activation.
- Learned routing, outcome memory, and textual backprop are diagnostic only for now.

The next research shape should be:

> Cost-aware cascade routing with a cheap default path, a lite specialist escalation slot, and expensive aggregation only as rescue.

## Required First Read For Any Subagent

1. `docs/project_status.md`
2. `docs/paper_outline.md`
3. `docs/next_iteration/reports/W2_complete_iteration_goals.md`
4. `docs/deliverables/08/result_table_code_suite_matrix.md`
5. `docs/deliverables/08/result_table_terminal_bench_full_steps12.md`
6. This folder's `00_current_evidence_snapshot.md`
7. The assigned brief file in this folder

## Brief Index

| Brief | File | Purpose |
|-------|------|---------|
| D01 | `01_cascade_generalization.md` | Stress-test whether cascade AA lite generalizes beyond the current 26 fixtures. |
| D02 | `02_expert_v2_specialization.md` | Redesign modules so routing chooses genuinely different capabilities. |
| D03 | `03_terminal_bench_aci_and_task_triage.md` | Improve Terminal-Bench agent-computer interface and task selection before scaling. |
| D04 | `04_public_benchmark_scaling.md` | Decide how to move from local fixtures to public benchmark evidence. |
| D05 | `05_router_dataset_and_learning.md` | Build a route-outcome dataset and decide when learning is justified. |
| D06 | `06_claims_stop_rules_and_paper_strategy.md` | Govern claims, stop rules, and workshop-vs-main-track positioning. |

## Shared Subagent Output Contract

Every subagent should return:

```text
scope
inputs_read
environment_observed
method
commands_run
artifacts_created
results
interpretation
supports_direction | weak_or_inconclusive | falsified_or_blocked
recommended_followup
```

For code changes, run:

```bash
python3 -m unittest discover -s tests
```

For benchmark changes, include:

- exact task subset
- model/provider
- matched budget
- regeneration command
- where raw logs and summaries are stored

## Evidence Rules

- Local fixture success is useful but not enough for main-track claims.
- Terminal-Bench results must separate environment failure from agent failure.
- Always report raw success and cost; never report cost-normalized success alone.
- Do not claim learned routing from N=26 without held-out validation.
- Do not claim expert routing unless redundancy and specialization metrics improve.

## Recommended Dispatch Order

The owner can dispatch in any order, but the most natural sequence is:

1. D02 expert v2 specialization
2. D01 cascade generalization
3. D03 Terminal-Bench ACI triage
4. D04 public benchmark scaling
5. D05 router dataset/learning
6. D06 paper strategy

The important dependency is conceptual: routing should not be scaled until the routed modules are meaningfully different.
