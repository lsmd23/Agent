# Router Ablation Plan

## scope

This document defines executable ablations and controls for the Subtask 03 router/gate design. The plan is restricted to code/search Phase 0-1 tasks, with optional web tasks as stretch, and uses only metrics computable from Subtask 02 trajectory/log fields.

The plan tests whether sparse routing improves efficiency, stability, and reliability under matched budgets. It does not claim multi-agent activation is generally stronger.

## claims

- [文献] FrugalGPT, RouteLLM, RouterBench, MasRouter, and Agent-as-a-Router show that routing should be evaluated with cost-quality and regret-style metrics, not only final accuracy.
- [文献] MoA-style aggregation can improve some outputs but adds cost and may introduce instability; it must be a baseline and counterexample, not an assumed target.
- [原型] Subtask 02 schemas make route decisions, gate decisions, verifier outcomes, memory use, cost, latency, and halt events measurable from logs.
- [实验] Cost-sensitive and negative-routing experiments are required to distinguish useful sparse activation from accidental over-activation.
- [猜想] A conservative lexical router can still be valuable if it reduces wasted calls, repeated actions, invalid calls, and premature halt without reducing success.

## design

### minimal version

Run all policies on the same Phase 0-1 code/search task suite:

| Policy | Description |
| --- | --- |
| `single_react_agent` | One recurrent controller with the same tools, no route scoring. |
| `fixed_workflow_agent` | Static planner -> executor/tool user -> verifier/critic. |
| `fixed_moa_agent` | Fixed candidate agents plus aggregator, full cost logged. |
| `rule_router_top1` | Hard rules select one module. |
| `lexical_router_top1` | Full Phase 0-1 lexical score selects one module. |
| `lexical_router_top2` | Full lexical score selects up to two modules. |
| `adaptive_topk_router` | k selected from uncertainty, risk, failure signals, and budget. |

Primary metrics:

- task success
- cost-normalized success
- average module calls
- token/tool/verifier/latency cost
- repeated action ratio
- invalid tool call ratio
- premature stopping rate
- loop-stuck rate
- verifier catch rate
- memory retrieval precision
- negative transfer cases
- route entropy
- oracle regret where available, otherwise proxy regret or undefined

### enhanced version

Enhanced ablations:

- `embedding_router`: replace lexical `semantic_match` with embedding similarity on paraphrased tasks.
- `learned_router_replay`: train/evaluate only on logged trajectories or offline matrices after Phase 0-1 logs exist.
- `textual_router_update`: allow local rule/threshold updates after repeated failure, with rollback condition.
- `adaptive_budget_frontier`: route to cheaper near-tie candidate when quality gap <= `epsilon_quality`.

### counterexamples

- Fixed workflow should win on homogeneous tasks where the routing decision is always the same.
- Fixed MoA may win on open-ended generation but lose cost-normalized success under equal budgets.
- No-cost router may improve raw success by overspending; this is not a clean architecture gain.
- Memory-enabled router may lose to no-memory when stale or contradictory memories are injected.

## interfaces

### experiment config

```yaml
router_ablation_config:
  task_suite: phase_0_1_code_search
  policies:
    - single_react_agent
    - fixed_workflow_agent
    - fixed_moa_agent
    - rule_router_top1
    - lexical_router_top1
    - lexical_router_top2
    - adaptive_topk_router
  budget:
    max_steps: int
    max_calls: int
    max_tokens: int
    max_latency_ms: int
    max_verifier_calls: int
  required_logs:
    - state_update
    - route_decision
    - module_call
    - memory_read
    - memory_write
    - verifier_result
    - failure_update
    - halt
```

### metric computation contract

All metrics must be computed from:

- `trajectory_event.success_signal`
- `trajectory_event.cost_delta`
- `trajectory_event.latency_ms`
- `trajectory_event.action_type`
- `trajectory_event.action_payload_hash`
- `trajectory_event.error_type`
- `trajectory_event.verifier_result`
- `trajectory_event.memory_ids_read`
- `trajectory_event.memory_usefulness_label`
- `route_decision.candidates[].score_terms`
- `route_decision.oracle.oracle_regret`
- `route_decision.oracle.proxy_regret`
- `halt_decision.halt_reason`
- `halt_decision.final_success_signal`

No metric may require raw hidden prompts or unlogged module internals.

## experiments

1. `sparse_activation_vs_fixed_workflow`
   - Compare fixed baselines against top-1, top-2, and adaptive top-k routers.
   - Controls: same task suite, same tool access, same budget ceilings, same verifier availability.
   - Metrics: success, cost-normalized success, average module calls, repeated action ratio, latency, invalid tool call ratio, premature halt, verifier catch rate.

2. `cost_sensitive_router_control`
   - Compare full score, no-cost/no-latency, high-cost-penalty, and budget-gated frontier policies.
   - Required outcome: identify cases where raw success gains disappear after cost normalization.
   - Metrics: token/tool/verifier cost, budget overrun, success lost from budget blocks, cost saved per successful task, proxy regret.

3. `negative_routing_case`
   - Inject high lexical match but harmful modules/memories: stale search result, irrelevant prior trajectory, risky tool, or repeated failed module.
   - Expected behavior: router rejects or downranks the attractive candidate through risk, repetition, harmful memory prior, or BudgetGate.
   - Metrics: rejected high-semantic-match count, harmful memory reads, negative transfer cases, final success delta, route regret.

4. `gate_accuracy_ablation`
   - Toggle each gate off, always on, and default thresholded mode.
   - Metrics: true positive, false positive, false negative, cost saved, errors introduced, verifier catch rate, premature halt, human-review minutes.

## risks

- Small toy suites can make routing effects look larger or smaller than they are.
- Equal budget comparisons can be unfair if baselines rely on parallel calls or longer context by design; report both equal-budget and unconstrained-cost views.
- Proxy regret can be weaker than oracle regret and must be labeled separately.
- Negative routing fixtures can become artificial; include both injected and naturally occurring cases.
- Learned-router replay should wait until trajectory logs are reliable enough to avoid training on instrumentation bugs.

## open_questions

- What exact Phase 0-1 task count is enough for stable ablation signals: 20, 30, or 50 tasks?
- Should web tasks remain optional until SearchGate is validated on code/search, or be included early to stress browsing failures?
- What is the official cost-normalized success formula across token, tool, verifier, latency, retry, and human-review costs?
- How should equal-budget MoA be configured so it is a fair baseline rather than an intentionally constrained one?
