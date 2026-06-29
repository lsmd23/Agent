# Architecture Map

## scope

This document normalizes the Agent-Attention architecture into a single map from task input to routing, module execution, memory, verification, halt, reflection, and textual backpropagation. It reconciles Subtasks 02-06 into one implementable architecture.

## claims

| Claim | Evidence type | Current support |
| --- | --- | --- |
| The architecture is a logged recurrent state machine, not a decorative Transformer analogy. | 原型 | Subtask 02 formal model and Subtask 06 runtime expose concrete state, route, memory, verifier, halt, and reflection events. |
| Sparse activation is meaningful only when rejected candidates and score terms are logged. | 原型 | Runtime route events include candidate score terms and reject reasons. |
| Memory must affect routing through bounded `memory_bonus`, not silently override state. | 原型 | Runtime and Subtask 04 use `memory_bonus` cap `+0.20` and floor `-0.40`. |
| Verification and halt are gates with independent metrics. | 原型 | Runtime logs `verifier_result` and `halt_gate`; Subtask 07 computes verifier and halt metrics. |

## design

### minimal version

```text
Task
  -> Goal Anchor
  -> State Encoder
  -> MemoryGate
  -> Memory KV-cache
  -> Query Builder
  -> Router/Gates
       - ToolGate
       - SearchGate
       - MemoryGate
       - VerifierGate
       - HaltGate
       - SafetyGate
       - BudgetGate
  -> Module Pool
       - agent modules
       - tool modules
       - memory modules
       - skill modules
       - verifier modules
       - aggregator modules
  -> BudgetGate per selected module
  -> Module Execution
  -> Aggregator / State Update
  -> VerifierGate / Verifier
  -> HaltGate
       - stop with reason
       - continue with active uncertainty/failure
  -> Reflection
  -> Memory Write
  -> Optional Textual Backpropagation
       - failure attribution
       - local textual gradient
       - bounded update
       - replay / held-out validation
```

### normalized terminology

| Term | Main definition |
| --- | --- |
| `module` | Any routable computation unit: agent, tool, memory operation, skill, verifier, aggregator, or halt gate. |
| `agent` | A module that performs reasoning/generation or task-specific work. |
| `tool` | A module that interacts with an external environment, API, shell, search index, test runner, or file system. |
| `skill` | A reusable procedure or behavior memory that can guide future runs. |
| `memory` | Typed key-value store for knowledge, episodic trajectories, skills, behavior routes, and failure/avoid patterns. |
| `route` | A logged decision over candidate modules with score terms, gates, selected modules, and reject reasons. |
| `gate` | A cheap decision function that constrains routing, requires verification, blocks risky actions, or decides halt. |
| `verifier` | A module or gate-backed checker that validates tests, citations, consistency, risk, or success conditions. |
| `reflection` | A compact post-run summary used for memory writes; not automatically a validated update. |
| `textual gradient` | A local, evidence-bound natural-language update proposal from a failure to a specific target. |
| `trajectory` | Ordered JSON event log containing enough state, route, memory, verifier, halt, cost, and outcome data for metrics. |

### counterexamples

- If only selected modules are logged, routing cannot be audited.
- If memory writes store full transcripts, retrieval becomes noisy and may leak benchmark answers.
- If verifier decisions are merged into final answers without separate events, verifier catch and false pass rates cannot be measured.
- If halt lacks a reason and budget snapshot, premature halt and budget exhaustion become indistinguishable.

## interfaces

### state

Canonical state carries:

- `goal`: immutable original goal and success criteria.
- `task_state`: decomposition and progress.
- `working_memory`: compact current context.
- `observations`: recent module/tool/memory observations.
- `beliefs`: accepted facts with evidence.
- `uncertainties`: unresolved questions and evidence needs.
- `failure_signals`: invalid calls, contradictions, verifier failures, loop stuck, premature halt, budget exceeded, negative transfer.
- `budget`: token/tool/verifier/retry/latency/cost accounting.
- `route_history`: route decisions, selected modules, scores, outcomes.
- `verification_status`: required checks, results, and halt eligibility.

### module pool

Each module exposes:

- `id`, `parent_id`, `kind`
- `capability`
- `input_schema`, `output_schema`
- `cost`, `latency`, `risk`, `reliability`
- `history_features`

Composite modules are allowed only if they log child activations or an opaque-cost record.

### router score

```text
score_i =
  w_sem * semantic_match_i
  + w_rel * reliability_i
  + w_hist * historical_success_i
  - w_cost * normalized_cost_i
  - w_lat * normalized_latency_i
  - w_risk * risk_i
  - w_rep * repetition_i
  + w_mem * memory_bonus_i
```

Phase 0-1 default: lexical `semantic_match`; embedding and learned policies are later variants.

### runtime event map

| Concept | Subtask 06 event kind |
| --- | --- |
| run start | `start` |
| memory retrieval | `memory_retrieval`, `memory_read` |
| gate evaluation | `gates` |
| route decision | `route` |
| budget decision | `budget_gate` |
| module call | `module_execution` |
| state update | `state_update` |
| verifier | `verifier_result` |
| halt | `halt_gate` |
| reflection | `reflection` |
| memory write | `memory_write` |
| run finish | `finish` |

Known deviation: Phase 0 uses a legacy `kind/payload` event list rather than the full target benchmark envelope.

## experiments

1. `architecture_event_coverage`
   - Validate that a run contains at least one route, gate, module execution, halt, reflection, and finish event, and memory/verifier events when enabled.

2. `module_boundary_ablation`
   - Compare atomic logging versus opaque composite workflow logging on the same task.
   - Measure metric computability, cost attribution, and error taxonomy confidence.

## risks

- Single-file runtime extension can become too complex if future phases add real tools.
- Opaque composite workflows can hide cost and failure attribution.
- Lexical routing can under-route paraphrased tasks.
- Memory and textual-backprop updates can silently become global unless bounded and audited.

## open_questions

- Should Phase 1 patch runtime output into the target envelope before any baseline result table?
- Should `failure_memory` become a first-class schema enum or remain `behavior_kv` with failure write reasons?
- Should update lifecycle move into the core `updateRecord` schema before Phase 3?
