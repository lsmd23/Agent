# Failure Replay Protocol

## scope

This document defines replay and held-out validation for textual backpropagation updates. It ensures every proposed update is tested against the failed trajectory evidence and at least one counterfactual or held-out condition before acceptance when feasible.

The protocol is log-first: all metrics must be computable from Subtask 02 `trajectoryEvent`, `failureSignal`, `updateRecord`, route decisions, memory labels, and `verificationStatus`.

## claims

- [文献] Routing and agent benchmarks motivate process metrics beyond final success, including cost, invalid calls, repeated actions, verifier catch, memory reuse, and regret.
- [原型] Subtask 02 requires enough event-level fields to replay route choices, module calls, memory use, verifier checks, and halt decisions in a toy deterministic runtime.
- [猜想] Failure replay is necessary but insufficient; held-out validation is needed to detect overfit updates and negative transfer.
- [实验] Local-vs-global and replay-vs-held-out controls can expose whether textual backpropagation is doing causal repair or just writing a better post-hoc explanation.

## design

### minimal version

For each update proposal, run:

1. `before_replay`: replay the failed trajectory with the pre-update policy/configuration.
2. `after_replay`: replay the same task with exactly one proposed update enabled.
3. `no_update_control`: replay without the update when stochastic components or external tools make outcomes non-deterministic.
4. `regression_guard`: run at least one held-out or fixture task that exercises the same target without sharing the failed answer.

Required replay metrics:

```yaml
primary:
  success_signal: pass | fail | partial | unknown
  verification_status: pass | fail | skipped | inconclusive | not_required
process:
  token_cost: number
  latency_ms: number
  tool_calls: integer
  verifier_calls: integer
  invalid_tool_call_ratio: number
  repeated_action_ratio: number
  loop_stuck: boolean
  premature_halt: boolean
  negative_transfer_cases: integer
routing:
  selected_modules: [string]
  route_entropy: number
  router_regret_or_proxy_regret: number | null
memory:
  memory_reads: integer
  useful_memory_reads: integer
  harmful_memory_reads: integer
```

Acceptance requires the after replay to improve the declared expected metric and avoid all hard regression guards in `update_acceptance_rules.md`.

### enhanced version

Use a four-cell validation matrix:

| Cell | Purpose |
| --- | --- |
| Failed task, no update | Confirms the failure is reproducible or identifies nondeterminism. |
| Failed task, local update | Measures direct repair. |
| Held-out related tasks, local update | Detects local generalization and negative transfer. |
| Failed and held-out tasks, global rewrite control | Measures whether broad prompt rewriting gives brittle gains. |

Target-specific replay fixtures:

| Target | Fixture |
| --- | --- |
| `router_rule` | Same query with competing modules and known oracle/proxy best route. |
| `module_prompt` | Same module with valid and invalid argument cases. |
| `memory_write_policy` | Useful, stale, contradictory, and irrelevant memory entries. |
| `memory_usefulness` | No-memory counterfactual plus harmful-memory replay. |
| `verifier_checklist` | Positive and negative examples for the new checklist item. |
| `tool_schema` | Valid boundary arguments and invalid malformed arguments. |
| `halt_threshold` | Success, premature halt, loop-stuck, and budget-exhausted traces. |
| `budget_policy` | Same task under matched success and constrained budgets. |
| `task_decomposition_heuristic` | Tasks requiring one-step, multi-step, and no decomposition. |

Replay isolation rules:

- Enable exactly one proposed update per after replay unless explicitly testing update interactions.
- Keep model, tool, memory corpus, benchmark split, and budget constant across before/after cells.
- Do not write replay memories into production memory unless the replay is explicitly marked as a benchmark run.
- Log stochastic seed or nondeterminism marker when exact replay is impossible.
- Treat verifier result as evidence, not truth; executable benchmark outcomes outrank self-verifier outcomes when available.

### counterexamples

- A failed trajectory replay that includes the answer in memory is not a fair validation of a memory or module prompt update.
- An after replay with higher success and doubled cost may fail acceptance if the expected effect was cost reduction.
- A router update that fixes one task by always selecting a strong expensive module can regress cost-normalized success.
- A held-out suite with only easy unrelated tasks cannot detect negative transfer for the updated target.

## interfaces

`validationRun`:

```yaml
validation_id: string
update_id: string
mode: failure_replay | held_out | counterfactual_no_update | global_rewrite_control
task_ids: [string]
policy_version_before: string
policy_version_after: string
enabled_update_ids: [string]
disabled_update_ids: [string]
before_event_ids: [trajectoryEvent.event_id]
after_event_ids: [trajectoryEvent.event_id]
before_metrics:
  success_rate: number
  token_cost: number
  latency: number
  invalid_tool_call_ratio: number
  repeated_action_ratio: number
  verifier_catch_rate: number
  negative_transfer_cases: number
  router_regret: number | null
after_metrics:
  success_rate: number
  token_cost: number
  latency: number
  invalid_tool_call_ratio: number
  repeated_action_ratio: number
  verifier_catch_rate: number
  negative_transfer_cases: number
  router_regret: number | null
regression_checks:
  - metric: string
    status: pass | fail | warn
    threshold: number
    observed_delta: number
verification_status_after: verificationStatus
decision_recommendation: accept | reject | quarantine
```

Metric formulas from logs:

| Metric | Formula |
| --- | --- |
| `success_rate` | Mean final `halt_decision.final_success_signal == pass` or task-level final `trajectoryEvent.success_signal == pass`. |
| `token_cost` | Sum `trajectoryEvent.cost_delta.token_cost_estimate`. |
| `latency` | Sum or mean `trajectoryEvent.latency_ms`, reported consistently. |
| `invalid_tool_call_ratio` | Count `error_type == invalid_tool` divided by tool calls. |
| `repeated_action_ratio` | Duplicate `action_payload_hash` within task divided by action events. |
| `verifier_catch_rate` | Verifier failures followed by successful correction divided by verifier failures. |
| `negative_transfer_cases` | Count harmful memory labels or `error_type == negative_transfer`. |
| `router_regret` | Use oracle regret when available; otherwise proxy regret only, never mixed. |
| `rollback_frequency` | Rolled back accepted updates divided by accepted updates. |
| `false_blame_rate` | Unsupported primary blame candidates divided by tested primary blame candidates. |

Every validation run must link to the `updateRecord.update_id`, the attribution evidence events, and the replay trajectory events used to compute metrics.

## experiments

1. `failure_replay_local_update`: On at least 20 failed code/search trajectories, compare no update, local update, and reflection-only memory. Metrics: replay improvement, repeated failure reduction, token cost delta, invalid tool call ratio, verifier catch rate.
2. `held_out_negative_transfer_probe`: Inject useful, stale, irrelevant, and harmful memories or route rules, then validate proposed updates on related held-out tasks. Metrics: negative transfer cases, useful memory reuse rate, regression rate, rollback frequency.
3. `local_vs_global_rewrite`: Compare local target updates against broad prompt rewrites under equal budgets. Metrics: success, cost-normalized success, held-out regression rate, false blame rate, route entropy.

## risks

- Replay may be nondeterministic when external tools, model sampling, or changing web/search content are involved.
- Held-out tasks can be too small to catch broad regressions from shared prompt or router updates.
- Exact trajectory replay can overfit to the original action order instead of validating a better policy.
- Metrics can be gamed if the update reduces cost by halting early with `partial` or `unknown` success.
- Global rewrite controls can contaminate conclusions if they are given more scope than local updates.

## open_questions

- What is the minimum held-out suite size per update target for Phase 0?
- Should replay use exact action forcing, policy re-execution from the same initial state, or both?
- How should nondeterministic external search or web observations be snapshotted for reproducible replay?
- Should replay-generated memories be discarded by default or kept with a `benchmark_replay` provenance label?
