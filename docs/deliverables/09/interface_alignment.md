# Interface Alignment

## scope

This document reconciles interfaces across Subtasks 01-08 and records the main schema decisions, deviations, and remaining conflicts. It is the handoff contract for the next implementation and experiment phase.

## claims

| Claim | Evidence type | Current support |
| --- | --- | --- |
| The research artifacts share a workable core schema. | 原型 | Subtasks 02-08 all reference state, module, route, memory, trajectory, failure, update, halt, task, metric, baseline, and ablation records. |
| Current runtime logs are scoreable but not yet full target envelopes. | 实验 | Subtask 07 scorer handles 5 legacy trajectories and records deviations. |
| Most interface conflicts can be resolved without changing Subtask 02 before Phase 1. | 原型 | Decision log defines compatibility cuts for `repetition`, `failure_memory`, `memory_bonus`, update lifecycle, and budget policy. |

## design

### minimal version

Accepted interface cuts:

| Topic | Main definition | Source / decision |
| --- | --- | --- |
| Routing unit | Atomic modules by default; composite workflows allowed with child events or opaque-cost record. | `Formal Model Defaults After Literature Map` |
| Memory kinds | `knowledge_memory`, `episodic_memory`, `skill_memory`, `behavior_kv`; `failure_memory` encoded as `behavior_kv` profile for Phase 0. | `Runtime Prototype Interface Cut` |
| Router default | Heuristic/lexical router is valid for Phase 0-1; learned routing is Phase 4. | Subtasks 02-03 |
| Semantic match | Phase 0-1 lexical. Embedding is enhanced/future ablation. | `Wave 2 Interface Defaults` |
| Repetition key | Serialized route score term is `repetition`; `repetition_penalty` is a human-readable alias only. | `Runtime Prototype Interface Cut` |
| Search gate | Separate from ToolGate. | `Runtime Prototype Interface Cut` |
| Memory bonus | Cap `+0.20`, floor `-0.40`. | `Runtime Prototype Interface Cut` |
| Textual update lifecycle | `accept/reject/quarantine/rollback` remains in Subtask 05 envelope for now. | `Runtime Prototype Interface Cut` |
| Budget policy update | Compile to `router_rule` or `halt_threshold` until schema revision. | `Runtime Prototype Interface Cut` |
| Phase 0 suite | code/search canonical; web optional stretch. | `Wave 2 Interface Defaults` |
| Phase 0 invariants | Warning/validation events now; hard failures for benchmark-required fields later. | `Wave 2 Interface Defaults` |

### enhanced version

Before Phase 1 result claims, consider adding a normalizer or runtime patch that wraps legacy trajectories into the target envelope:

```yaml
schema_version: agent_attention.benchmark_trajectory.v0.1
run_id: string
task_id: string
benchmark_id: string
baseline_id: string
runtime_config: object
events: [trajectory_event]
final_success_label: pass | fail | partial | unknown
failure_reason: string | null
metrics_summary: object
known_deviations: [string]
```

### counterexamples

- Treating legacy scalar activation cost as real API/token cost would invalidate cost comparisons.
- Treating proxy regret as oracle regret would overstate routing evidence.
- Adding `failure_memory` as a fifth enum in one document but not in runtime would break scoring.
- Filling missing `task_id` by guessing from the final answer would pollute benchmark joins.

## interfaces

### state schema alignment

| Field | Formal spec | Runtime status | Gap |
| --- | --- | --- | --- |
| `goal` | Immutable residual anchor | Implemented as `goal` string | Target envelope should add goal hash and success criteria. |
| `task_state` | Decomposition/progress | Partly implicit in observations/hypotheses | Needs explicit target envelope for Phase 1. |
| `working_memory` | Compact summary | Observations/hypotheses lists | Needs normalized summary field. |
| `failure_signals` | Typed records | String list plus event payloads | Should normalize to typed `failureSignal`. |
| `budget` | Full cost accounting | Toy scalar budget/cost | Needs `cost_delta` expansion. |
| `route_history` | Route refs | Route events present | Needs run/task IDs for joins. |
| `verification_status` | Required checks/results | `verifier_status`, `verifier_required` | Needs checklist and correction refs. |

### route schema alignment

Runtime route events include:

- `decision_id`
- `routing_policy`
- `top_k`
- `query`
- `selected_modules`
- `candidates`
- `route_scores`
- `budget_snapshot`

Candidate score terms include:

- `semantic_match`
- `reliability`
- `historical_success`
- `cost`
- `latency`
- `risk`
- `repetition`
- `memory_bonus`

Open gap: oracle/proxy route regret is absent in legacy trajectories.

### memory schema alignment

Runtime memory read/write records include:

- key/value summary
- `memory_type`
- usefulness label
- route signature
- evidence refs
- negative-transfer count
- bounded `memory_bonus`
- write reason

Open gaps:

- no online usefulness update after later outcomes
- `failure_memory` is an operational profile, not schema enum
- no persistent quarantine promotion lifecycle yet

### textual update alignment

Subtask 05 defines:

- attribution case
- textual gradient
- proposed update
- lifecycle envelope
- replay/held-out validation

Runtime status:

- reflection and memory write are implemented
- failure attribution/update lifecycle is not implemented

Open gaps:

- update lifecycle not in core `updateRecord`
- budget policy not a first-class update target
- replay snapshots for nondeterministic search are not implemented

### task / trajectory / metrics alignment

Subtask 07 defines task and trajectory schemas plus scorer. Current scoring supports:

- target envelopes
- legacy Subtask 06 event lists

Known deviations that must remain visible:

- `legacy_06_event_list_no_top_level_run_metadata`
- `legacy_06_uses_scalar_activation_cost_not_full_cost_delta`
- `legacy_06_lacks_task_schema_join`
- `legacy_06_lacks_oracle_route_regret`
- `oracle_route_regret_unavailable`
- `proxy_route_regret_unavailable`

### baseline / ablation alignment

Subtask 08 defines:

- six baseline families
- single-variable ablation matrix
- result table fields matching Subtask 07 scorer
- error taxonomy

Open gap: `full_history_agent` and `moa_style_agent` are not yet required keys in the Subtask 07 task schema's `baseline_applicability`.

## experiments

1. `trajectory_normalizer_check`
   - Wrap all current legacy trajectories into target envelopes with external manifest metadata.
   - Run `scoring_script.py` and confirm metrics match legacy scoring.

2. `schema_gap_patch_check`
   - Add `task_id`, `benchmark_id`, `baseline_id`, and `cost_delta` to one runtime trajectory.
   - Compare known deviations before/after.

## risks

- Schema drift can hide in Markdown if runtime output is not validated.
- Baseline fairness depends on fields not yet emitted by all systems.
- Memory and textual-update lifecycles are designed but not implemented.
- Without target envelopes, Phase 1 results will require external manifests.

## open_questions

- Should target envelope emission be a required patch before running Phase 1 baselines?
- Should Subtask 07 schema add `full_history_agent` and `moa_style_agent` to `baseline_applicability`?
- Should `failure_memory` and update lifecycle be promoted into Subtask 02 before Phase 3?
