# Routing Equations

## scope

This document defines the implementable routing, aggregation, memory, update, regret, and halt equations for the Phase 0-1 Agent-Attention runtime. It gives a deterministic heuristic router first and a learned-router extension for Phase 4.

The equations are runtime contracts: every variable used for scoring must be present in state, module registry, memory entries, or trajectory events.

## claims

- [文献] Cost-quality routing from FrugalGPT, RouteLLM, RouterBench, MasRouter, and Agent-as-a-Router supports separating route quality from raw task success.
- [文献] Reflexion and Voyager motivate failure-conditioned memory and local textual updates.
- [原型] A deterministic top-k router is sufficient for Phase 0-1 because the main need is logging and comparability.
- [猜想] A router that logs semantic match, reliability, historical success, cost, latency, risk, repetition, and memory bonus can expose why sparse activation helps or fails.

## design

### minimal version

At step `t`, build a query:

```text
Q_t = encode(
  goal = state.goal,
  active_subgoal = state.task_state.active_subgoal,
  uncertainties = state.uncertainties,
  failure_signals = state.failure_signals,
  budget = state.budget,
  evidence_need = required_evidence(state),
  action_need = required_action(state)
)
```

For every candidate module `m_i`, compute:

```text
score_i =
  w_sem * semantic_match(Q_t, K_i)
  + w_rel * reliability_i
  + w_hist * historical_success_i
  - w_cost * normalized_cost_i(B_t)
  - w_lat * normalized_latency_i(B_t)
  - w_risk * risk_i
  - w_rep * repetition_i(state.route_history)
  + w_mem * memory_bonus_i(Q_t, M)
```

Default Phase 0-1 weights:

```yaml
w_sem: 1.00
w_rel: 0.50
w_hist: 0.50
w_cost: 0.35
w_lat: 0.20
w_risk: 0.45
w_rep: 0.30
w_mem: 0.25
```

The weights are provisional and must be logged in every `route_decision`.

Term definitions:

```text
semantic_match(Q_t, K_i) in [0, 1]
reliability_i = module.reliability.observed_success_rate or module.reliability.prior
historical_success_i = module.history_features.historical_success
normalized_cost_i = expected_total_cost_i / remaining_or_nominal_budget
normalized_latency_i = expected_latency_i / remaining_or_nominal_time
risk_i = module.risk.score plus state-conditioned risk adjustments
repetition_i = recent_duplicate_activation_penalty(module_id, action_payload_hash)
memory_bonus_i = usefulness_weighted retrieval support for module route
```

Select modules:

```text
C_t = candidates passing schema, budget, and safety constraints
R_t = sort_desc(C_t, score_i)
selected_t = top_k(R_t, k_t)
```

Default `k_t`:

```text
k_t = 1 if uncertainty_low and risk_low
k_t = 2 if uncertainty_medium or verifier_disagreement
k_t = min(3, budget.max_parallel_calls) if risk_high and budget_allows
```

Verifier activation:

```text
require_verifier_t =
  halt_attempt_t
  or risk_high_t
  or executable_change_t
  or contradiction_present_t
  or benchmark.requires_executable_feedback
```

Halt:

```text
halt_allowed_t =
  success_criteria_satisfied(state_t)
  and no_blocking_uncertainty(state_t)
  and budget_not_exceeded(state_t)
  and (verification_status.pass or verification_status.not_required)

halt_t = stop if halt_allowed_t else continue
```

### enhanced version

Hierarchical module score:

```text
score(composite_j) =
  parent_score_j
  - opaque_cost_penalty_j
  + child_explainability_bonus_j
```

where `child_explainability_bonus_j > 0` only when child activations are logged. If a composite workflow hides child calls, it must produce an `opaque_cost_record` with aggregate tokens, tool calls, verifier calls, latency, retries, errors, and human-review time.

State-conditioned risk:

```text
risk_i(state_t) =
  base_risk_i
  + lambda_irrev * irreversible_action_i
  + lambda_fail * active_failure_overlap_i
  + lambda_unc * uncertainty_overlap_i
  + lambda_mem_harm * retrieved_memory_harm_rate_i
```

Memory bonus:

```text
memory_bonus_i =
  mean_top_n(
    retrieval_score(memory_j, Q_t)
    * usefulness_prior(memory_j)
    * route_match(memory_j.key.route_signature, module_i)
    * freshness_decay(memory_j)
  )
  - negative_transfer_penalty_i
```

Aggregation:

```text
accepted = outputs with evidence and no stronger contradiction
rejected = outputs failing verifier or schema checks
uncertainties_{t+1} = unresolved_uncertainties + new_conflicts - resolved_items
beliefs_{t+1} = update_beliefs(beliefs_t, accepted, evidence_refs)
failure_signals_{t+1} = detect_failures(outputs, verifier_results, budget, route_history)
```

Textual backpropagation:

```text
failure_signal f
  -> blame_candidates = rank_by_temporal_proximity_and_causal_link(f, route_history)
  -> update_target in {router_rule, module_prompt, memory_write_policy,
                       verifier_checklist, tool_schema, halt_threshold,
                       task_decomposition_heuristic}
  -> textual_gradient = concise diagnosis + expected local correction
  -> update_record with evidence_refs, confidence, rollback_condition
```

Learned Phase 4 router:

```text
features_i = concat(features(state_t), features(module_i), route_history_features, memory_features)
pi_i = learned_router(features_i)
selected_t = constrained_top_k(pi_i, schema_valid, budget_valid, risk_valid)
reward_t = task_success
  - c_token * token_cost
  - c_tool * tool_calls
  - c_verifier * verifier_calls
  - c_latency * latency_ms
  - c_invalid * invalid_calls
  - c_repeat * repeated_actions
  - c_risk * realized_risk
```

### counterexamples

- A high semantic score can select a familiar but unreliable module; reliability and historical success are separate terms to expose this.
- A cheap module can dominate if cost is over-weighted; success and verifier outcome must remain in downstream metrics.
- A memory bonus can be harmful when stale memories share vocabulary with the task; negative-transfer penalties must be logged.
- A learned router can reduce exploration and miss new modules; Phase 4 needs held-out route evaluation and drift checks.

## interfaces

### route score event fields

Every candidate in `route_decision.candidates` must include:

```yaml
module_id: string
schema_valid: boolean
budget_valid: boolean
risk_valid: boolean
score_total: float
score_terms:
  semantic_match: float
  reliability: float
  historical_success: float
  cost: float
  latency: float
  risk: float
  repetition: float
  memory_bonus: float
score_weights:
  semantic_match: float
  reliability: float
  historical_success: float
  cost: float
  latency: float
  risk: float
  repetition: float
  memory_bonus: float
selected: boolean
reject_reason: null | schema_invalid | budget_exceeded | risk_exceeded | below_top_k | suppressed_duplicate
```

### cost accounting

Cost is cumulative in `state.budget` and incremental in `trajectory_event.cost_delta`:

```yaml
cost_delta:
  prompt_tokens: int
  completion_tokens: int
  token_cost_estimate: float
  tool_calls: int
  tool_cost_estimate: float
  verifier_calls: int
  verifier_cost_estimate: float
  failed_retries: int
  retry_cost_estimate: float
  latency_ms: int
  monetary_cost_estimate: float
  human_review_minutes: float
```

`human_review_minutes` is separately labeled and never mixed silently into model/tool price.

### regret accounting

```yaml
route_regret:
  oracle_available: boolean
  oracle_source: offline_matrix | exhaustive_replay | none
  selected_score: float | null
  oracle_best_score: float | null
  oracle_regret: float | null
  proxy_regret: float | null
  proxy_formula: string | null
```

Rules:

- Use `oracle_regret` only when an offline outcome matrix or exhaustive replay exists.
- Use `proxy_regret` for verifier-derived or baseline-derived estimates.
- Leave both null when neither is defensible.

### metric formulas from trajectory

```yaml
success_rate: "mean(final_task_success == pass)"
average_tool_calls: "mean(sum(cost_delta.tool_calls by run_id))"
token_cost: "sum(cost_delta.token_cost_estimate)"
latency: "sum(cost_delta.latency_ms) or wall_clock from events"
repeated_action_ratio: "count(duplicate action_payload_hash within run) / count(action events)"
invalid_tool_call_ratio: "count(error_type == invalid_tool) / max(1, sum(tool_calls))"
premature_stopping_rate: "count(halt where success_signal != pass and budget remains) / task_count"
loop_stuck_rate: "count(run with repeated_action_ratio > threshold or error_type == loop_stuck) / task_count"
verifier_catch_rate: "count(verifier_result == fail followed by correction_success) / count(verifier_result == fail)"
memory_retrieval_precision: "count(memory_read event with memory_usefulness_label == useful) / count(memory_read)"
useful_memory_reuse_rate: "count(successful step with memory_usefulness_label == useful) / count(memory_read)"
negative_transfer_cases: "count(memory_usefulness_label == harmful or error_type == negative_transfer)"
router_regret: "sum(oracle_regret where oracle_available)"
proxy_router_regret: "sum(proxy_regret where oracle_available == false and proxy_regret != null)"
route_entropy: "entropy(selected module distribution by run or benchmark)"
route_switch_count: "count(selected_modules_t != selected_modules_{t-1})"
cost_normalized_success: "success_score / max(epsilon, total_cost)"
```

## experiments

1. `route_term_replay`: Save route decisions for 100 steps, then replay selection while zeroing one score term at a time. Measure selected-module changes, success delta, cost delta, verifier catch delta, and negative-transfer delta.
2. `adaptive_top_k_vs_fixed`: Compare fixed `k=1`, fixed `k=2`, and adaptive `k_t` on mixed tasks. Report success, cost, latency, route entropy, verifier catch rate, and loop-stuck rate.
3. `verifier_gate_threshold_sweep`: Sweep risk and uncertainty thresholds for `require_verifier_t`. Report premature halt, verifier false confidence, latency, and cost-normalized success.

## risks

- Normalizing cost by remaining budget can over-penalize expensive but necessary modules late in a task.
- Historical success can reinforce early lucky wins; include sample size and confidence.
- Proxy regret can be mistaken for oracle regret; fields and reports must keep them separate.
- Adaptive top-k can hide cost growth if parallel calls are not fully accounted.
- Repetition penalty can suppress legitimate retries after a corrected tool argument.

## open_questions

- Should Phase 0-1 use lexical similarity, embeddings, or both for `semantic_match`?
- What default threshold should define low, medium, and high uncertainty?
- Should `memory_bonus` be capped to prevent old memories from dominating fresh evidence?
- How should route score weights be chosen for the first public experiment: hand-set, grid-searched, or fitted on a development split?
- What proxy regret formula is acceptable for tasks without oracle matrices?
