# Router Design

## scope

This document specifies the Phase 0-1 router for Agent-Attention Runtime. The router chooses which `agent`, `tool`, `memory`, `skill`, `verifier`, `aggregator`, or `halt` module to activate at a runtime step, using the state/module/route/memory/trajectory/halt contracts from Subtask 02.

In scope:

- Four router layers: `rule_router`, `lexical_router`, `embedding_router`, and `learned_router`.
- Cost-, latency-, risk-, repetition-, and memory-aware sparse activation.
- Full candidate logging for selected and rejected modules.
- Negative routing cases where the router should deliberately avoid a plausible but harmful route.

Out of scope:

- Changing the Subtask 02 schemas.
- Assuming multi-agent routes are stronger by default.
- Requiring embeddings or learned routing for Phase 0-1.

## claims

- [文献] ReAct, Toolformer, HuggingGPT, Reflexion, Voyager, FrugalGPT, RouteLLM, RouterBench, MasRouter, and Agent-as-a-Router motivate explicit trajectories, tool gates, memory, feedback, cost-quality routing, and regret-style router evaluation.
- [原型] The current project memo and Subtask 02 spec treat deterministic heuristic routing as a valid Phase 0-1 measurement harness when all score terms are logged.
- [实验] Router quality can be evaluated separately from final task success through route logs, cost-normalized success, repeated action ratio, invalid calls, verifier catch rate, negative transfer, and oracle/proxy regret.
- [猜想] The useful contribution is selective activation under observable budget and risk, not activating more agents. Multi-agent activation can hurt through cost, latency, instability, consensus drift, and negative transfer.

## design

### minimal version

Phase 0-1 uses a deterministic cascade:

```text
eligible = schema_filter(module_pool, state_t)
eligible = safety_budget_filter(eligible, state_t.budget, state_t.failure_signals)
rules = rule_router(state_t, eligible)
scores = lexical_router(state_t, eligible, rules)
selected = top_k_or_threshold(scores, budget_status, uncertainty, risk)
```

`semantic_match` is lexical by default in Phase 0-1. It is computed from normalized token overlap between the route query and module keys:

```text
semantic_match =
  0.50 * jaccard(query.task_tags, module.key.task_tags)
  + 0.25 * keyword_hit_rate(query.action_need, module.capability)
  + 0.25 * schema_term_overlap(query.required_io, module.key.input_schema_ref/output_schema_ref)
```

Every candidate keeps the Subtask 02 score terms:

```text
score_i =
  w_sem * semantic_match_i
  + w_rel * reliability_i
  + w_hist * historical_success_i
  - w_cost * normalized_cost_i
  - w_lat * normalized_latency_i
  - w_risk * risk_i
  - w_rep * repetition_penalty_i
  + w_mem * memory_bonus_i
```

Default weights inherit Subtask 02:

```yaml
semantic_match: 1.00
reliability: 0.50
historical_success: 0.50
cost: 0.35
latency: 0.20
risk: 0.45
repetition_penalty: 0.30
memory_bonus: 0.25
```

Default top-k:

```text
k = 1 when uncertainty_low and risk_low
k = 2 when uncertainty_medium, verifier_disagreement, or failed_previous_route
k = min(3, budget.max_parallel_calls) when risk_high and BudgetGate permits
```

The minimal router must never return only the selected module. It logs every candidate, score term, weight, gating validity flag, selection bit, and reject reason.

### enhanced version

The enhanced router keeps the same interface but adds optional layers:

- `embedding_router`: replaces only the lexical implementation of `semantic_match` with embedding similarity plus metadata filters. It remains an enhanced variant, not a Phase 0-1 dependency.
- `learned_router`: uses trajectory-derived features and supervised/bandit feedback in Phase 4. It must log feature version, policy version, exploration mode, and constrained top-k results.
- `adaptive_top_k`: increases k when uncertainty, route disagreement, irreversible action, or previous failures are high, then shrinks k under low budget or repeated duplicate routes.
- `cost_quality_frontier`: suppresses a higher scoring module if a cheaper candidate is within `epsilon_quality = 0.05` and expected risk is not higher.
- `router_textual_update`: after repeated failures, a local update can adjust a router rule, threshold, or weight with evidence and rollback condition.

### counterexamples

- If a coding task only needs a cheap syntax check, routing to a large planner plus two agents may improve confidence language while wasting cost and increasing latency.
- If a search task asks for stable information already present in trusted memory, SearchGate should often stay closed; web search can add stale or irrelevant evidence.
- If an irrelevant memory shares many lexical terms with the current task, `memory_bonus` must be countered by prior harmful outcomes and negative-transfer labels.
- If all tasks in a homogeneous suite require the same module, dynamic routing may underperform a fixed workflow because router overhead has no useful choice to make.
- If a learned router is trained on noisy final success labels, it may overfit cheap modules, popular modules, or accidental benchmark artifacts.

## interfaces

### router input

```yaml
router_input:
  state_t: state
  module_pool: [module]
  memory_candidates: [memory_entry]
  budget_status: budget_state
  failure_signals: [failure_signal]
```

### router output

```yaml
router_output:
  selected_modules: [string]
  scores:
    - module_id: string
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
        repetition_penalty: float
        memory_bonus: float
      score_weights:
        semantic_match: float
        reliability: float
        historical_success: float
        cost: float
        latency: float
        risk: float
        repetition_penalty: float
        memory_bonus: float
      selected: boolean
      reject_reason: null | schema_invalid | budget_exceeded | risk_exceeded | below_top_k | suppressed_duplicate | dominated_by_cheaper_candidate | gate_closed
  rationale: string
  expected_cost: float
  expected_risk: float
```

`repetition_penalty` maps to the Subtask 02 `score_terms.repetition` field when serialized. The name is expanded here for readability; the route event should preserve both a human label and the schema-compatible key if needed.

### router layers

| Layer | Phase | Purpose | Input features | Output | Default status |
| --- | --- | --- | --- | --- | --- |
| `rule_router` | 0 | Hard inclusion/exclusion from task family, action need, schema, and safety. | `state.goal`, `active_subgoal`, `failure_signals`, module kind, schemas, risk labels. | eligibility flags and rule reasons. | Required. |
| `lexical_router` | 0-1 | Auditable score over module keys and route query. | lexical tokens, task tags, schema terms, cost, latency, risk, repetition, memory labels. | full candidate scores. | Required. |
| `embedding_router` | 2+ | Better semantic recall for paraphrases and large module pools. | query embedding, module key embedding, metadata filters. | replacement/enhancement for `semantic_match`. | Optional enhanced. |
| `learned_router` | 4 | Optimize route policy from historical trajectories. | state/module/memory/budget/failure features and outcomes. | constrained route probabilities or scores. | Future only. |

### trajectory event fields

Router decisions are logged as `trajectory_event.event_type: route_decision` with:

```yaml
candidate_modules: [module_id]
selected_modules: [module_id]
route_scores:
  module_id:
    score_total: float
    semantic_match: float
    reliability: float
    historical_success: float
    cost: float
    latency: float
    risk: float
    repetition: float
    memory_bonus: float
    reject_reason: string | null
action_type: no_op
cost_delta: zero_or_router_overhead
latency_ms: router_latency_ms
error_type: none | budget_exceeded | schema_invalid | loop_stuck | negative_transfer
```

Metrics computable from these fields:

- route entropy
- selected module count
- average module calls
- cost-normalized success
- repeated action ratio
- suppressed duplicate count
- route switch count
- invalid route ratio
- oracle/proxy router regret

## experiments

1. `sparse_activation_vs_fixed_workflow`: Compare `single_react_agent`, `fixed_workflow_agent`, `fixed_moa_agent`, top-1 router, top-2 router, and adaptive top-k router on the Phase 0-1 code/search suite. Metrics: task success, cost-normalized success, average module calls, token/tool/verifier cost, latency, repeated action ratio, invalid tool call ratio, premature halt, verifier catch rate, route entropy, and proxy regret.
2. `cost_sensitive_frontier`: Run the same tasks under low, medium, and high budget ceilings. Compare normal weights, no-cost-term, and exaggerated-cost-term routers. Metrics: success, total cost, cost-normalized success, budget-exceeded events, verifier catch rate, and tasks where cheap dominated choices matched expensive-route success.
3. `negative_routing_case`: Inject irrelevant/stale memories and semantically attractive but risky tools. The correct router should avoid a high lexical match when negative-transfer rate, risk, or repetition is high. Metrics: harmful memory read count, negative transfer cases, risk-triggered rejections, success delta versus no-memory, and rejected high-semantic-match candidate outcomes.

## risks

- Lexical routing can miss paraphrases and make the early router look weaker than the architecture could be.
- Score weights can look precise despite being provisional; all weights must be logged and ablated.
- Cost penalties can over-suppress useful verification, causing false confidence or premature halt.
- Memory bonus can reward stale or causally irrelevant memories unless usefulness labels and harmful outcomes are included.
- Learned routing can optimize benchmark quirks if trained before trajectory quality and labels are reliable.
- Multi-agent top-k can increase cost and instability even when final success improves.

## open_questions

- Should Phase 1 allow a lightweight embedding `semantic_match` ablation while keeping lexical as the official default?
- What exact proxy regret formula should be shared with Subtask 06 when no offline route oracle exists?
- How should router latency be accounted for when the router is implemented inside an existing LLM call rather than a separate module?
- Should `repetition_penalty` stay as an alias or should all documents use the shorter schema key `repetition` only?
