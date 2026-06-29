# Textual Gradient Policy

## scope

This document defines how a failed Agent-Attention run is converted into a local textual gradient and a bounded proposed update. It is limited to Subtask 05 design material and only targets artifacts under `docs/deliverables/05/`.

The policy consumes Subtask 02 `failureSignal`, `trajectoryEvent`, `verificationStatus`, route history, memory read/write events, and halt decisions. It emits an attribution case plus an `updateRecord`-compatible patch. It does not modify the core Subtask 02 schemas.

## claims

- [文献] Reflexion, Voyager, Self-Refine, and LATS support using natural-language feedback after failures, but the project needs stricter provenance than ordinary reflective summaries.
- [原型] Subtask 02 already requires event-level evidence, candidate route scores, failure signals, verifier results, and update records; textual gradients can therefore be audited without reading hidden prompts.
- [猜想] Local textual gradients reduce repeated failures more safely than global prompt rewrites because they bind a symptom to a component, an update target, and a rollback condition.
- [实验] The replay and held-out protocols in this deliverable make improvement, false blame, regression, and negative transfer measurable from trajectory logs.

## design

### minimal version

For each final failure, generate exactly one primary textual gradient and optionally secondary candidates. The primary record must include:

```yaml
failure_id: string
symptom: string
root_cause_hypothesis: string
blamed_component: router | memory | module | aggregator | verifier | halt
evidence_event_ids: [trajectory_event.event_id]
local_gradient: string
proposed_update:
  target: router_rule | module_prompt | memory_write_policy | verifier_checklist | tool_schema | halt_threshold | task_decomposition_heuristic
  target_id: string
  before: string
  after: string
expected_effect: string
rollback_condition: string
```

The gradient should read as a local derivative: "Given this failure evidence, change only this target in this direction." A valid gradient names the decision boundary that should move, not just the desired future behavior.

Component-specific gradient templates:

| Blamed component | Symptom examples | Valid local gradient |
| --- | --- | --- |
| `router` | selected wrong module, repeated module, ignored cost | Increase/decrease a route score term or add a narrow suppression rule for a task signature. |
| `memory` | stale retrieval, harmful reuse, bad write | Lower usefulness, blacklist for a task family, or tighten write/retrieval policy. |
| `module` | bad tool args, schema mismatch, incomplete answer | Add a targeted prompt instruction or argument checklist for one module. |
| `aggregator` | lost evidence, merged contradiction, over-compressed | Add a merge rule requiring evidence refs or contradiction preservation. |
| `verifier` | missed failure, false alarm, incomplete checklist | Add or narrow one checklist item tied to observed evidence. |
| `halt` | premature stop, endless loop, budget exhaustion | Adjust halt threshold or required verification condition for the failure class. |

### enhanced version

Enhanced textual backpropagation ranks multiple blame candidates before choosing an update:

```text
blame_score =
  0.35 * causal_link_score
  + 0.20 * temporal_proximity_score
  + 0.20 * counterfactual_plausibility_score
  + 0.15 * verifier_agreement_score
  + 0.10 * recurrence_score
```

Candidate generation rules:

- Include the last failing module, but never select it solely by temporal proximity.
- Include router candidates when route scores show a high-scoring rejected module that later evidence suggests was needed.
- Include memory candidates when a harmful or stale memory read precedes the wrong route, wrong claim, or failed halt.
- Include verifier candidates when a later failure was visible in earlier evidence but marked `pass` or `skipped`.
- Include halt candidates when a halt event happened with active failure signals, blocking uncertainties, or missing required verification.

Allowed update targets include the Subtask 02 targets plus two Subtask 05 extension targets:

| Target | 02 compatibility |
| --- | --- |
| `router_rule` | Native `updateRecord.update_target`. |
| `module_prompt` | Native. |
| `memory_write_policy` | Native. |
| `memory_usefulness` | Compile to `memory_write_policy` unless 02 later adds this target. |
| `verifier_checklist` | Native. |
| `tool_schema` | Native. |
| `halt_threshold` | Native. |
| `budget_policy` | Compile to `router_rule` or `halt_threshold` unless 02 later adds this target. |
| `task_decomposition_heuristic` | Native. |

### counterexamples

- "The agent should reason better" is not a textual gradient because it has no blamed component, no target, and no measurable decision boundary.
- "Always call the expensive verifier before answering" is too broad unless repeated high-risk failures justify the cost and the update is scoped to a task family.
- "The verifier passed, so the module must be correct" is invalid because verifier conclusions are evidence, not ground truth.
- "The final answer was wrong, so rewrite the system prompt" is a global rewrite and should be used only as a quarantined control.

## interfaces

The textual gradient pipeline is:

```text
failureSignal
  + trajectoryEvent evidence refs
  + verificationStatus
  -> attributionCase
  -> updateRecord-compatible patch
  -> failure_update trajectoryEvent
  -> validationRun
  -> accept | reject | quarantine | rollback
```

`attributionCase` fields:

```yaml
case_id: string
failure_id: string
trigger_failure_ids: [string]
symptom: string
root_cause_hypothesis: string
blamed_component: router | memory | module | aggregator | verifier | halt
blame_candidates:
  - candidate_id: string
    component_type: router | memory | module | aggregator | verifier | halt
    component_id: string
    hypothesis: string
    causal_link_score: float
    temporal_proximity_score: float
    counterfactual_plausibility_score: float
    evidence_event_ids: [string]
    evidence_refs: [evidenceRef]
    label: primary | secondary | ruled_out | unknown
evidence_event_ids: [string]
evidence_refs: [evidenceRef]
local_gradient: string
proposed_update: proposedUpdate
rollback_condition: string
confidence: float
```

`updateRecord` mapping:

| Textual field | Subtask 02 field |
| --- | --- |
| `trigger_failure_ids` | `updateRecord.trigger_failure_ids` |
| `proposed_update.target` | `updateRecord.update_target` after compatibility mapping |
| `proposed_update.target_id` | `updateRecord.target_id` |
| `local_gradient` | `updateRecord.textual_gradient` |
| `before/after/bounded_scope` | `updateRecord.patch_summary` |
| `evidence_refs` | `updateRecord.evidence_refs` |
| `confidence` | `updateRecord.confidence` |
| initial lifecycle status | `updateRecord.applied=false` until accepted |
| `rollback_condition` | `updateRecord.rollback_condition` |
| `expected_effect` | `updateRecord.expected_metric_effect` |

Every proposed update must also emit a `trajectoryEvent` with `event_type=failure_update`, `action_type=no_op`, `correction_of_event_ids` set to the blamed evidence events, and `evidence_refs` pointing to the trajectory evidence used for attribution.

## experiments

1. `textual_gradient_compilation`: Take 30 failed synthetic code/search trajectories and compile each textual gradient to an `updateRecord` patch. Compare against reflection-only summaries. Metrics: compile success rate, evidence coverage, target specificity, invalid target count, missing rollback count.
2. `component_blame_ablation`: For failures with known injected causes, compare last-module blame, heuristic blame score, and verifier-only blame. Metrics: attribution accuracy, false blame rate, replay improvement, regression rate.
3. `local_vs_global_gradient_control`: Compare no update, local update, and global prompt rewrite on the same failed replay plus held-out tasks. Metrics: after-update success, token cost, repeated action ratio, negative transfer cases, rollback frequency.

All metrics must be computed from `failureSignal`, `trajectoryEvent`, `updateRecord`, validation results, and optional benchmark oracle labels.

## risks

- False blame can produce a neat but harmful update when the trajectory lacks decisive counterfactual evidence.
- Textual gradients may overfit one failure if accepted from replay alone.
- Shared module prompts can make a nominally local update behave globally.
- Memory usefulness updates are especially prone to negative transfer when semantic similarity masks causal irrelevance.
- Global prompt rewrite controls may look attractive on replay but hide held-out regressions.

## open_questions

- Should `memory_usefulness` become a first-class Subtask 02 `update_target`, or remain compiled through `memory_write_policy`?
- Should `budget_policy` become a first-class Subtask 02 target, or be represented through router and halt updates?
- What minimum number of repeated failures is required before updating a shared module prompt?
- Should ambiguous blame require human review, or is quarantine plus held-out validation enough for Phase 0-1?
