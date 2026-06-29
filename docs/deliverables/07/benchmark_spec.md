# Benchmark Spec

## scope

This document defines the Phase 0-1 benchmark contract for Agent-Attention runtime evaluation. It covers task records, trajectory records, baseline comparability, metric computation, and a small seed suite in `experiments/tasks/phase0_seed_tasks.jsonl`.

The scope is deliberately log-first. A benchmark run is valid only if final success, cost, routing, memory, verifier, and halt metrics can be computed from the task schema and trajectory JSON without reading hidden prompts. The first supported trajectory source is the Subtask 06 lightweight `kind/payload` envelope; the target schema also aligns with Subtask 02 formal trajectory fields.

Out of scope:

- Subtask 08 implementation or dispatch.
- Editing `docs/decision_log.md`, `docs/project_status.md`, `src/`, or `tests/`.
- Claiming that the proposed runtime wins before baseline and ablation runs exist.
- Large external benchmark execution.

## claims

- [文献] ReAct, SWE-agent, API/ToolBench-style tool tasks, SWE-bench, RouterBench, Reflexion, Voyager, MoA, MasRouter, and Agent-as-a-Router motivate evaluating process, cost, routing, memory, verification, and failure recovery rather than final success alone.
- [原型] Subtask 06 trajectories already expose route score terms, selected modules, gates, memory reads/writes, verifier events, halt events, budget gate decisions, and final state snapshots in a lightweight JSON envelope.
- [实验] A seed suite with code, search, and mini-research tasks can smoke-test metric computability and baseline fairness before any large run.
- [猜想] The first credible Agent-Attention result will likely be matched-success efficiency, stability, or observability improvement rather than broad raw-success dominance.

## design

### minimal version

The minimal benchmark contains task families that exercise different module routes:

| Family | Purpose | Required oracle |
| --- | --- | --- |
| `code_agent_task` | Tests tool/code routing, verifier need, budget pressure, and repeated-action failures. | Executable test, synthetic runtime oracle, or explicit pass/fail label. |
| `search_agent_task` | Tests external-evidence need, citation correctness, source conflict handling, and unnecessary search cost. | Short answer plus required evidence/citation rubric. |
| `mini_research_task` | Tests taxonomy/ablation synthesis, memory reuse, critic/aggregator activation, and fair baseline reporting. | Rubric with required sections and prohibited unsupported claims. |

Each task record must include:

- `task_id`, `benchmark_id`, `task_family`, `split`, and `prompt`.
- `success_oracle` with `oracle_type`, `success_label`, and machine-checkable or rubric-checkable criteria.
- `budget` ceilings for steps, calls, cost units, tokens, verifier calls, and latency where available.
- `expected_route` as an oracle or soft label, used for route precision/regret only when marked `oracle_available`.
- `negative_transfer_probe` fields when a task intentionally includes stale, harmful, or irrelevant memory.
- `baseline_applicability` so every baseline is run on the same task only when the task interface is fair.

The minimal run matrix is:

| Policy | Required in Phase 0 seed scoring? | Notes |
| --- | --- | --- |
| `single_react_agent` | yes, when implemented | Same tools and budgets, no explicit route scores required but must log action/cost. |
| `fixed_workflow_agent` | yes, when implemented | Static planner -> executor -> critic/verifier. |
| `retrieval_memory_agent` | yes, when implemented | Same controller plus memory read/write. |
| `fixed_moa_agent` | yes, when implemented | Full candidate/aggregator cost must be logged. |
| `agent_attention_agent` | yes | Subtask 06 runtime is the Phase 0 prototype. |

### enhanced version

The enhanced benchmark adds:

- Paired no-memory and memory-enabled runs for every memory-transfer task.
- Offline route outcome matrices for selected synthetic tasks, enabling true `oracle_route_regret`.
- Stale and harmful memory injection for negative-transfer probes.
- Real executable code tasks with pytest results, patch diffs, and test pass/fail artifacts.
- Search tasks with frozen source snapshots to avoid recency drift.
- Cost frontiers: equal-budget view, unconstrained-cost view, and cost-normalized success view.
- Held-out task-family splits so memory writes from train runs cannot leak answers into eval tasks.

### counterexamples

- A dynamic router can lose to fixed workflow on homogeneous tasks where the same route is always optimal.
- Fixed MoA may improve raw answer quality while losing cost-normalized success.
- A no-cost router can improve success by over-activating expensive modules; that is not a clean architecture win.
- Memory may increase confidence and lower cost while causing wrong-route activation or stale-answer negative transfer.
- A verifier can raise cost without catching failures if its checklist is weak or not grounded in task oracles.

## interfaces

### task schema

The task object is specified in `docs/deliverables/07/task_schema.json`. Required oracle fields are:

```yaml
success_oracle:
  oracle_type: exact_match | regex | pytest | citation_rubric | human_rubric | synthetic_runtime | schema_check
  success_label: pass | fail | partial | unknown
  criteria:
    - criterion_id: string
      description: string
      weight: number
      required: boolean
  expected_answer: string | null
  expected_tests: [string]
  citation_requirements: object
```

### trajectory schema

The target trajectory envelope is specified in `docs/deliverables/07/trajectory_schema.json`. The canonical envelope is:

```yaml
schema_version: agent_attention.benchmark_trajectory.v0.1
run_id: string
task_id: string
benchmark_id: string
baseline_id: string
runtime_config: object
module_registry_snapshot: [object]
events: [trajectory_event]
final_answer: string
final_success_label: pass | fail | partial | unknown
failure_reason: string | null
metrics_summary: object
```

The Subtask 06 prototype currently emits a legacy-compatible list:

```yaml
- event_id: int
  step: int
  kind: start | memory_retrieval | memory_read | gates | route | budget_gate | module_execution | state_update | verifier_result | halt_gate | reflection | memory_write | finish
  payload: object
  timestamp: float
```

`scoring_script.py` accepts both forms.

### known deviations from 06 runtime

- 06 has no top-level `run_id`, `task_id`, `benchmark_id`, `baseline_id`, or `final_success_label`.
- 06 cost is an activation budget scalar from `budget_gate.module_cost` and state snapshots, not a full `cost_delta` object with tokens, tool price, verifier price, latency, and human-review minutes.
- 06 event IDs are numeric and run-local.
- 06 verifier is deterministic and heuristic, not a test/citation oracle.
- 06 route events do not include `oracle_best_module_id`, `oracle_regret`, or `proxy_regret`.
- 06 memory usefulness is seed/static and not updated after counterfactual reuse.
- 06 logs selected modules and budget-gate decisions, but not full action payload hashes for all actions.

### metric/API contract

The scoring API is:

```bash
python3 docs/deliverables/07/scoring_script.py <trajectory_path> [more_paths...] [--output experiments/metrics/summary.json]
```

The script returns one JSON object with:

- `runs`: per-trajectory summaries.
- `aggregate`: mean/sum metrics across supplied runs.
- `known_deviations`: fields inferred or unavailable under the legacy 06 envelope.

## experiments

1. `phase0_metric_computability_smoke`
   - Inputs: at least one existing 06 trajectory and the seed task file.
   - Command: `python3 docs/deliverables/07/scoring_script.py experiments/trajectories/runtime_demo.json`.
   - Pass condition: the script reports final, process, routing, memory, verifier, halt, and known-deviation sections without reading prompts.

2. `equal_budget_baseline_matrix`
   - Inputs: the same seed tasks for `single_react_agent`, `fixed_workflow_agent`, `retrieval_memory_agent`, `fixed_moa_agent`, and `agent_attention_agent`.
   - Controls: same task prompts, same tool availability, same max steps/calls/tokens/cost, same verifier availability.
   - Metrics: success, cost-normalized success, activation cost, module calls, repeated action ratio, premature halt, budget exhaustion, verifier catch, memory reuse, negative transfer, route entropy, oracle/proxy regret where available.

3. `memory_negative_transfer_probe`
   - Inputs: seed tasks with useful, irrelevant, stale, and harmful memories.
   - Controls: no-memory, useful-memory, stale-memory, and harmful-memory runs.
   - Metrics: useful memory reuse, harmful memory reads, negative transfer cases, verifier catch of memory harm, success/cost delta versus no-memory.

## risks

- The seed suite is too small to estimate effect size; it is only for schema and metric readiness.
- Legacy trajectory support can hide missing instrumentation if known deviations are ignored.
- Human-rubric search/research tasks need reviewer calibration before formal claims.
- Proxy regret is weaker than true oracle regret and must not be mixed with offline oracle regret.
- Equal-budget comparisons can penalize MoA or fixed workflow if their natural operating point uses more parallel calls; report equal-budget and cost-frontier views.
- Memory tasks can leak benchmark answers if train/eval split and provenance are not enforced.

## open_questions

- What is the official Phase 1 task count: 20, 30, or 50 seed-plus-real tasks?
- Should the canonical Phase 1 suite include web tasks, or remain code/search/mini-research until routing logs stabilize?
- What price model should convert tokens, tool calls, verifier calls, latency, and human review into a single cost-normalized denominator?
- Should unknown memory usefulness count against retrieval precision, or be reported only as coverage debt?
- Who labels citation correctness and negative transfer when executable verifiers are unavailable?
- Should 06 be patched later to emit full target envelopes, or should synthesis keep a normalizer layer for legacy logs?
