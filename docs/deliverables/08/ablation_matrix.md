# Ablation Matrix

## scope

This document defines the first Agent-Attention ablation matrix. Each ablation changes exactly one variable relative to a declared control unless the row is explicitly marked as a separate factorial follow-up. The matrix covers memory, verifier, halt, budget, route score terms, textual backpropagation, memory write policy, top-k, and router-family variants.

The first control is `agent_attention_default_phase0`: lexical router, adaptive top-k, memory read/write enabled, conditional verifier gate, halt gate enabled, budget gate enabled, repetition/risk/cost penalties enabled, and textual backpropagation enabled only as logged local update proposals, not automatic global rewrites.

## claims

- [文献] Routing systems should be evaluated with cost-quality and regret-style metrics, so score-term ablations must include cost, latency, and route entropy/regret where available.
- [文献] Memory and Reflexion-style feedback can help or harm, so no-memory, read-only, success-only write, and textual-backprop controls are necessary.
- [文献] Verifier and critic stages can catch failures but also add cost and false alarms; no-verifier and always-on verifier are both required.
- [原型] Subtask 06 emits gate, route, memory, verifier, budget, halt, and finish events that support Phase 0 scoring, with known legacy deviations.
- [实验] Subtask 07 metrics can score most ablations from existing fields, while oracle/proxy regret requires target envelope extensions or offline route matrices.
- [猜想] The proposed system can lose when lexical routing misses paraphrases, memory creates negative transfer, or cost/risk penalties block a useful expensive module.

## design

### minimal version

Control configuration:

```yaml
control_id: agent_attention_default_phase0
baseline_id: agent_attention_agent
routing_policy: lexical
top_k_policy: adaptive
memory_policy: read_write_behavior_kv
memory_write_policy: success_plus_failure
verifier_policy: conditional
halt_gate: enabled
budget_gate: enabled
score_terms:
  semantic_match: enabled
  reliability: enabled
  historical_success: enabled
  cost: enabled
  latency: enabled
  risk: enabled
  repetition: enabled
  memory_bonus: enabled
textual_backprop: local_update_proposals_only
```

Required one-variable ablations:

| Ablation ID | Single Change From Control | Tests | Metrics To Inspect | Expected Failure Or Counterexample |
| --- | --- | --- | --- | --- |
| `aa_no_memory` | Disable memory read and write; set `memory_bonus = 0`. | Whether gains come from memory. | success, activation cost, memory reads, useful reuse, negative transfer, route entropy. | May improve stale-memory tasks by avoiding negative transfer. |
| `aa_memory_read_only` | Allow memory reads; disable all memory writes. | Whether writes/reflections add value beyond retrieval. | memory reuse, cross-task transfer gain, cost, negative transfer. | May prevent noisy failure memories from polluting later runs. |
| `aa_success_only_memory_write` | Write memory only after final `pass`. | Whether failure memories/avoid rules help. | useful reuse, verifier catch, wrong-route activation, negative transfer. | May miss avoid patterns after failed or partial tasks. |
| `aa_no_verifier` | Disable verifier calls and verifier-required halt. | Whether verifier catches matter. | success, activation cost, premature halt, verifier catch, false confidence. | May be cheaper and equally successful on easy synthetic tasks. |
| `aa_verifier_always_on` | Run verifier at every step or after every module output within verifier budget. | Whether conditional verifier is cost-effective. | verifier calls, verifier catch, latency, activation cost, success. | May catch more errors but lose cost-normalized success. |
| `aa_no_halt_gate` | Disable learned/heuristic halt decision; stop only at max steps or external terminal success. | Whether halt gate causes premature stop or saves cost. | step exhaustion, cost, repeated ratio, loop stuck, premature halt. | May reduce premature halt but increase loops and cost. |
| `aa_no_budget_gate` | Do not reject modules for budget; still log cost. | Whether budget gate blocks useful modules. | success, activation cost, budget exhaustion, cost-normalized success. | May raise raw success by overspending. |
| `aa_no_repetition_penalty` | Set repetition score weight to zero. | Whether repetition penalty prevents loops. | repeated action ratio, loop stuck, route entropy, success. | May help when repeating a verifier/test is genuinely useful. |
| `aa_no_risk_penalty` | Set risk score weight to zero. | Whether risk term prevents harmful routes. | invalid tool ratio, negative transfer, verifier failures, success. | May improve tasks where risk estimate is overconservative. |
| `aa_no_cost_penalty` | Set cost and latency score weights to zero, keep budget ceiling. | Whether cost-aware routing matters. | activation cost, latency, cost-normalized success, budget rejection. | May improve raw success but worsen cost frontier. |
| `aa_no_textual_backprop` | Disable failure reflection/update proposals; keep memory and router unchanged. | Whether local textual updates help future trials. | repeated failure rate, memory writes, verifier catch, success on replay. | May reduce noisy overfit updates. |
| `aa_top1` | Force top-k to 1. | Whether sparse single activation suffices. | module calls, success, latency, route regret. | May be cheapest but miss verifier/aggregator needs. |
| `aa_top2` | Force top-k to 2. | Whether fixed small fanout beats adaptive. | module calls, success, repeated ratio, cost. | May outperform adaptive if adaptive k is noisy. |
| `aa_adaptive_topk` | Use adaptive top-k. This is the control row for top-k sweeps. | Whether uncertainty/risk-driven fanout is useful. | cost-normalized success, route entropy, verifier catch. | May over-activate on ambiguous but easy tasks. |
| `aa_rule_router` | Replace lexical semantic scoring with deterministic rules; keep all other score terms. | Whether simple rules are enough. | success, route entropy, route regret, wrong-route activation. | May beat lexical on seed tasks with clear task-family tags. |
| `aa_lexical_router` | Use lexical router. This is the Phase 0 control row. | Baseline deterministic router. | selected score, route reject rate, entropy, success. | May fail paraphrases and synonym-heavy tasks. |
| `aa_embedding_router` | Replace lexical semantic match with embedding similarity only. | Whether semantic paraphrase handling improves. | route precision/regret, success, latency/cost, negative transfer. | May retrieve semantically similar but causally wrong routes. |
| `aa_learned_router_replay` | Replace semantic/rule router with learned policy in offline replay; keep gates and budgets. | Whether learned routing improves route choice after logs exist. | oracle/proxy regret, cost-normalized success, route entropy. | May overfit noisy toy labels and cheap modules. |

### enhanced version

Enhanced matrix additions:

- Factorial follow-up for interactions after single-variable results: memory x verifier, top-k x cost penalty, router family x memory policy.
- Cost-frontier sweeps for `aa_no_cost_penalty`, `aa_verifier_always_on`, `aa_top1`, `aa_top2`, and `aa_adaptive_topk`.
- Offline route replay using synthetic oracle route matrices to report true `oracle_route_regret`.
- Held-out negative-transfer suite with useful, irrelevant, stale, contradictory, and wrong-route memory entries.
- Real code-task verifier integration where `verifier_result` is backed by tests rather than deterministic toy signals.
- Confidence intervals by task family once each family has at least 20 tasks.

### counterexamples

- `aa_no_memory` can beat the full proposed system on stale or adversarial memory probes.
- `aa_no_verifier` can beat verifier-enabled systems on trivial tasks where verifier cost is pure overhead.
- `aa_verifier_always_on` can catch more failures but still be worse because latency and activation cost dominate.
- `aa_no_budget_gate` can raise raw success by spending beyond the allowed budget; this must not be counted as a fair win.
- `aa_top1` can beat adaptive top-k on homogeneous tasks where the best module is obvious.
- `aa_embedding_router` can be worse than lexical/rule routing if semantic similarity ignores tool schema or task-family constraints.
- `aa_learned_router_replay` can underperform if trained on legacy trajectories with missing oracle labels or proxy costs.

### ablation groups

| Group | Rows | Primary Causal Question |
| --- | --- | --- |
| Memory | `aa_no_memory`, `aa_memory_read_only`, `aa_success_only_memory_write` | Is transfer from memory helpful, harmful, or just overhead? |
| Verification | `aa_no_verifier`, `aa_verifier_always_on` | Is conditional verifier routing better than none or always-on? |
| Gates | `aa_no_halt_gate`, `aa_no_budget_gate` | Do gates prevent waste without causing premature failures? |
| Score terms | `aa_no_repetition_penalty`, `aa_no_risk_penalty`, `aa_no_cost_penalty` | Which objective terms carry measurable value? |
| Feedback | `aa_no_textual_backprop` | Do local textual update proposals improve replay or held-out tasks? |
| Top-k | `aa_top1`, `aa_top2`, `aa_adaptive_topk` | Does sparse fanout need to adapt to task uncertainty/risk? |
| Router | `aa_rule_router`, `aa_lexical_router`, `aa_embedding_router`, `aa_learned_router_replay` | Is route selection driven by rules, lexical signals, semantic embeddings, or learned feedback? |

## interfaces

### ablation config

```yaml
ablation_run_config:
  run_id: string
  task_id: string
  benchmark_id: string
  baseline_id: agent_attention_agent
  ablation_id: string
  control_id: agent_attention_default_phase0
  changed_variable:
    name: string
    control_value: string | number | boolean | object
    ablated_value: string | number | boolean | object
  invariants:
    same_task: true
    same_budget: true
    same_model_tier: true
    same_tool_access: true
    same_memory_corpus_except_policy: true
    same_verifier_implementation_except_policy: true
  runtime_config:
    routing_policy: rule | lexical | embedding | learned
    top_k_policy: top1 | top2 | adaptive
    memory_policy: none | read_only | read_write
    memory_write_policy: none | success_only | success_plus_failure
    verifier_policy: none | conditional | always_on
    halt_gate_enabled: boolean
    budget_gate_enabled: boolean
    score_weights:
      cost: number
      latency: number
      risk: number
      repetition: number
      memory_bonus: number
    textual_backprop_enabled: boolean
  output_trajectory_schema: agent_attention.benchmark_trajectory.v0.1 | legacy_06_event_list
```

### required trajectory fields

Every ablation run must support the `docs/deliverables/07/scoring_script.py` fields:

- Final: `final_success_label`, `failure_reason`, or legacy final halt/finish equivalent.
- Process: cost, module calls, verifier calls, repeated module/action proxy, invalid tool failures, loop stuck, budget exhaustion, step exhaustion, premature halt.
- Routing: route candidates, selected candidates, selected modules, route reject rate, route entropy, selected route score/cost, oracle/proxy regret where available.
- Memory: memory reads, usefulness labels, negative-transfer count.
- Verifier: verifier statuses, failures, catches.

Known 06/07 deviations to record:

- Legacy event list lacks top-level `run_id`, `task_id`, `benchmark_id`, `baseline_id`, and `final_success_label`.
- Legacy cost is scalar toy activation cost, not full `cost_delta`.
- Legacy logs lack oracle/proxy route regret.
- Legacy action repetition uses module IDs as proxy when action hashes are absent.
- Legacy verifier catch is conservative because correction events are not explicit.

### result join keys

Use these join keys for result tables:

```yaml
join_keys:
  - task_id
  - benchmark_id
  - task_family
  - baseline_id
  - ablation_id
  - control_id
  - run_id
  - seed
```

When using legacy Subtask 06 trajectories, `task_id`, `benchmark_id`, and `run_id` may be missing and must be supplied by an external manifest, not guessed from final answer text.

## experiments

1. `single_variable_gate_score_ablation`
   - Run control plus `aa_no_memory`, `aa_no_verifier`, `aa_verifier_always_on`, `aa_no_halt_gate`, `aa_no_budget_gate`, `aa_no_repetition_penalty`, `aa_no_risk_penalty`, and `aa_no_cost_penalty` on the Phase 0 seed suite.
   - Controls: identical task records, budgets, model tier, memory fixture, and verifier implementation.
   - Metrics: success, cost-normalized success, activation cost, module calls, repeated ratio, premature halt, budget exhaustion, verifier catch, negative transfer.

2. `memory_policy_negative_transfer_ablation`
   - Run `aa_no_memory`, `aa_memory_read_only`, `aa_success_only_memory_write`, and control on `phase0_seed_negative_memory_001` plus repeated code/search tasks.
   - Controls: same injected useful and harmful memory IDs; no benchmark answer leakage.
   - Metrics: useful reuse, harmful reads, negative-transfer cases, wrong-route activation, verifier catch, success/cost delta.

3. `topk_router_family_ablation`
   - Run top-k variants and router variants in separate sweeps: first top-k under lexical router, then router family under fixed top-k.
   - Controls: only one variable changes inside each sweep.
   - Metrics: route entropy, oracle/proxy regret where available, selected route score/cost, module calls, success, latency.

4. `textual_backprop_replay_control`
   - Run failed trajectories with control and `aa_no_textual_backprop`, then replay one local update at a time.
   - Controls: same replay task, same memory corpus, same budget, no global prompt rewrite.
   - Metrics: repeated failure reduction, held-out regression, negative transfer, verifier catch, cost delta.

## risks

- Some ablations cannot be executed on the current legacy runtime without a runner or manifest; keep them as design rows until implemented.
- Single-variable discipline can be broken accidentally if disabling a gate also changes logging; ablation configs must record the changed variable explicitly.
- Learned router replay should wait until enough target-envelope logs exist; legacy logs lack route oracle labels.
- Cost-normalized success can be misleading if activation cost remains a toy scalar; report the deviation.
- Verifier always-on may exceed verifier budget; if so, the ablation should change only policy intent, while budget rejections remain logged.
- Textual backprop can overfit failure explanations unless held-out regression checks are included.

## open_questions

- What is the official control value for adaptive top-k thresholds?
- Should `aa_no_budget_gate` be allowed to exceed budget for diagnostic purposes, or should it only disable pre-call rejection while still marking budget violations?
- Should `aa_embedding_router` be Phase 1 or Phase 4, given the Wave 2 default of lexical-only Phase 0?
- What minimum trajectory count is required before `aa_learned_router_replay` is meaningful?
- Should unknown memory usefulness count as neutral, harmful, or coverage debt in ablation summaries?
- How should verifier false positives and false negatives be labeled when task oracles are rubric-based?
