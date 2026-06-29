# Taxonomy

## scope

This document defines a reusable taxonomy for literature, baselines, benchmarks, and mechanisms relevant to Agent-Attention. It translates the literature table into categories that later subtasks can consume without changing the core terms in `docs/research_memo.md`.

## claims

- [文献] The field separates naturally into loop/control, tool use, memory, aggregation, routing, self-improvement, and evaluation; these categories map to different runtime interfaces.
- [文献] "Routing" should be reserved for a policy that chooses among alternatives under an objective such as quality, cost, risk, latency, or regret. A planner/controller is not automatically a router.
- [原型] The memo's current runtime abstraction can represent most surveyed systems if every module activation is logged with route features, cost, and feedback.
- [猜想] The central research gap is not "more agents" but selective activation plus feedback-updated behavior memory under measurable budgets.

## design

### minimal baseline set

| Baseline ID | Representative Works | What It Tests | Required Logs |
| ----------- | -------------------- | ------------- | ------------- |
| `single_react_agent` | ReAct, SWE-agent as coding variant | Whether a single recurrent loop already solves the task cheaply. | thought/action/observation, tool calls, retries, halt reason, success. |
| `fixed_workflow_agent` | HuggingGPT, MetaGPT, planner-executor-critic | Whether human-written workflow structure beats routing. | stage id, assigned role/tool, stage output, verifier result, cost. |
| `fixed_moa_agent` | Mixture-of-Agents, LLM-Blender-style rank/fuse | Whether aggregation quality offsets extra calls. | proposer outputs, rank/fuse decisions, aggregator output, per-agent cost. |

### enhanced map

| Category | Inclusion Criteria | Exclusion Criteria | Canonical Examples | Agent-Attention Reuse |
| -------- | ------------------ | ------------------ | ------------------ | --------------------- |
| Fixed workflow | Stages/roles are mostly predetermined. | Learned or feedback-updated activation is central. | HuggingGPT, MetaGPT, planner-executor-critic. | Baseline; artifact schema for stage logs. |
| Dynamic planner/controller | Chooses next actions based on observations. | Only one-shot generation with no environment feedback. | ReAct, LATS, SWE-agent. | Control loop and trajectory format. |
| Tool-use learner | Learns/selects/calls APIs or external tools. | Pure RAG without executable calls. | Toolformer, Gorilla, API-Bank, ToolBench. | Tool schema, invalid-call metric, tool gate. |
| Memory-augmented agent | Stores/retrieves experience, context, or skills. | Stateless prompting or static few-shot examples. | Memory Networks, Generative Agents, MemGPT, Voyager, Reflexion. | Memory read/write interfaces and reuse metrics. |
| Multi-agent aggregator | Multiple models/agents produce candidates or debate. | Single model self-refinement only. | MoA, LLM-Blender, AutoGen panels. | Aggregator interface and consensus/cost counterexample. |
| Routing-optimized agent | Explicitly chooses model/agent/MAS configuration under objective. | Plain planner without alternative-cost scoring. | FrugalGPT, RouteLLM, RouterBench, MasRouter, Agent-as-a-Router. | Router score, oracle regret, cost-quality trade-off. |
| Self-improving agent | Uses feedback to update future behavior without weight training. | One-pass verifier with no update. | Reflexion, Self-Refine, Voyager iterative prompting. | Textual backprop and failure attribution. |
| Evaluation benchmark | Provides task set/environment and measurable success. | Demo-only system with no repeatable tasks. | WebShop, ALFWorld, SWE-bench, AgentBench, GAIA, RouterBench, CodeRouterBench. | Task suite and log-derived metrics. |

### counterexamples

- `HuggingGPT` is a controller and model selector, but without learned cost-sensitive feedback it should not be treated as a full router.
- `AutoGen` is a framework; an AutoGen application can implement routing, but the framework itself does not guarantee a routing policy.
- `Reflexion` stores behavioral feedback, but the memory is usually local to the actor and not a general module key-value cache.
- `MoA` activates many agents by design; it is a multi-agent aggregator, not evidence that sparse routing is unnecessary.
- `RouteLLM` is true routing for model choice, but it does not address long-horizon tool/memory/verifier activation.

## interfaces

Canonical category record:

```yaml
category:
  id: routing_optimized_agent
  parent: routing
  definition: "A system with an explicit policy that chooses among candidate modules/models/workflows under a measurable objective."
  required_decision_fields:
    - candidate_ids
    - selected_ids
    - decision_features
    - objective_terms
    - estimated_cost
    - observed_feedback
  log_metrics:
    - route_entropy
    - route_switch_count
    - cumulative_regret
    - cost_normalized_success
  counterexample_tests:
    - "Remove cost term; check if success gain disappears under equal budget."
    - "Use homogeneous tasks; check if routing overhead dominates."
```

Baseline record:

```yaml
baseline:
  id: fixed_moa_agent
  category_ids: [multi_agent_aggregator]
  modules: [proposer_agent, aggregator_agent]
  activation_rule: fixed_all
  compatible_benchmarks: [GAIA, WebShop, SWE-bench-lite]
  required_metrics: [success, token_cost, latency_ms, repeated_action_ratio]
```

Benchmark record:

```yaml
benchmark:
  id: webshop
  category_ids: [evaluation_benchmark]
  task_family: web
  success_metric: purchase_success_or_reward
  trajectory_fields: [state, action, observation, url_or_page, reward, done]
  added_agent_attention_fields: [route_decision, module_id, memory_ids, verifier_result, cost]
```

## experiments

1. `taxonomy_coding_exercise`: Take 12 systems from the table and encode them as `baseline` records. The taxonomy passes if two reviewers assign the same category and routing status for at least 10/12 systems.
2. `controller_vs_router_ablation`: Implement HuggingGPT/MetaGPT-like fixed controller, then add only cost-aware route scoring. Compare success, cost, invalid tool calls, and route entropy on the same tasks.
3. `moa_counterexample_test`: Run fixed MoA with 2, 4, and 6 agents under equal and unequal budgets. Check whether quality gains survive after normalizing for token cost and latency.

## risks

- Category boundaries can blur: a controller may contain implicit routing even when not logged.
- "Memory" can mean context paging, factual recall, episodic reflection, or executable skills; mixing them hides different failure modes.
- Benchmarks with answer-only scoring can reward lucky final answers while hiding unstable trajectories.
- A taxonomy that is too fine-grained will be hard for later subtasks to implement consistently.

## open_questions

- Should `routing_policy` require learned parameters, or is an auditable heuristic router enough for the first paper?
- Should `memory-augmented agent` be split into `knowledge_memory`, `episodic_memory`, and `skill_memory` in the formal model?
- Does `agent_attention` route over atomic modules or over composite workflows such as "coding agent with shell"?
- Which category owns verifier-gated halting: routing, self-improvement, or evaluation?
