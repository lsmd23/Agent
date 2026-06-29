# Must-Read Papers

## scope

This is a prioritized reading list for the main Agent-Attention project. It is not a bibliography dump: each item states why it matters, what to extract, and what not to overclaim. The list emphasizes works that should shape baselines, interfaces, metrics, and experiments.

## claims

- [文献] The minimum must-read set should cover five anchor comparators: ReAct, HuggingGPT, Reflexion, Voyager, and Mixture-of-Agents.
- [文献] Routing papers are now important enough to be first-class, especially MasRouter and Agent-as-a-Router, because they directly address cost-aware selection and feedback-grounded routing.
- [文献] Benchmarks must be read alongside systems; otherwise the project will inherit success metrics that cannot explain cost, instability, or negative transfer.
- [猜想] A small set of deeply read papers will be more useful than a broad unsorted agent bibliography, because later subtasks need schemas and ablations.

## design

### minimal baseline set

Read these first to implement the initial baselines:

1. ReAct: single recurrent loop baseline.
2. HuggingGPT or MetaGPT: fixed workflow/model-pool baseline.
3. Mixture-of-Agents plus LLM-Blender: multi-output aggregation baseline.
4. SWE-agent: practical coding-agent baseline if the benchmark includes repositories.

### enhanced map

Read these next to implement Agent-Attention mechanisms:

| Priority | Work | Extract | Do Not Overclaim |
| -------- | ---- | ------- | ---------------- |
| P0 | ReAct | Thought/action/observation trajectory format; single-loop baseline. | Do not call every controller a router. |
| P0 | Reflexion | Verbal feedback and episodic memory update. | Reflections can be wrong; require verifier or outcome logs. |
| P0 | Voyager | Executable skill library, curriculum, iterative repair. | Minecraft transfer does not imply general cross-domain transfer. |
| P0 | Mixture-of-Agents | Layered aggregation and cost of multi-agent calls. | MoA is not sparse routing by default. |
| P0 | HuggingGPT | LLM controller over model/tool pool. | Model selection by description is not enough for learned routing. |
| P1 | FrugalGPT | Cascades, thresholds, cost-quality frontier. | Mostly one-shot model/API routing. |
| P1 | RouteLLM | Preference-trained router and transfer across model pairs. | Not a long-horizon agent. |
| P1 | RouterBench | Offline routing evaluation and oracle outcomes. | Static route matrices omit trajectory adaptation. |
| P1 | MasRouter | Routing collaboration mode, roles, and LLMs in MAS. | MAS routing is not yet unified module routing. |
| P1 | Agent-as-a-Router | Context-Action-Feedback router with verifier/memory and CodeRouterBench. | As of 2026-06-26 it is a very recent comparator; reproduction risk is high. |
| P1 | Toolformer | Tool-call supervision and self-supervised tool-use data. | Tool-call training differs from runtime module activation. |
| P1 | Gorilla / APIBench | API retrieval and accurate call generation. | API correctness is narrower than task success. |
| P1 | ToolLLM / ToolBench | Large tool-use data and multi-tool solution paths. | Synthetic data may not expose realistic instability. |
| P1 | Memory Networks | Read/write external memory abstraction. | Pre-LLM memory model is conceptual, not directly comparable. |
| P1 | MemGPT | Memory tiering and virtual context. | Context memory is not automatically behavior memory. |
| P1 | Generative Agents | Observation, retrieval, reflection, planning over memories. | Believability is not the same as task reliability. |
| P1 | LATS | Search over reasoning/action/planning with reflections. | MCTS-style search may be too costly for the target budget. |
| P1 | AutoGen | Conversation programming for multi-agent workflows. | Framework flexibility is not a measured routing policy. |
| P1 | SWE-agent | ACI design for coding agents and repo interaction. | Interface improvements can dominate architecture comparisons. |
| P2 | WebShop | Grounded web navigation and action trajectories. | Need extra logs for route decisions and cost. |
| P2 | ALFWorld | Abstract-to-grounded long-horizon embodied tasks. | Might be outside the first prototype scope. |
| P2 | SWE-bench | Real GitHub issue benchmark with test validation. | Full benchmark can be expensive; use Lite/verified subsets first. |
| P2 | AgentBench | Broad multi-environment agent evaluation. | Breadth can blur which module failed. |
| P2 | GAIA | Mixed assistant tasks with tool/browsing needs. | Answer-only scoring needs trajectory instrumentation. |

### counterexamples

- A paper reporting higher benchmark score with more calls is not evidence for Agent-Attention unless cost and stability are logged.
- A memory paper that retrieves facts does not prove behavior memory will transfer.
- A routing benchmark with one-shot prompts does not prove long-horizon routing works.
- A multi-agent framework with configurable conversations is not a baseline until the conversation policy is fixed and logged.

## interfaces

Reading-note schema to reuse in synthesis:

```yaml
reading_note:
  work_id: string
  source_url: string
  year: int
  evidence_type: literature | official_code | benchmark_page | experiment | conjecture
  category_ids: [string]
  mechanism:
    controller: string
    routing_policy: string
    memory_policy: string
    feedback_update: string
    aggregation: string
    verifier_or_halt: string
  baseline_fit:
    baseline_id: string
    implementation_risk: low | medium | high
  benchmark_fit:
    benchmark_id: string
    trajectory_fields_available: [string]
    missing_logs: [string]
  project_delta: string
  counterexample: string
```

Baseline/category/benchmark minimum fields:

```yaml
baseline_fields: [id, family, representative_work, route_policy, memory_policy, feedback_update, required_logs]
category_fields: [id, definition, inclusion_criteria, exclusion_criteria, examples, counterexamples]
benchmark_fields: [id, task_family, success_metric, process_metrics_from_log, executable_feedback, oracle_route_possible]
```

## experiments

1. `paper_to_schema_validation`: For each P0/P1 paper, create one `reading_note` record. The literature task is complete only if every required field is filled without inventing unavailable metrics.
2. `must_read_reproduction_triage`: For ReAct, SWE-agent, MoA, RouteLLM, MasRouter, and Agent-as-a-Router, label reproduction risk as low/medium/high by checking code availability, task dependencies, and whether offline evaluation is possible.
3. `source_staleness_check`: Re-run source checks for 2025-2026 routing papers before final synthesis and record `checked_at`.

## risks

- Very recent routing papers may change code/data availability after this map.
- Some benchmark leaderboards move faster than papers; avoid using leaderboard rank as a stable claim.
- Reading papers without implementing minimal logs may create abstract categories that later cannot be measured.
- Official code can differ from paper pseudocode; reproduction notes should record the exact commit when implementation starts.

## open_questions

- Which P0/P1 papers should be reproduced versus only cited as conceptual baselines?
- Should CodeRouterBench be adopted immediately despite its 2026 freshness, or held as a secondary evaluation until stable?
- Does the main project need an official `reading_note` YAML/JSON file in addition to Markdown?
- Who owns source freshness checks during synthesis: literature subtask or benchmark subtask?
