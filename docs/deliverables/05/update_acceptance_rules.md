# Update Acceptance Rules

## scope

This document defines how textual updates move from proposal to `accept`, `reject`, `quarantine`, or `rollback`. It applies to router rules, module prompts, memory write/usefulness policy, verifier checklists, tool schemas, halt thresholds, budget policy, and task decomposition heuristics. It aligns with Subtask 02 `failureSignal`, `updateRecord`, `trajectoryEvent`, and `verificationStatus`.

## claims

- [文献] Reflexion-style verbal learning can improve future trials, but the literature also shows reflection and memory can amplify wrong diagnoses when feedback is noisy.
- [原型] Subtask 02 exposes the fields needed to gate updates: evidence refs, confidence, expected metric effects, verifier status, cost, repeated actions, memory usefulness, and negative-transfer labels.
- [猜想] A three-way decision policy is safer than binary apply/discard because quarantine preserves promising but under-validated updates for later evidence.
- [实验] Replay plus held-out validation can distinguish local improvement from overfit repair and detect negative transfer.

## design

### minimal version

Every proposed update starts as `applied=false` in the Subtask 02 `updateRecord`. A separate Subtask 05 lifecycle envelope assigns the decision:

| Decision | Criteria |
| --- | --- |
| `accept` | Schema valid; evidence refs present; target is allowed; replay improves at least one declared metric; no required regression guard fails; verificationStatus is `pass` or `not_required`. |
| `reject` | Missing evidence; target too broad; replay does not improve declared metric; update violates schema; update creates a worse primary outcome; rollback condition is absent. |
| `quarantine` | Evidence is plausible but incomplete; replay improves but held-out is missing; confidence is medium; target affects shared modules; regression guard warns but does not fail. |
| `rollback` | Previously accepted update meets its rollback condition in later runs. |

Minimum numeric gates for Phase 0-1:

```yaml
accept:
  confidence_min: 0.70
  replay_primary_metric_delta_min: 0.01
  regression_guard_max_relative_drop: 0.00
  required_evidence_event_ids_min: 1
  required_validation_modes: [failure_replay]
quarantine:
  confidence_min: 0.45
  confidence_max_exclusive: 0.70
  allowed_validation_modes: [failure_replay, held_out]
reject:
  confidence_below: 0.45
rollback:
  observed_regression_rate_min: 0.05
  repeated_failure_reappears_min: 2
```

The gates are deliberately conservative defaults, not claims about optimal thresholds.

### enhanced version

Enhanced acceptance uses target-specific guards:

| Target | Extra acceptance guard | Rollback trigger |
| --- | --- | --- |
| `router_rule` | Reduces router regret or repeated wrong route on replay. | Increased proxy/oracle regret or route-switch instability on held-out tasks. |
| `module_prompt` | Improves module-local failure without increasing invalid calls. | Invalid tool/schema failures rise for the module target. |
| `memory_write_policy` | Reduces harmful writes or stale reuse. | Useful memory reuse drops or negative-transfer cases rise. |
| `memory_usefulness` | Supported by verifier/outcome label or no-memory counterfactual. | Later harmful label for same memory/task signature. |
| `verifier_checklist` | Increases verifier catch rate without large false alarms. | False-positive verifier blocks increase cost or premature failure. |
| `tool_schema` | Reduces invalid tool calls without lowering successful tool calls. | Valid tool calls become rejected or schema-invalid events rise. |
| `halt_threshold` | Reduces premature halt or loop-stuck rate. | Budget exhaustion or overlong loops increase. |
| `budget_policy` | Improves cost-normalized success. | Success drops under same budget or verifier-required halt is skipped. |
| `task_decomposition_heuristic` | Improves task progress and lowers repeated subgoal churn. | More decomposition steps without success/cost gain. |

Acceptance score:

```text
accept_score =
  0.25 * evidence_quality
  + 0.20 * replay_improvement
  + 0.20 * held_out_stability
  + 0.15 * attribution_confidence
  + 0.10 * locality_score
  + 0.10 * rollback_clarity
```

Recommended decision:

```text
accept if accept_score >= 0.75 and all hard guards pass
quarantine if 0.50 <= accept_score < 0.75 or held_out_stability is unknown
reject if accept_score < 0.50 or any hard guard fails
```

### counterexamples

- A replay-only fix that succeeds by memorizing the failed answer should be quarantined or rejected if held-out tasks regress.
- A verifier checklist that catches one failure but blocks many correct runs should be rolled back despite higher verifier catch rate.
- A memory blacklist created from one ambiguous harmful read can reduce useful transfer; it needs either counterfactual evidence or quarantine.
- A tool schema change that narrows allowed arguments may reduce invalid calls while also blocking valid rare arguments; held-out schema fixtures are required.

## interfaces

`textualUpdateEnvelope` lifecycle:

```yaml
envelope_id: string
update_record_patch: updateRecord
decision: accept | reject | quarantine | rollback
decision_reason: string
validation_refs: [string]
accepted_at_event_id: string | null
quarantine_reason: string | null
rollback_record: rollbackRecord | null
audit_status: complete | missing_replay | missing_held_out | missing_evidence | schema_conflict
```

`updateRecord.applied` meaning:

| Envelope decision | `updateRecord.applied` |
| --- | --- |
| `accept` | `true` after the update is installed for future runs. |
| `reject` | `false`. |
| `quarantine` | `false` for production routing; may be `true` only inside isolated validation. |
| `rollback` | `false` after rollback event completes. |

Required `trajectoryEvent` records:

- Proposal: `event_type=failure_update`, `action_type=no_op`, `success_signal=unknown`.
- Validation replay: route/module/verifier/halt events for before and after runs.
- Acceptance: `event_type=failure_update`, `observation_summary` includes lifecycle decision.
- Rollback: `event_type=failure_update`, `correction_of_event_ids` points to the accepted update and the regression events.

Required `verificationStatus`:

- `accept` requires `pass` or `not_required`.
- `quarantine` allows `inconclusive`.
- `reject` records `fail`, `inconclusive`, or missing validation.
- `rollback` records the validation or monitoring checks that tripped the rollback condition.

## experiments

1. `accept_reject_quarantine_fixture`: Create proposed updates with known evidence quality and validation outcomes. Metrics: decision accuracy, false accept rate, false reject rate, quarantine rate, schema conflict count.
2. `rollback_monitoring_replay`: Accept updates, then replay future trajectories with injected regressions. Metrics: rollback precision, rollback latency in steps, regression rate after rollback, repeated failure reduction.
3. `target_guard_ablation`: Disable one target-specific guard at a time. Metrics: negative transfer cases, invalid tool call ratio, verifier false-positive rate, loop-stuck rate, cost-normalized success.

## risks

- Conservative thresholds may reject useful updates early in Phase 0.
- Quarantine can become a graveyard if no process promotes or rejects queued updates.
- Validation tasks can leak the failed trajectory if replay is not separated from held-out probes.
- Locality can be misestimated for shared prompts, shared memory policies, and broad router rules.
- Rollback conditions that are too sensitive can oscillate updates on and off.

## open_questions

- Should accepted updates require held-out validation immediately, or is replay plus quarantine promotion enough for Phase 0?
- How large should the held-out set be for shared module prompts compared with narrow router rules?
- Should rollback remove the update entirely or demote it to quarantine for later re-evaluation?
- Should accept/reject/quarantine be added to the core Subtask 02 `updateRecord`, or remain a Subtask 05 lifecycle envelope?
