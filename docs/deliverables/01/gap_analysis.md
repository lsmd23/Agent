# Gap Analysis

## scope

This document identifies what remains unsolved after mapping the literature: the gap between existing agent loops, tool-use systems, memory systems, multi-agent aggregation, model routing, and the proposed Agent-Attention architecture. It is intended to guide later subtasks on formal modeling, router/gate design, memory KV-cache, textual backpropagation, and benchmark design.

## claims

- [文献] ReAct, LATS, and SWE-agent show that explicit trajectories are valuable, but they do not by themselves solve cost-aware module selection.
- [文献] HuggingGPT and MetaGPT show that fixed role/workflow decomposition is practical, but hand-written stages can over-activate modules and propagate early mistakes.
- [文献] MoA and LLM-Blender show that aggregation can improve outputs, but aggregation is not free: extra candidate generation increases cost and may introduce consensus drift.
- [文献] Reflexion and Voyager show that language feedback and skill memory can improve later trials, but they do not standardize negative-transfer measurement.
- [文献] FrugalGPT, RouteLLM, RouterBench, MasRouter, and Agent-as-a-Router make routing measurable through cost-quality trade-offs or regret, but most routing work routes models/MAS configurations rather than all agent computation units.
- [猜想] The defensible project novelty is a unified, logged, sparse activation interface across agents, tools, memory, skills, verifiers, aggregators, and halting, not a blanket claim that multi-agent systems are better.

## design

### minimal baseline set

Use three baselines before claiming improvement:

1. `single_react_agent`: ReAct-style loop, same tool access, no cross-task memory.
2. `fixed_workflow_agent`: planner -> executor -> critic/verifier, with static stage order.
3. `fixed_moa_agent`: parallel or layered agent candidates plus aggregation, with logged full cost.

### enhanced map

Main gaps and candidate mechanisms:

| Gap | Existing Coverage | Missing Piece | Borrowable Mechanism |
| --- | ----------------- | ------------- | -------------------- |
| Sparse activation | RouteLLM, FrugalGPT, MasRouter, Agent-as-a-Router | Unified routing over tools, agents, memory, skills, verifiers, and halt gate. | Cost-quality score, cascaded controller, C-A-F loop. |
| Behavior memory | Reflexion, Voyager, Generative Agents, MemGPT | Route-conditioned memory keys and negative-transfer labels. | Verbal reflections, executable skill library, memory tiering. |
| Failure feedback | Reflexion, Self-Refine, Voyager, LATS | Local update target: router rule vs prompt vs memory write vs verifier. | Textual reflection and iterative repair. |
| Stability | AgentBench failure analysis, WebShop trajectories, SWE-bench tests | Loop-stuck, repeated action, route-switch, and premature-halt metrics. | Environment feedback and executable verification. |
| Cost accounting | FrugalGPT, RouteLLM, RouterBench, MasRouter | Token/tool/latency cost at every route decision, not only final model call. | Cost-quality frontier and cumulative regret. |
| Benchmark transfer | Voyager transfer, RouterBench transfer, SWE-bench repo diversity | Cross-task routing and memory transfer under controlled negative memories. | Held-out task families and oracle route matrices. |

Three mechanisms to borrow first:

1. `cost_quality_router`: from FrugalGPT/RouteLLM/RouterBench, adapted to module activation.
2. `verbal_failure_memory`: from Reflexion/Voyager, but stored with task, route, feedback, and reuse outcome.
3. `rank_then_fuse_aggregator`: from LLM-Blender/MoA, used only when route uncertainty justifies multiple candidates.

### counterexamples

- If all tasks require the same best module, dynamic routing adds overhead and can reduce reliability.
- If verifier signals are weak, verifier-gated halting can produce false confidence and longer loops.
- If memory retrieval prioritizes semantic similarity over causal usefulness, it can cause negative transfer.
- If MoA uses stronger models or more tokens than the proposed method, apparent gains are not attributable to architecture.
- If the benchmark lacks executable feedback, textual self-improvement may optimize style rather than correctness.

## differences from required comparators

| Comparator | What It Does | Difference From This Project |
| ---------- | ------------ | ---------------------------- |
| ReAct | Interleaves reasoning and acting in one loop. | Agent-Attention treats action-capable agents, tools, memories, verifiers, aggregators, and halt gates as selectable modules; ReAct is the single-loop baseline. |
| MoA | Uses layered multi-agent/model outputs and aggregation. | Agent-Attention should activate extra agents only when expected value exceeds cost/risk; MoA is a fixed aggregation baseline and counterexample for over-activation. |
| HuggingGPT | Uses an LLM controller to plan, select models by descriptions, execute subtasks, and summarize. | Agent-Attention requires logged routing objectives, feedback, memory, and halting; HuggingGPT is a fixed controller/model-pool baseline. |
| Reflexion | Converts feedback into verbal reflections stored in episodic memory. | Agent-Attention generalizes feedback into local updates for router, memory policy, verifier, prompts, and halt thresholds; Reflexion supplies a memory/update mechanism. |
| Voyager | Builds an automatic curriculum and executable skill library in Minecraft. | Agent-Attention borrows skill-memory and iterative repair, but targets mixed code/search/tool tasks with module routing rather than one embodied domain. |

## interfaces

Trajectory-derived metric requirements:

```yaml
trajectory_event:
  task_id: string
  step_id: int
  state_summary: string
  candidate_modules: [string]
  selected_modules: [string]
  route_scores: {module_id: float}
  action_type: llm_call | tool_call | memory_read | memory_write | verifier_call | aggregate | halt
  action_payload_hash: string
  observation_summary: string
  success_signal: pass | fail | partial | unknown
  verifier_result: pass | fail | skipped | inconclusive
  token_cost_estimate: float
  latency_ms: int
  error_type: none | invalid_tool | timeout | contradiction | loop_stuck | premature_halt
  memory_ids_read: [string]
  memory_ids_written: [string]
```

Metrics computable from logs:

```yaml
metrics:
  success_rate: "mean(task.success)"
  average_tool_calls: "mean(count(action_type == tool_call))"
  token_cost: "sum(token_cost_estimate)"
  repeated_action_ratio: "duplicate(action_payload_hash within task) / actions"
  invalid_tool_call_ratio: "count(error_type == invalid_tool) / tool_calls"
  premature_stopping_rate: "halt_before_success_with_remaining_oracle_steps / tasks"
  loop_stuck_rate: "tasks_with_repeated_action_ratio_above_threshold"
  verifier_catch_rate: "verifier_failures_followed_by_successful_correction / verifier_failures"
  memory_retrieval_precision: "useful_memory_reads / memory_reads"
  useful_memory_reuse_rate: "successful_steps_using_prior_memory / memory_reads"
  negative_transfer_cases: "memory_reads_followed_by_regression_or_wrong_route"
  router_regret: "oracle_best_score_minus_selected_score from offline outcome matrix"
```

Benchmark fields:

```yaml
benchmark:
  id: string
  supports_executable_feedback: boolean
  supports_oracle_route: boolean
  supports_cross_task_memory: boolean
  required_tooling: [string]
  cost_observability: token | api_price | wall_clock | tool_calls
```

## experiments

1. `equal_budget_agent_attention_vs_moa`: Run single ReAct, fixed MoA, and Agent-Attention under the same max tokens and wall-clock ceiling. Report success, cost-normalized success, repeated-action ratio, route entropy, and verifier catch rate.
2. `feedback_update_target_ablation`: On tasks with failures, compare no update, reflection-only, router-rule update, memory-write-policy update, and verifier-checklist update. Measure next-trial success, cost, and negative transfer.
3. `oracle_route_replay`: For offline routing benchmarks, replay trajectories with known per-module outcomes and compute selected-route regret. This isolates router quality from model output noise.

## risks

- Without strong single-agent baselines, any improvement may be an artifact of weak prompting.
- Cost normalization can become controversial if different tools have hidden latency or API prices.
- Route decisions may become hard to debug if scoring mixes semantic similarity, memory priors, risk, and verifier signals without event-level logs.
- Cross-task memory evaluation can leak benchmark answers if memory writes are not scoped by train/test split.
- Negative transfer is rare and easy to miss unless deliberately injected or counterfactually measured.

## open_questions

- What is the project's official oracle for route regret when no offline outcome matrix exists?
- Should cost include only model tokens, or also tool latency, human review, failed retries, and verifier calls?
- What minimum benchmark subset is enough to show long-horizon stability without making the prototype too expensive?
- How should reusable skills be sandboxed so that a stored behavior does not silently mutate future tasks?
