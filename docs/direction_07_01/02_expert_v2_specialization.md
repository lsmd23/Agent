# D02: Expert V2 Specialization Brief

## Objective

Redesign Agent-Attention modules so routing selects genuinely different capabilities, not redundant prompt personas.

## Why This Matters

Sparse routing cannot win if all routed modules are near-identical. The previous specialization audit found 96% redundant activation and almost no unique rescue cases.

## Required Inputs

- `docs/next_iteration/research_directions/07_expert_redesign_proposal.md`
- `experiments/analysis/expert_specialization_audit.md`
- `experiments/real_benchmarks/faithful_llm_runners.py`
- `experiments/real_benchmarks/llm_executors.py`
- `src/agent_attention_runtime.py`
- current code-suite task manifests

## Proposed Expert V2 Set

| Module | Role | Distinct Capability |
|--------|------|---------------------|
| `patch_author` | write minimal Python patch | default code repair specialist |
| `repo_navigator` | inspect multi-file structure | import/API/config/multi-file bugs |
| `test_runner` | run or simulate tests and structure failure | verifier/tool-bound specialist |
| `shell_agent` | execute terminal commands | Terminal-Bench tasks only |
| `aggregator` | merge conflicting proposals | expensive rescue only |

Retire generic parallel proposers unless they show measurable unique value.

## Research Questions

1. Do specialist outputs differ meaningfully?
2. Does any specialist produce unique rescues?
3. Can the cascade route to specialists only when needed?
4. Does specialization reduce redundant activation below 50%?

## Suggested Experiments

### Experiment A: Patch Fingerprint Disagreement

Compare outputs across specialists by:

- touched files
- changed functions
- patch hash/fingerprint
- final pytest outcome

Target:

- disagreement rate > 40%
- redundant activation < 50%

### Experiment B: Unique Rescue Audit

For each task, identify if only one specialist succeeds.

Target:

- at least 3 unique sole-module rescues on the 26-task suite or expanded suite.

### Experiment C: Specialist-Gated Cascade

Replace AA lite escalation with targeted specialist routing:

```text
ReAct -> route to patch_author/repo_navigator/test_runner -> optional aggregator
```

Compare against current `cascade_react_aa_lite_llm`.

## Acceptance Criteria

`supports_direction` if:

- redundancy drops below 50%;
- specialists show unique rescue behavior;
- cascade cost-quality is maintained or improved.

`weak_or_inconclusive` if:

- outputs differ but end-task outcomes do not;
- specialization helps only one task.

`falsified_or_blocked` if:

- specialists remain redundant;
- added modules increase cost without rescue value.

## Deliverables

- `docs/direction_07_01/reports/D02_expert_v2_specialization.md`
- specialization metrics JSON
- updated module registry or design patch, if implemented
- recommendation: keep, revise, or abandon each specialist

## Guardrails

- Do not add persona-only experts.
- Do not route verifier as a normal proposer; keep it as a gate or tool-bound checker.
- Do not evaluate Terminal-Bench routing until `shell_agent` behavior is separately audited.
