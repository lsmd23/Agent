# Literature Table

## scope

This table maps papers, systems, and benchmarks that are directly useful for positioning an Agent-Attention architecture: a sparse, routable control layer over agents, tools, memories, skills, verifiers, aggregators, and halt gates. The scope is not a general agent survey. It focuses on work that can inform baselines, routing policies, behavior memory, feedback updates, or trajectory-level evaluation.

Sources prioritize paper pages, official repositories, benchmark pages, or author/project pages. Recency-sensitive routing entries were checked on 2026-06-26.

## claims

- [文献] Existing agent-loop work gives strong recurrent baselines, but usually keeps the controller fixed inside a single prompt/program rather than learning or logging sparse module activation as a first-class policy.
- [文献] Tool-use papers often solve API selection and argument generation; only some expose enough trajectory structure to evaluate invalid calls, retries, and cost-aware routing.
- [文献] Multi-agent aggregation can improve generation quality in some settings, but fixed layered/panel designs are not equivalent to budget-aware sparse routing and can increase cost, latency, and instability.
- [文献] Routing work is strongest for model selection and cost-quality trade-offs; agent/tool/memory/verifier routing is newer and less standardized.
- [文献] Memory work splits into knowledge/context memory and behavior/skill memory. This project needs the latter: route-conditioned reusable trajectory summaries, failures, and negative-transfer records.
- [猜想] A clean Agent-Attention result is more likely to come from efficiency/stability improvements under matched success than from broad SOTA claims.

## design

### taxonomy

- `Loop and Acting`: interleaved reasoning/action loops and planner-controller agents.
- `Tool Use`: API/model invocation, tool retrieval, argument formation, and tool-use training data.
- `Multi-Agent Aggregation`: debate, panel, mixture, rank-and-fuse, and conversation frameworks.
- `Routing`: model routing, cascade routing, multi-agent-system routing, agentic routing with feedback.
- `Memory`: external memory, episodic reflection, virtual context, skill libraries.
- `Self-Improvement`: verbal feedback, iterative refinement, failure-aware update loops.
- `Evaluation`: interactive, coding, web, routing, and tool-use benchmarks with trajectory/log signals.

### minimal baseline set

The three main baselines recommended for this project are:

1. `single_react_agent`: one ReAct-style loop chooses all actions and sees the same tools.
2. `fixed_workflow_agent`: planner -> executor/tool user -> verifier/critic, using HuggingGPT/MetaGPT/SWE-agent patterns.
3. `fixed_moa_agent`: fixed N-agent or layered MoA aggregator under the same task budget.

### enhanced map

The enhanced comparison should add:

- `retrieval_memory_agent`: same single loop plus memory retrieval/write.
- `routing_model_agent`: RouteLLM/FrugalGPT-style model router adapted to module selection.
- `agent_attention_agent`: sparse top-k module activation with memory, verifier, and halt gates logged at every step.

### counterexamples

- MoA can be stronger on open-ended generation but worse for constrained tasks if all agents are always activated.
- Reflection can amplify a wrong diagnosis if failure signals are noisy.
- Memory can hurt when stale or over-retrieved trajectories bias future routing.
- A fixed workflow may beat dynamic routing on homogeneous tasks because the routing overhead has no useful decision to make.

## interfaces

Minimum schema fields to align with later subtasks:

```yaml
baseline:
  id: string
  name: string
  family: single_agent | fixed_workflow | retrieval_memory | moa | router | agent_attention
  controller_policy: prompt | program | learned_router | cascade | search
  module_pool: [agent | tool | memory | verifier | skill | aggregator]
  routing_policy: none | static | heuristic | learned | feedback_updated
  memory_policy: none | read_only | episodic | skill_library | virtual_context | behavior_kv
  feedback_update: none | self_feedback | external_feedback | verbal_reflection | local_policy_update
  activation_budget: {max_steps: int, max_calls: int, max_tokens: int}
  trajectory_requirements: [thought, action, observation, route_decision, cost, verifier_result]

category:
  id: string
  definition: string
  inclusion_criteria: [string]
  exclusion_criteria: [string]
  observables_from_log: [string]
  typical_failures: [string]

benchmark:
  id: string
  task_family: coding | web | embodied | qa | tool_use | routing | mixed_assistant
  environment_type: static_dataset | interactive_env | executable_repo | simulator | offline_router
  success_metric: string
  process_metrics_from_log: [tool_calls, token_cost, invalid_calls, retries, loop_stuck, verifier_catch]
  oracle_route_possible: boolean
  negative_transfer_probe: boolean
```

## literature map

| Work | Year | Category | Core Mechanism | Agent Module Mapping | Evaluation | Limitation For This Project | Source |
| ---- | ---- | -------- | -------------- | -------------------- | ---------- | --------------------------- | ------ |
| ReAct | 2022 | Loop and Acting | Interleaves reasoning traces and environment actions. | Single recurrent controller; tool/environment calls are actions. | HotpotQA, FEVER, ALFWorld, WebShop. | Strong loop baseline but no explicit sparse module router or learned activation policy. | [arXiv](https://arxiv.org/abs/2210.03629), [code](https://github.com/ysymyth/ReAct) |
| Toolformer | 2023 | Tool Use | Self-supervised training to decide when/how to call APIs and incorporate results. | Tool-use gate embedded in LM token generation. | Downstream NLP tasks with calculator, QA, search, translation, calendar tools. | Learns tool calls, not multi-module agent routing or behavior memory. | [arXiv](https://arxiv.org/abs/2302.04761), [Meta page](https://ai.meta.com/research/publications/toolformer-language-models-can-teach-themselves-to-use-tools/) |
| HuggingGPT | 2023 | Tool Use / Fixed Workflow | LLM controller plans tasks, selects Hugging Face models by descriptions, executes, summarizes. | Planner, model selector, executor, summarizer. | Multimodal AI task demos. | Controller is mostly fixed; model selection is textual and not budget/feedback optimized. | [arXiv](https://arxiv.org/abs/2303.17580), [code](https://github.com/AI-Chef/HuggingGPT) |
| Gorilla / APIBench | 2023 | Tool Use | Retriever-aware API-call generation over large API sets. | Tool retriever plus API-call generator. | APIBench over HuggingFace, TorchHub, TensorHub APIs. | Focuses on API accuracy; not a full long-horizon agent loop. | [arXiv](https://arxiv.org/abs/2305.15334), [project](https://gorilla.cs.berkeley.edu/) |
| API-Bank | 2023 | Evaluation / Tool Use | Runnable benchmark for planning, retrieving, and calling APIs in dialogues. | Tool-use environment and API-call evaluator. | 73 API tools, annotated tool-use dialogues, training set. | Good tool benchmark, but behavior-memory and routing regret need extra logging. | [arXiv](https://arxiv.org/abs/2304.08244), [ACL](https://aclanthology.org/2023.emnlp-main.187/) |
| ToolLLM / ToolBench | 2023 | Tool Use / Evaluation | Builds tool-use instruction data over 16k+ APIs and evaluates multi-tool solution paths. | Tool retriever, planner, API caller, search over tool paths. | ToolBench and ToolEval. | Strong for API use; less direct for verifier-gated halting and cross-task behavior memory. | [arXiv](https://arxiv.org/abs/2307.16789), [code](https://github.com/openbmb/toolbench) |
| Reflexion | 2023 | Self-Improvement / Memory | Verbal reinforcement: reflect on feedback and store episodic memory for later trials. | Actor, evaluator, self-reflection memory. | Sequential decision-making, coding, reasoning tasks. | Updates are textual and useful, but not routed across a module pool. | [arXiv](https://arxiv.org/abs/2303.11366), [code](https://github.com/noahshinn/reflexion) |
| Self-Refine | 2023 | Self-Improvement | Same model iteratively gives feedback and refines outputs without training. | Generator, feedback provider, refiner; often same LM. | Seven generation/reasoning tasks. | Test-time refinement loop can improve outputs but lacks environment-grounded route/action logs. | [arXiv](https://arxiv.org/abs/2303.17651), [OpenReview](https://openreview.net/forum?id=S37hOerQLB) |
| LATS | 2023/2024 | Loop and Acting / Planning | Monte Carlo Tree Search with LM reasoning, value estimates, and reflections. | Planner/search controller, actor, value/verifier, reflection. | HumanEval, WebShop, QA, math. | Search can be expensive; route policy is tree expansion rather than reusable module attention. | [arXiv](https://arxiv.org/abs/2310.04406), [code](https://github.com/lapisrocks/LanguageAgentTreeSearch) |
| Voyager | 2023 | Memory / Self-Improvement | Automatic curriculum, executable skill library, iterative prompting with feedback. | Curriculum agent, action/code generator, skill memory, self-verifier. | Minecraft exploration and transfer to new worlds. | Excellent behavior-skill memory; environment-specific and not a general module router. | [arXiv](https://arxiv.org/abs/2305.16291), [project](https://voyager.minedojo.org/), [code](https://github.com/MineDojo/Voyager) |
| Memory Networks | 2014/2015 | Memory | Long-term memory read/write with inference components. | External memory abstraction: write, retrieve, infer, respond. | QA and simulated-world tasks. | Conceptual anchor, not an LLM agent runtime or trajectory memory implementation. | [arXiv](https://arxiv.org/abs/1410.3916) |
| Generative Agents | 2023 | Memory / Planning | Stores observations, retrieves memories, reflects, and plans social behavior. | Observation memory, reflection synthesizer, planner. | Sandbox simulation and human evaluation of believability. | Memory is behavior-relevant but evaluation is social believability, not task efficiency/regret. | [arXiv](https://arxiv.org/abs/2304.03442), [code](https://github.com/joonspk-research/generative_agents) |
| MemGPT | 2023 | Memory | Virtual context management across memory tiers with control-flow interrupts. | Memory manager, context paging, user/system interrupts. | Long-document QA and multi-session chat. | Solves context management more than route-conditioned behavior reuse. | [arXiv](https://arxiv.org/abs/2310.08560), [project](https://research.memgpt.ai/) |
| AutoGen | 2023 | Multi-Agent Framework | Conversable agents with programmable multi-agent interaction patterns. | Agent pool, conversation protocol, optional tools/humans. | Multiple application examples across coding, QA, math, decision tasks. | Flexible framework, but routing/activation quality is developer-defined unless instrumented. | [arXiv](https://arxiv.org/abs/2308.08155), [Microsoft Research](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/) |
| MetaGPT | 2023 | Fixed Workflow / Multi-Agent | Encodes SOPs into prompt sequences and assigns roles in an assembly-line workflow. | Product manager, architect, engineer, reviewer roles with artifacts. | Collaborative software engineering benchmarks. | Good fixed-workflow baseline; role activation is mostly static and may propagate early errors. | [arXiv](https://arxiv.org/abs/2308.00352), [code](https://github.com/geekan/MetaGPT) |
| Mixture-of-Agents | 2024 | Multi-Agent Aggregation | Layered agents consume previous-layer outputs to improve generation. | Fixed layered proposer/aggregator agents. | AlpacaEval 2.0, MT-Bench, FLASK. | Not sparse or cost-aware by default; high parallel call cost and possible consensus drift. | [arXiv](https://arxiv.org/abs/2406.04692), [code](https://github.com/togethercomputer/moa) |
| LLM-Blender | 2023 | Multi-Agent Aggregation | Ranks candidate outputs pairwise and fuses top candidates. | Candidate generators, PairRanker, GenFuser. | MixInstruct and multiple instruction-following metrics. | Useful rank/fuse mechanism, but assumes candidate outputs exist and lacks long-horizon actions. | [arXiv](https://arxiv.org/abs/2306.02561), [project](https://yuchenlin.xyz/LLM-Blender/) |
| FrugalGPT | 2023 | Routing | LLM cascade with learned order/stopping to reduce cost and improve accuracy. | Model router/cascade and halt threshold. | NLP tasks with cost-accuracy curves. | Strong cost baseline but routes models, not tools/memories/verifiers/skills. | [arXiv](https://arxiv.org/abs/2305.05176), [OpenReview](https://openreview.net/forum?id=cSimKw5p6R) |
| RouteLLM | 2024 | Routing | Learns routers from preference data to select strong vs weak LLMs. | Query encoder, model router, cost-quality policy. | Widely used generation benchmarks and transfer across model pairs. | Useful for routing objective; not agentic and has no trajectory feedback loop. | [arXiv](https://arxiv.org/abs/2406.18665), [code](https://github.com/lm-sys/routellm) |
| RouterBench | 2024 | Routing Benchmark | Dataset/framework for evaluating multi-LLM routing with 405k+ inference outcomes. | Offline router evaluation with known outcomes. | Multi-model outcome matrix and routing metrics. | Excellent oracle/regret substrate, but not long-horizon agent execution. | [arXiv](https://arxiv.org/abs/2403.12031), [code](https://github.com/withmartian/routerbench) |
| MasRouter | 2025 | Routing / Multi-Agent | Cascaded controller routes collaboration mode, agent roles, and LLM assignment. | MAS router over mode, role allocation, model selection. | MBPP, HumanEval, mainstream MAS framework integration. | Very close; still focused on MAS construction rather than memory/tool/verifier as unified modules. | [arXiv](https://arxiv.org/abs/2502.11133), [code](https://github.com/yanweiyue/masrouter) |
| Agent-as-a-Router / CodeRouterBench | 2026 | Routing / Evaluation | Context-Action-Feedback loop with orchestrator, verifier, memory for coding model routing. | Orchestrator, verifier, memory, model router, regret benchmark. | CodeRouterBench with about 10k tasks and verified scores from 8 frontier LLMs. | Closest recent comparator; routes backend models for coding, not full agent/tool/memory module activation. | [arXiv](https://arxiv.org/abs/2606.22902), [code](https://github.com/LanceZPF/agent-as-a-router) |
| SWE-agent | 2024 | Loop and Acting / Coding System | Agent-computer interface for editing, navigation, and tests in real repos. | Single coding agent plus shell/editor/test interface. | SWE-bench and HumanEvalFix. | Strong coding baseline; ACI focus rather than explicit multi-module routing. | [arXiv](https://arxiv.org/abs/2405.15793), [code](https://github.com/swe-agent/swe-agent) |
| WebShop | 2022 | Evaluation | Simulated shopping website for grounded web navigation and purchase tasks. | Interactive environment with search/click/select actions. | Task success and reward over product-finding trajectories. | Good long-horizon web benchmark, but needs added module-routing logs. | [arXiv](https://arxiv.org/abs/2207.01206), [project](https://webshop-pnlp.github.io/), [code](https://github.com/princeton-nlp/WebShop) |
| ALFWorld | 2020/2021 | Evaluation | TextWorld and embodied ALFRED-aligned tasks for abstract-to-grounded policies. | Environment simulator with text/embodied action loop. | Household task success across seen/unseen splits. | Good for planning stability; may be too embodied for early code/search prototype. | [arXiv](https://arxiv.org/abs/2010.03768), [project](https://alfworld.github.io/) |
| SWE-bench | 2023/2024 | Evaluation | Real GitHub issues require code edits validated by tests. | Executable repository environment and patch verifier. | Resolved issue rate on 2,294 Python tasks. | Strong real-world benchmark but expensive; use Lite/verified subsets for initial experiments. | [arXiv](https://arxiv.org/abs/2310.06770), [code](https://github.com/swe-bench/SWE-bench) |
| AgentBench | 2023 | Evaluation | Multi-environment benchmark for LLM-as-agent reasoning and decision-making. | Suite of interactive environments and evaluator package. | 8 environments, multi-turn open-ended generation. | Good breadth; may mix capabilities too broadly for isolating router effects. | [arXiv](https://arxiv.org/abs/2308.03688), [code](https://github.com/THUDM/AgentBench) |
| GAIA | 2023 | Evaluation | Real assistant questions requiring reasoning, browsing, multimodality, and tool use. | Mixed assistant task benchmark with short verifiable answers. | 466 questions and public leaderboard. | Useful mixed-task stress test; tool access and answer-only scoring need custom trajectory instrumentation. | [arXiv](https://arxiv.org/abs/2311.12983), [leaderboard](https://huggingface.co/spaces/gaia-benchmark/leaderboard) |

## experiments

1. `baseline_matrix_smoke`: Implement the three main baselines plus `agent_attention_agent` over a 30-task pilot split: 10 WebShop-style tasks, 10 SWE-bench Lite-style tasks, and 10 GAIA-style research/tool tasks. Log `route_decision`, `module_id`, `tool_calls`, `token_cost`, `latency_ms`, `verifier_result`, `halt_reason`, `success`.
2. `routing_oracle_regret`: On RouterBench or CodeRouterBench, simulate `always_strong`, `always_cheap`, `FrugalGPT/RouteLLM-style`, `MasRouter-style`, and `agent_attention_router` policies. Compute cumulative regret, cost-normalized success, and route-switch instability from offline outcome matrices.
3. `memory_negative_transfer_probe`: Run repeated task families with relevant, irrelevant, stale, and contradictory memories. Compute useful memory reuse rate, negative transfer count, and success/cost delta relative to no-memory.

## risks

- Literature claims may become stale quickly for 2026 routing papers; keep source URLs and checked dates.
- Published agent benchmarks often report success, but not enough process logs for cost/stability analysis.
- Some systems are frameworks rather than reproducible baselines; implementation choices can dominate results.
- The project can overfit to coding if SWE-bench/CodeRouterBench become the only practical evaluation path.
- Multi-agent baselines can look weak if budget is equalized too harshly, or too strong if cost is ignored.

## open_questions

- Should `agent_attention_agent` route over individual tools and verifiers in the first prototype, or only over higher-level agent modules?
- Which benchmark mix is the canonical minimum: code/search only, or code/search/web with one embodied task?
- Should the main baseline use ReAct exactly, SWE-agent-style ACI, or a repo-native single-agent runtime?
- How should negative transfer be labeled: automatic verifier failure, human annotation, or counterfactual no-memory comparison?
