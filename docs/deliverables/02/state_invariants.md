# State Invariants

## scope

This document defines invariants, validity checks, and failure/update/halt rules for the Agent-Attention state machine. It is written so an implementer can turn each invariant into a runtime assertion or log validator.

The invariants keep the state compact, auditable, metric-computable, and aligned with Subtask 01 baselines and benchmarks.

## claims

- [文献] ReAct-style trajectories and tool-use benchmarks show that action/observation logs are necessary for grounded evaluation.
- [文献] Reflexion and Voyager show that feedback can improve later behavior, but only if failures and updates are recorded with provenance.
- [原型] Atomic route and event logs make toy-runtime metrics computable without inspecting hidden prompts.
- [猜想] The most important stability invariant is that `goal` remains an immutable residual anchor while task decomposition evolves around it.

## design

### minimal version

Core invariants:

1. `goal.original` is immutable after run creation.
2. Every state update has at least one `evidence_ref`, or explicitly states `evidence_ref: none` with reason `internal_decomposition`.
3. Every route decision logs all candidate score terms: `semantic_match`, `reliability`, `historical_success`, `cost`, `latency`, `risk`, `repetition`, and `memory_bonus`.
4. Every selected module has a matching module registry entry and compatible input schema.
5. Every observation is linked to the action or module call that produced it.
6. Every memory write has `memory_type`, `write_reason`, `evidence_refs`, and an initial usefulness label of `unknown` unless immediately verified.
7. Every memory read event has `memory_usefulness_label`; use `unknown` until later evidence can mark it `useful`, `harmful`, or `neutral`.
8. Every verifier conclusion binds to `check_items` and evidence.
9. Every halt event has `halt_reason`, `success_signal`, `verification_status`, and `budget_snapshot`.
10. Every failure update names a failure signal, a blame candidate, an update target, and a rollback condition.
11. Every metric in `formal_spec.md` and `routing_equations.md` is computable from `state` or `trajectory_event`.

### enhanced version

Additional invariants for richer runtimes:

1. Composite modules must either expose child activations or emit an `opaque_cost_record`.
2. Memory reads must later receive a reuse outcome: `useful`, `harmful`, `neutral`, or `unknown`.
3. Negative-transfer labels must point to the memory read and the later regression or wrong route.
4. Learned-router decisions must log feature version, model version, policy version, and exploration mode.
5. Human review cost must be separately labeled and not folded into token cost.
6. Offline oracle regret and proxy regret must never occupy the same field.
7. A state may store compressed summaries, hashes, and evidence refs, but should not duplicate full raw transcript unless the benchmark requires it.
8. A halt gate may stop for success, budget exhaustion, user stop, unrecoverable failure, or safety/risk stop; it may not stop without a reason.

### counterexamples

- A state that overwrites the original goal after decomposition can appear successful while solving the wrong task.
- A route log that records only selected modules cannot compute regret, route entropy, or rejected-module analysis.
- A verifier result without check items cannot distinguish a real pass from a vague critique.
- A memory write labeled as useful before reuse can inflate memory metrics.
- A halt because "looks done" without success criteria and verifier status creates premature-stop ambiguity.

## interfaces

### failure signal schema

```yaml
failure_signal:
  failure_id: string
  step_id: int
  failure_type: invalid_tool | timeout | contradiction | test_failed | verifier_failed | loop_stuck | premature_halt | budget_exceeded | negative_transfer | schema_invalid | low_confidence
  severity: info | warning | blocking | fatal
  description: string
  evidence_refs: [string]
  source_event_ids: [string]
  candidate_causes: [module_id | memory_id | route_decision_id | halt_decision_id]
  status: active | mitigated | accepted_risk | resolved
```

### update record schema

```yaml
update_record:
  update_id: string
  step_id: int
  trigger_failure_ids: [string]
  update_target: router_rule | module_prompt | memory_write_policy | verifier_checklist | tool_schema | halt_threshold | task_decomposition_heuristic | none
  target_id: string | null
  textual_gradient: string
  patch_summary: string
  evidence_refs: [string]
  confidence: float
  applied: boolean
  rollback_condition: string
  expected_metric_effect: [success_rate | token_cost | latency | invalid_tool_call_ratio | repeated_action_ratio | verifier_catch_rate | negative_transfer_cases | router_regret]
```

### halt decision schema

```yaml
halt_decision:
  halt_id: string
  step_id: int
  decision: stop | continue
  halt_reason: success | budget_exhausted | unrecoverable_failure | user_stop | safety_risk | needs_more_work | verifier_required | blocked
  success_criteria_status:
    - criterion_id: string
      status: pass | fail | unknown | not_applicable
      evidence_refs: [string]
  verification_status: pass | fail | skipped | inconclusive | not_required
  blocking_uncertainties: [string]
  active_failure_signals: [string]
  budget_snapshot: budget_state
  final_success_signal: pass | fail | partial | unknown
```

### invariant check result

```yaml
invariant_check:
  check_id: string
  run_id: string
  step_id: int
  invariant_id: string
  status: pass | fail | warn
  message: string
  offending_event_ids: [string]
  repair_hint: string
```

### baseline/category/benchmark observability

The following Subtask 01 observables are guaranteed by invariants:

| Observable | Required fields |
| --- | --- |
| `tool_calls` | `trajectory_event.cost_delta.tool_calls`, `action_type` |
| `token_cost` | `cost_delta.prompt_tokens`, `cost_delta.completion_tokens`, `token_cost_estimate` |
| `invalid_calls` | `error_type`, `failure_signal.failure_type` |
| `retries` | `cost_delta.failed_retries`, repeated `action_payload_hash` |
| `loop_stuck` | `error_type == loop_stuck`, repeated action ratio |
| `verifier_catch` | `verifier_result`, following correction event |
| `memory_reuse` | `memory_ids_read`, `memory_usefulness_label` |
| `negative_transfer` | `error_type == negative_transfer`, `memory_usefulness_label == harmful` |
| `oracle_route_possible` | `route_regret.oracle_available`, `oracle_source` |

## experiments

1. `invariant_validator_smoke`: Generate valid and intentionally invalid trajectory fixtures. The validator must catch overwritten goals, missing route score terms, missing evidence refs, memory writes without reason, memory reads without usefulness labels, halt without reason, and mixed oracle/proxy regret.
2. `halt_failure_replay`: Replay tasks with forced premature halt, budget exhaustion, verifier failure, and success. Confirm halt metrics and failure updates are computed only from `halt_decision`, `verification_status`, `failure_signals`, and `trajectory_event`.
3. `memory_outcome_audit`: Inject useful, neutral, stale, and harmful memory entries. Confirm memory reuse precision and negative-transfer counts are derived from read events and later outcome labels.

## risks

- Too many invariants can make early prototyping slow. Start with core invariants 1-10 and add enhanced checks as warnings.
- Evidence refs can become ceremonial if they only point to vague summaries. Validators should require source event IDs for external claims.
- Failure blame can be wrong; update records need confidence and rollback conditions.
- Halt rules can become overly conservative and keep running after enough evidence exists.
- Strict schema checks may reject useful exploratory modules unless extension fields are allowed.

## open_questions

- Should invariant failures stop the runtime immediately or emit warnings during Phase 0?
- What minimum evidence ref is acceptable for internal reasoning updates?
- How should a runtime label a memory read as harmful when no counterfactual no-memory run exists?
- Should halt on budget exhaustion be counted as `fail`, `partial`, or a separate final outcome?
- Which invariants should be benchmark-required versus development-only?
