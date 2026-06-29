# Formal Spec

## scope

This document defines the Phase 0-1 formal model for Agent-Attention: a sparse, logged runtime that routes over agents, tools, memories, skills, verifiers, aggregators, and halt gates. It turns the Transformer/MoE/Memory analogy into implementable state, module, routing, memory, trajectory, update, and halt contracts.

The spec is intentionally conservative. A toy runtime should be able to implement it with deterministic heuristics and JSON logs before any learned router exists. Learned routing is a Phase 4 extension.

Out of scope:

- Claiming that multi-agent activation is generally stronger than a single agent.
- Requiring differentiable attention over discrete tools.
- Modifying Subtask 01 deliverables, `docs/decision_log.md`, `docs/project_status.md`, `src/`, or `tests/`.

## claims

- [文献] ReAct, Toolformer, HuggingGPT, Reflexion, Voyager, MoA, RouterBench, MasRouter, and Agent-as-a-Router justify modeling agent execution as loop state plus actions, external calls, memory, feedback, routing, aggregation, and verification.
- [原型] The memo states that the current toy runtime is a deterministic measurement harness; this spec preserves that by requiring auditable route terms and trajectory JSON events.
- [猜想] The useful novelty is not "more agents"; it is selective activation under observable cost, latency, risk, reliability, memory transfer, and verifier feedback.
- [猜想] The Transformer/MoE analogy is useful only as naming pressure: query/key/value, sparse activation, residual goal anchor, memory KV, and gates must all compile down to concrete runtime fields.

## design

### minimal version

The runtime is a recurrent controller with explicit state:

```text
state_t = Update(state_{t-1}, observation_t, action_{t-1}, memory_delta_t)
query_t = BuildQuery(state_t)
route_t = Router(query_t, module_pool, memory_index)
outputs_t = Execute(route_t.selected_modules)
state_{t+1} = Aggregate(state_t, outputs_t)
halt_t = HaltGate(state_{t+1})
```

Minimum modules:

- one `agent` module for reasoning or generation
- one `tool` module or environment action
- one `memory` module supporting typed read/write
- one `verifier` module
- one `aggregator` module
- one `halt` gate represented as a routeable decision, even if implemented as a function

Minimum routing:

```text
score_i =
  semantic_match_i
  + alpha * reliability_i
  + beta * historical_success_i
  - gamma * cost_i
  - delta * latency_i
  - eta * risk_i
  - rho * repetition_i
  + memory_bonus_i
```

Every score term must be logged per candidate, not only for selected modules.

Minimum state fields:

- `goal`: immutable original request, the residual anchor.
- `task_state`: decomposition, active subgoal, progress, and status.
- `working_memory`: compact short-term context, not full history.
- `observations`: recent external observations and summaries.
- `beliefs`: accepted facts or hypotheses with evidence references.
- `uncertainties`: unresolved questions and missing evidence.
- `failure_signals`: errors, contradictions, failed tests, invalid calls, verifier failures, loop-stuck signals.
- `budget`: token, time, tool, verifier, retry, latency, monetary, and optional human-review accounting.
- `route_history`: selected modules, candidate scores, route features, and outcomes.
- `verification_status`: required checks, verifier results, and whether halt is allowed.

### enhanced version

Enhanced Agent-Attention adds:

- Hierarchical modules: atomic modules are the default logged unit; composite workflows are allowed only when they expose child activations or an explicit opaque-cost record.
- Typed memory under one schema: `knowledge_memory`, `episodic_memory`, `skill_memory`, and `behavior_kv`.
- Adaptive top-k routing: choose `k` from uncertainty, risk, budget, and disagreement.
- Conditional verifier routing: activate verifiers when risk, uncertainty, irreversible action, or halt attempt crosses a threshold.
- Textual backpropagation: failures produce local updates to router rules, module prompts, memory write policy, verifier checklist, tool schema, halt threshold, or decomposition heuristic.
- Regret reporting: use offline oracle route matrices when available; otherwise report proxy regret separately or leave regret undefined.
- Learned router in Phase 4:

```text
pi(module_i | state_t) = learned_router(features(state_t, module_i))
reward = success - cost - latency - invalid_calls - repeated_actions - risk_penalty
```

### counterexamples

- If all tasks use the same best module, dynamic routing can add cost and latency with no benefit.
- If memory retrieval is semantically similar but causally irrelevant, memory can create negative transfer.
- If verifiers are weak, verifier-gated halting can increase false confidence and loop length.
- If a fixed MoA activates all agents, gains may be caused by extra tokens and parallel candidates rather than architecture.
- If a learned router is trained on noisy feedback, it may overfit cheap modules or unstable success labels.

### analogy versus mechanism

| Term | Transformer/MoE/Memory analogy | Actual runtime mechanism |
| --- | --- | --- |
| Residual connection | Keep original signal available across layers. | `state.goal` is immutable and every update links derived subgoals back to it. |
| Query | Token representation seeking relevant keys. | `query_t` encodes task intent, subgoal, uncertainty, failures, budget, and evidence needs. |
| Key | Module/memory address used for matching. | Module capability, schemas, task tags, reliability, cost, risk, and history features. |
| Value | Retrieved content or expert output. | Module output, memory entry, verifier result, skill, observation, or aggregation decision. |
| Sparse MoE | Activate a small set of experts. | Top-k selected modules under logged score terms and budget constraints. |
| Attention weights | Soft relevance over keys. | Interpretable route scores; no claim of differentiability in Phase 0-1. |
| Memory network | External read/write memory. | Typed entries with keys, values, provenance, usefulness, and negative-transfer labels. |
| Layer | Stack of transformations. | Runtime step or optional hierarchical workflow level, logged as trajectory events. |
| Gate | Select expert or stop computation. | Router, verifier gate, memory write gate, and halt gate. |

## interfaces

### symbol table

| Symbol | Runtime field | Meaning |
| --- | --- | --- |
| `g` | `state.goal` | Immutable original goal. |
| `s_t` | `state` | Full compact state at step `t`. |
| `q_t` | `route_decision.query` | Current routing query. |
| `m_i` | `module.id` | Candidate module. |
| `k_i` | `module.key` | Capability/schema/history key for `m_i`. |
| `v_i` | `module_output` or `memory_entry.value` | Result returned by selected module or memory. |
| `a_t` | `trajectory_event.action_type/action_payload_hash` | Action executed at step `t`. |
| `o_t` | `trajectory_event.observation` | External or module observation. |
| `r_t` | `route_decision` | Candidate scores and selected modules. |
| `B_t` | `state.budget` | Remaining and spent budget. |
| `F_t` | `state.failure_signals` | Active failure signals. |
| `V_t` | `state.verification_status` | Verification state and halt eligibility. |
| `H_t` | `halt_decision` | Stop/continue decision with reason. |

### baseline/category/benchmark alignment

The runtime must preserve Subtask 01 fields so experiments can compare systems without schema conversion:

```yaml
baseline:
  id: string
  family: single_agent | fixed_workflow | retrieval_memory | moa | router | agent_attention
  controller_policy: prompt | program | learned_router | cascade | search
  routing_policy: none | static | heuristic | learned | feedback_updated
  memory_policy: none | read_only | episodic | skill_library | virtual_context | behavior_kv
  feedback_update: none | self_feedback | external_feedback | verbal_reflection | local_policy_update
  activation_budget: {max_steps: int, max_calls: int, max_tokens: int}
  trajectory_requirements: [thought, action, observation, route_decision, cost, verifier_result]

category:
  id: string
  observables_from_log: [string]
  typical_failures: [string]

benchmark:
  id: string
  task_family: coding | web | embodied | qa | tool_use | routing | mixed_assistant
  success_metric: string
  process_metrics_from_log: [string]
  oracle_route_possible: boolean
  negative_transfer_probe: boolean
```

### state schema summary

```yaml
state:
  run_id: string
  task_id: string
  step_id: int
  goal:
    original: string
    goal_hash: string
    constraints: [string]
    success_criteria: [string]
  task_state:
    active_subgoal: string
    decomposition: [{subgoal_id, parent_id, status, evidence_refs}]
    progress_status: not_started | in_progress | blocked | verifying | done | failed
  working_memory:
    summary: string
    focus_items: [string]
    context_refs: [string]
  observations: [observation_ref]
  beliefs: [{id, statement, confidence, evidence_refs, status}]
  uncertainties: [{id, question, evidence_needed, severity}]
  failure_signals: [failure_signal]
  budget: budget_state
  route_history: [route_decision_ref]
  verification_status: verification_status
```

### module schema summary

```yaml
module:
  id: string
  parent_id: string | null
  kind: agent | tool | memory | skill | verifier | aggregator | halt
  capability: string
  key:
    task_tags: [string]
    input_schema_ref: string
    output_schema_ref: string
    applicable_benchmarks: [string]
  input_schema: object
  output_schema: object
  cost: {token_estimate, tool_call_cost, verifier_call_cost, monetary_cost}
  latency: {p50_ms, p95_ms}
  risk: {score, labels}
  reliability: {prior, observed_success_rate, sample_size}
  history_features:
    historical_success: float
    invalid_call_rate: float
    repeated_action_rate: float
    negative_transfer_rate: float
```

### route decision schema summary

```yaml
route_decision:
  decision_id: string
  step_id: int
  query: query
  candidates:
    - module_id: string
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
      selected: boolean
      reject_reason: string | null
  selected_modules: [string]
  routing_policy: heuristic | static | learned | feedback_updated
  top_k: int
  budget_snapshot: budget_state
  oracle:
    oracle_available: boolean
    oracle_best_module_id: string | null
    oracle_regret: float | null
    proxy_regret: float | null
```

### memory entry schema summary

```yaml
memory_entry:
  memory_id: string
  memory_type: knowledge_memory | episodic_memory | skill_memory | behavior_kv
  key:
    task_signature: string
    route_signature: [string]
    tool_schema_refs: [string]
    failure_success_features: [string]
  value:
    trajectory_summary: string
    accepted_facts: [string]
    successful_workflow: [string]
    useful_reflection: string
    reusable_skill_ref: string | null
  provenance:
    source_run_id: string
    evidence_refs: [string]
    created_at: string
  write_reason: success | failure | uncertainty | negative_transfer | manual_seed
  reuse_outcomes:
    useful_count: int
    harmful_count: int
    last_outcome: useful | harmful | neutral | unknown
```

### trajectory event schema summary

Each event must contain enough data to compute all process metrics:

```yaml
trajectory_event:
  event_id: string
  run_id: string
  task_id: string
  step_id: int
  event_type: state_update | route_decision | module_call | memory_read | memory_write | aggregate | verifier_result | failure_update | halt
  baseline_id: string
  category_ids: [string]
  benchmark_id: string
  state_ref: string
  goal_hash: string
  candidate_modules: [string]
  selected_modules: [string]
  route_scores: object
  action_type: llm_call | tool_call | memory_read | memory_write | verifier_call | aggregate | halt | no_op
  action_payload_hash: string
  observation_summary: string
  success_signal: pass | fail | partial | unknown
  verifier_result: pass | fail | skipped | inconclusive
  cost_delta: cost_delta
  latency_ms: int
  error_type: none | invalid_tool | timeout | contradiction | loop_stuck | premature_halt | verifier_failed | budget_exceeded | negative_transfer
  memory_ids_read: [string]
  memory_ids_written: [string]
  memory_usefulness_label: useful | harmful | neutral | unknown | not_applicable
  correction_of_event_ids: [string]
  evidence_refs: [string]
```

## experiments

1. `toy_runtime_schema_compliance`: Implement a deterministic runtime over 20 synthetic code/search/tool tasks. The test passes if every state update, route decision, memory read/write, verifier result, failure update, and halt event validates against `schemas.json`, and every metric listed in this spec can be computed from logs without reading raw prompts.
2. `heuristic_router_ablation`: Compare `single_react_agent`, `fixed_workflow_agent`, `fixed_moa_agent`, and `agent_attention_agent` on the same task set. Ablate no memory, no verifier gate, no cost term, no risk term, fixed top-k, and adaptive top-k. Report success, token cost, latency, repeated action ratio, invalid tool call ratio, verifier catch rate, memory reuse, negative transfer, and route entropy.
3. `oracle_proxy_regret_split`: On RouterBench/CodeRouterBench-style offline outcome matrices, compute true oracle regret. On tasks without an oracle matrix, compute proxy regret from verifier outcome, cost-normalized success, and counterfactual baseline replay, then label it as `proxy_regret` only.

## risks

- The state can become a hidden full-history prompt. Mitigation: require compact `working_memory.summary`, event refs, and evidence pointers rather than raw transcript duplication.
- Heuristic scores can look scientific while hiding arbitrary weights. Mitigation: log score terms, weights, selected modules, rejected modules, and outcomes.
- Typed memory may overfit before ablation evidence exists. Mitigation: keep one schema with memory type labels and run no-memory/read-only/write-policy ablations.
- Multi-agent routes can inflate success by spending more. Mitigation: expanded cost accounting and cost-normalized success.
- Verifier-gated halt can fail when verifier signals are weak. Mitigation: log verifier checklists, false positives, false negatives, and inconclusive results.

## open_questions

- What benchmark subset becomes the canonical Phase 0-1 toy suite: code/search only, or code/search/web?
- What proxy regret formula should be official when no offline oracle route matrix exists?
- What thresholds should trigger verifier-required halt: risk, uncertainty, irreversible action, or all of them?
- How strict should composite modules be: must every child activation be logged, or is opaque-cost logging acceptable for expensive external systems?
- Who labels memory usefulness and negative transfer in early experiments: verifier, heuristic counterfactual, or human review?
