# Metrics Definitions

## scope

This document defines metrics for Agent-Attention benchmark runs. Every metric is computable from `task_schema.json`, `trajectory_schema.json`, or the Subtask 06 legacy `kind/payload` trajectory envelope. Metrics are grouped into final, process, routing, memory, verifier, and fairness/cost views.

The definitions separate "correct but expensive" from "wrong but cheap" by always reporting success and cost jointly. They also expose negative transfer, premature halt, budget exhaustion, verifier catch, memory reuse, and route score/cost behavior.

## claims

- [文献] Routing and agent benchmark literature supports cost-quality, regret, route-selection, and trajectory-process metrics in addition to final task accuracy.
- [原型] Subtask 06 logs enough route, memory, verifier, budget, and halt events to compute a useful Phase 0 subset.
- [实验] Baseline and ablation comparisons are fair only when metrics are computed from the same trajectory fields under matched task and budget records.
- [猜想] Process metrics will reveal early architectural value or failure before final success moves on small toy suites.

## design

### minimal version

Required Phase 0 metrics:

| Metric | Formula | Primary fields | Legacy 06 path |
| --- | --- | --- | --- |
| `task_success` | `final_success_label == pass` | envelope final label or final halt success | last `halt_gate.payload.success_signal` |
| `success_rate` | mean `task_success` over runs | run summaries | same |
| `activation_cost` | sum module/tool/verifier cost deltas | `events[].cost_delta` | sum allowed `budget_gate.payload.module_cost` |
| `cost_normalized_success` | `task_success / (1 + activation_cost)` | success plus cost | same |
| `module_calls` | count selected/allowed module activations | module call events | allowed `budget_gate` decisions or `finish.selected_modules` |
| `verifier_calls` | count verifier activations | verifier cost/events | allowed `budget_gate.module_id == verifier` |
| `budget_exhaustion` | final halt reason or failure signal indicates budget exhaustion | halt/failure events | `halt_gate.reason == budget_exhausted` or verifier budget rejection |
| `step_exhaustion` | run reaches step limit without terminal success/failure halt | runtime config and finish reason | final answer reason `max_steps_reached` after last halt continued |
| `repeated_action_ratio` | duplicate action/module activations divided by activations | action hashes or module IDs | duplicates in allowed module IDs |
| `loop_stuck` | loop-stuck error or repeated ratio above threshold | error/failure events | `halt_gate.reason == loop_stuck` or repeated ratio > 0.6 |
| `premature_halt` | run stops without pass while budget remains or halt reason is success despite failed oracle | halt plus oracle | inferred from final halt/finish and remaining budget |
| `invalid_tool_call_ratio` | invalid tool failures divided by tool calls | `error_type`, failure signals, tool call count | failure strings containing `invalid_tool` or `wrong_module` over tool-like calls |
| `route_entropy` | entropy of activated module distribution | selected modules | selected modules from route/budget/finish |
| `selected_route_score_mean` | mean score of selected candidates | route candidates | `route.payload.candidates[].score` |
| `selected_route_cost_mean` | mean `score_terms.cost` for selected candidates | route candidates | same |
| `route_reject_rate` | rejected candidates divided by total candidates | route candidates | candidate `reject_reason != null` |
| `oracle_route_regret` | mean selected regret versus oracle | route oracle fields | unavailable unless target schema provides it |
| `proxy_route_regret` | separately labeled proxy regret | route oracle proxy fields | unavailable unless target schema provides it |
| `memory_reads` | count memory read events | memory events | `kind == memory_read` |
| `useful_memory_reuse_rate` | useful reads divided by labeled reads | memory usefulness labels | `memory_read.payload.usefulness_label` |
| `negative_transfer_cases` | harmful memory or negative-transfer failures | memory/failure fields | harmful labels, `negative_transfer_count`, failure strings |
| `verifier_catch_rate` | verifier failures followed by correction and final pass divided by verifier failures | verifier/failure/correction events | `verifier_result.status == fail` followed by final pass |

### enhanced version

Enhanced Phase 1 metrics add:

- `test_pass_rate`: executable code tasks passing all listed tests divided by code task runs.
- `answer_correctness`: exact/rubric answer correctness for search and mini-research tasks.
- `citation_correctness`: supported citations divided by required citations, with source freshness flags.
- `human_preference_score`: calibrated human rating, reported separately from automatic success.
- `retrieval_precision`: useful reads divided by useful plus harmful plus neutral reads; unknown labels reported as coverage debt.
- `stale_memory_rate`: stale or contradicted memory reads divided by memory reads.
- `memory_write_acceptance_rate`: accepted writes divided by candidate writes.
- `post_verification_success_gain`: success after verifier correction minus success before verifier correction.
- `verifier_false_positive_rate`: verifier fail on runs whose oracle passes.
- `verifier_false_negative_rate`: verifier pass on runs whose oracle fails.
- `cross_task_transfer_gain`: memory-enabled cost-normalized success minus no-memory cost-normalized success on matched tasks.
- `oracle_route_precision`: selected oracle-useful modules divided by selected modules when oracle route labels are available.
- `cost_frontier_auc`: area under success versus cost threshold curve for a policy family.

### counterexamples

- A run with `task_success = 1` and high `activation_cost` should rank lower on `cost_normalized_success` than an equally successful cheap run.
- A run with `task_success = 0` and low cost is not a win; it should show low cost but zero cost-normalized success.
- A memory-enabled run can have high success and still be risky if `negative_transfer_cases` or harmful reads rise.
- A verifier-always-on ablation can increase catch rate and still be worse if cost doubles without success gain.
- Route scores can be high for rejected modules; route quality must use selected outcomes, cost, and oracle/proxy regret, not score alone.

## interfaces

### normalized run summary

`scoring_script.py` emits:

```yaml
run_summary:
  trajectory_path: string
  task_id: string | null
  benchmark_id: string | null
  baseline_id: string | null
  final:
    success_label: pass | fail | partial | unknown
    task_success: boolean
    failure_reason: string | null
  process:
    activation_cost: number
    module_calls: int
    verifier_calls: int
    repeated_action_ratio: number
    invalid_tool_call_ratio: number
    loop_stuck: boolean
    budget_exhaustion: boolean
    step_exhaustion: boolean
    premature_halt: boolean
  routing:
    route_events: int
    route_candidates: int
    selected_candidates: int
    route_reject_rate: number
    route_entropy: number
    selected_route_score_mean: number | null
    selected_route_cost_mean: number | null
    oracle_route_regret_mean: number | null
    proxy_route_regret_mean: number | null
  memory:
    memory_reads: int
    useful_memory_reads: int
    harmful_memory_reads: int
    unknown_memory_reads: int
    useful_memory_reuse_rate: number | null
    negative_transfer_cases: int
  verifier:
    verifier_failures: int
    verifier_catches: int
    verifier_catch_rate: number | null
  known_deviations: [string]
```

### source fields

Target schema fields:

- `final_success_label`
- `failure_reason`
- `events[].event_type`
- `events[].action_type`
- `events[].action_payload_hash`
- `events[].selected_modules`
- `events[].route_scores`
- `events[].cost_delta`
- `events[].latency_ms`
- `events[].error_type`
- `events[].verifier_result`
- `events[].memory_ids_read`
- `events[].memory_usefulness_label`
- `events[].route_decision.oracle`

Legacy 06 fields:

- `kind == start`, `payload.goal`, `payload.config`
- `kind == route`, `payload.candidates`, `payload.selected_modules`, `payload.route_scores`
- `kind == budget_gate`, `payload.decision`, `payload.module_id`, `payload.module_cost`
- `kind == memory_read`, `payload.usefulness_label`, `payload.negative_transfer_count`
- `kind == verifier_result`, `payload.status`
- `kind == halt_gate`, `payload.reason`, `payload.success_signal`, `payload.budget_snapshot`
- `kind == finish`, `payload.final_answer`, `payload.failure_signals`, `payload.selected_modules`

### known deviations

- If a metric needs an oracle or exact tests and the trajectory lacks them, the script returns `null` and records a known deviation.
- If token cost is absent, `activation_cost` is a toy module-cost estimate and must not be compared to API prices.
- If action hashes are absent, repeated action ratio uses module IDs as a proxy.
- If task schema is absent, task-family-specific metrics such as `test_pass_rate` and `citation_correctness` are not computed.

## experiments

1. `scoring_legacy_trajectory`
   - Run `scoring_script.py` on an existing 06 trajectory.
   - Expected output: non-null activation cost, route counts, selected route score/cost means, memory reuse counts, verifier counts, and halt flags.

2. `cost_quality_control`
   - Compare a success trajectory and a cheap failure trajectory.
   - Expected output: success trajectory has `task_success = true`; cheap failure has lower cost but zero `cost_normalized_success`.

3. `negative_transfer_fixture`
   - Score a trajectory with `memory_read.usefulness_label == harmful` or `negative_transfer_count > 0`.
   - Expected output: `negative_transfer_cases > 0`, and memory usefulness metrics report the harmful read.

## risks

- Module-cost estimates from toy runtime are not directly comparable to token/API price.
- Premature halt inference is approximate without explicit task oracle status and remaining oracle steps.
- Verifier catch is undercounted in legacy logs because correction events are not explicit.
- Route entropy can reward indecision if interpreted without success and cost.
- Unknown memory labels can make memory precision look better if silently dropped.

## open_questions

- Should `activation_cost` be replaced by a weighted `total_cost` once token/tool/verifier costs are available?
- Should premature halt require human/oracle confirmation, or is log inference enough for Phase 0 alerts?
- What repeated-action threshold should define loop stuck across code and search tasks?
- Should route entropy be normalized by available modules or only activated modules?
- How should verifier catch be credited when a verifier fails but the runtime stops instead of correcting?
