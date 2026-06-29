# Routing Features

## scope

This document defines the feature dictionary used by `rule_router`, `lexical_router`, optional `embedding_router`, optional `learned_router`, and all gates. Each feature must be derivable from Subtask 02 state, module, memory, route, trajectory, failure, budget, or halt fields.

Phase 0-1 uses auditable lexical and metadata features. Embedding and learned features are enhanced extensions.

## claims

- [文献] Routing literature shows that cost-quality decisions need quality, cost, latency, and regret features rather than only semantic relevance.
- [文献] Memory and self-improvement work motivates reuse outcome, failure, and negative-transfer features.
- [原型] Subtask 02 route logs already require all score terms needed for Phase 0-1 scoring.
- [实验] A feature dictionary enables ablations such as no-cost, no-risk, no-memory, no-repetition, lexical versus embedding, and fixed versus adaptive top-k.
- [猜想] Feature provenance is as important as feature value; every metric should remain computable without hidden prompts or raw transcripts.

## design

### minimal version

Required route score terms:

| Feature | Schema field | Range | Phase 0-1 source | Notes |
| --- | --- | --- | --- | --- |
| `semantic_match` | `route_decision.candidates[].score_terms.semantic_match` | `[0,1]` | lexical overlap between route query and module key/capability/schema terms | Default is lexical, not embedding. |
| `reliability` | `score_terms.reliability` | `[0,1]` | `module.reliability.observed_success_rate` or `prior` | Use prior when sample size is low. |
| `historical_success` | `score_terms.historical_success` | `[0,1]` | `module.history_features.historical_success` filtered by task family | Separate from reliability to expose task-family transfer. |
| `cost` | `score_terms.cost` | `[0,+]` normalized then clipped for scoring | module cost estimate divided by remaining or nominal budget | Subtracted in score. |
| `latency` | `score_terms.latency` | `[0,+]` normalized then clipped for scoring | module `latency.p50_ms`/`p95_ms` over remaining time | Subtracted in score. |
| `risk` | `score_terms.risk` | `[0,1]` | `module.risk.score` plus state-conditioned adjustments | Subtracted in score and used by gates. |
| `repetition_penalty` | `score_terms.repetition` | `[0,1]` | recent duplicate `module_id` and `action_payload_hash` in route history | Subtracted in score. |
| `memory_bonus` | `score_terms.memory_bonus` | `[-1,1]` | useful memory support minus harmful/stale memory penalty | Can be negative for likely transfer harm. |

Minimal lexical `semantic_match`:

```text
query_terms = normalize(goal + active_subgoal + uncertainties + action_need + evidence_need)
module_terms = normalize(module.capability + task_tags + schema refs + risk labels)
semantic_match =
  0.50 * tag_overlap
  + 0.25 * capability_keyword_hit_rate
  + 0.25 * schema_overlap
```

Minimal derived gate features:

```yaml
uncertainty_max_severity: low | medium | high
requires_current_info: boolean
requires_external_action: boolean
requires_executable_feedback: boolean
irreversible_action: boolean
previous_failure_severity: none | info | warning | blocking | fatal
remaining_budget_fraction: float
duplicate_action_recent: boolean
memory_harm_prior: float
```

### enhanced version

Enhanced features add:

- `embedding_similarity`: query/module vector cosine, stored as a feature value or hash with model/version metadata.
- `route_disagreement`: variance between rule, lexical, embedding, and learned scores.
- `expected_information_gain`: predicted uncertainty reduction from a module call.
- `counterfactual_memory_delta`: success/cost delta versus no-memory replay where available.
- `oracle_or_proxy_regret`: from offline matrix or labeled proxy replay.
- `calibrated_gate_probability`: learned probability that a gate should open.
- `route_stability`: route-switch frequency across similar states.

These features must not replace required score terms. They may inform weights, thresholds, or enhanced routers.

### counterexamples

- High lexical `semantic_match` can select a stale web-search skill for a local code task unless task family and evidence need are included.
- Low cost can dominate if `historical_success` and `risk` are missing, producing cheap repeated failures.
- Memory features based only on retrieval score can reward negative transfer; reuse outcomes and harmful counts are required.
- Repetition features based only on module ID can penalize legitimate repeated test runs; include `action_payload_hash` and correction context.

## interfaces

### feature record

```yaml
routing_feature_record:
  feature_id: string
  run_id: string
  step_id: int
  module_id: string | null
  memory_id: string | null
  feature_name: string
  feature_value: number | string | boolean
  feature_source:
    - state.goal
    - state.task_state
    - state.uncertainties
    - state.failure_signals
    - state.budget
    - module.key
    - module.cost
    - module.latency
    - module.risk
    - module.reliability
    - module.history_features
    - memory_entry.reuse_outcomes
    - trajectory_event
  feature_version: string
  evidence_refs: [string]
```

### score serialization

The router writes feature values into the Subtask 02 route schema:

```yaml
route_decision:
  candidates:
    - module_id: string
      score_terms:
        semantic_match: float
        reliability: float
        historical_success: float
        cost: float
        latency: float
        risk: float
        repetition: float
        memory_bonus: float
      selected: boolean
      reject_reason: string | null
```

### metric sources

| Metric | Required features/events |
| --- | --- |
| route entropy | candidate `score_total` distribution and selected flags |
| cost-normalized success | `success_signal`, `cost_delta`, budget snapshot |
| repeated action ratio | `action_payload_hash`, `module_id`, `step_id` |
| invalid tool call ratio | `error_type: invalid_tool`, `action_type: tool_call` |
| verifier catch rate | `verifier_result: fail`, following correction event |
| memory retrieval precision | `memory_ids_read`, `memory_usefulness_label` |
| negative transfer cases | harmful memory label plus later regression/failure |
| router regret | `route_decision.oracle.oracle_regret` or `proxy_regret` |

## experiments

1. `feature_computability_check`: Given trajectory fixtures, compute every required score term and process metric without raw prompts. The experiment fails if any metric needs hidden module internals.
2. `feature_ablation_matrix`: Compare full lexical router to no-cost, no-latency, no-risk, no-repetition, no-memory-bonus, and semantic-only variants. Metrics: success, cost, latency, repeated action ratio, invalid calls, harmful memory reads, and proxy regret.
3. `lexical_vs_embedding_probe`: Optional enhanced ablation on paraphrased tasks. Keep lexical as the Phase 0-1 default and report whether embedding improves recall enough to justify cost and complexity.

## risks

- Feature drift can occur if Markdown definitions and runtime code diverge; use `feature_version` and validation fixtures.
- Lexical feature normalization choices can dominate results on small task suites.
- Derived labels such as negative transfer may require counterfactual or human review and should not be overclaimed.
- Embedding features can hide why a route fired unless paired with metadata explanations.
- Learned features can leak benchmark answers if memory/task split information is not enforced.

## open_questions

- Should `routing_feature_record` be added to the formal schema or remain a derived analysis artifact?
- What exact tokenizer/normalizer should define lexical `semantic_match` for Phase 0-1?
- How should legitimate repeated actions, such as rerunning tests after a patch, be distinguished from loop-stuck repetition?
- Should expected information gain be included in Phase 1 scoring or reserved for enhanced experiments?
