# Master Research Outline

## scope

This document synthesizes Subtasks 01-08 into a master research report outline for the Agent-Attention Architecture project. It covers the research question, formal model, runtime, evaluation, baselines, known evidence, limitations, and next experiments.

This is not a final results paper. Phase 0 has validated a deterministic toy runtime and metric computability, but baseline and ablation experiments have not yet been executed.

## claims

| Claim | Evidence type | Current support |
| --- | --- | --- |
| Fixed `plan -> act -> observe -> update` loops are strong baselines, not strawmen. | 文献 | ReAct, SWE-agent, Reflexion, Voyager, HuggingGPT, MetaGPT, MoA, and routing literature are mapped in Subtask 01. |
| Agent-Attention can be formalized as logged sparse routing over modules, memory, verifier, aggregation, and halt gates. | 原型 | Subtask 02 schemas plus Subtasks 03-05 interface designs compile to the Subtask 06 toy runtime. |
| Phase 0 instrumentation is sufficient for first-pass observability. | 实验 | `python3 -m unittest discover -s tests` passes 8 tests; demo trajectories contain routing, gates, memory, verifier, halt, reflection, and budget events. |
| The current runtime can compute a useful Phase 0 metric subset. | 实验 | Subtask 07 scoring script scores 5 legacy trajectories and emits known deviations. |
| Agent-Attention improves efficiency, stability, or transfer over baselines. | 猜想 | Must wait for Phase 1-4 baseline, memory, textual-backprop, and learned-routing experiments. |

## design

### minimal version

Report structure:

1. Motivation
   - Why fixed workflows are inspectable but brittle.
   - Why "more agents" is not the hypothesis.
   - Research target: efficiency, stability, transfer, and inspectable trajectories.

2. Related Work
   - Loop and acting: ReAct, SWE-agent, LATS.
   - Tool use: Toolformer, HuggingGPT, Gorilla/APIBench, ToolBench.
   - Memory and self-improvement: Memory Networks, Reflexion, Voyager, MemGPT, Generative Agents.
   - Multi-agent aggregation: MoA, LLM-Blender, AutoGen, MetaGPT.
   - Routing and routing benchmarks: FrugalGPT, RouteLLM, RouterBench, MasRouter, Agent-as-a-Router.
   - Evaluation: WebShop, ALFWorld, SWE-bench, AgentBench, GAIA.

3. Formal Model
   - State with immutable `goal` residual anchor.
   - Module pool with kind, capability, schema, cost, latency, risk, reliability, and history features.
   - Query/key/value mapping as concrete runtime fields.
   - Router score: semantic match + reliability + historical success - cost - latency - risk - repetition + memory bonus.
   - Gates: tool, search, memory, verifier, halt, safety, budget.
   - Memory KV-cache and textual backpropagation as auditable state transitions.

4. Agent-Attention Runtime
   - Deterministic toy runtime in `src/agent_attention_runtime.py`.
   - CLI, toggles, event kinds, score terms, gate events, memory audit, verifier and halt payloads.
   - Known deviations from full schema.

5. Router and Gates
   - Rule, lexical, embedding, learned router levels.
   - Phase 0-1 default: auditable lexical heuristic.
   - Gate metrics and failure modes.

6. Memory KV-cache
   - Typed memory profiles under one schema.
   - Behavior KV and failure memory encoding.
   - Memory bonus cap/floor, quarantine, decay, and negative-transfer labels.

7. Textual Backpropagation
   - Failure -> attribution -> local textual gradient -> proposed update -> replay/held-out validation -> accept/reject/quarantine/rollback.
   - Update targets and rollback discipline.

8. Experimental Setup
   - Phase 0 seed tasks and legacy trajectory scoring.
   - Target task and trajectory schemas.
   - Metrics: success, cost, process, routing, memory, verifier, negative transfer.

9. Baselines and Ablations
   - Single ReAct, fixed workflow, full-history, retrieval-memory, MoA-style, proposed Agent-Attention.
   - Single-variable ablations.
   - Equal-budget and cost-frontier reporting.

10. Results
   - Phase 0 only: instrumentation and scoring smoke results.
   - Placeholder for Phase 1-4 quantitative comparisons.

11. Failure Analysis
   - Bad route, bad memory, bad module output, bad aggregation, verifier miss/false alarm, premature halt, budget exhausted, loop stuck, external tool failure, schema/logging gap.

12. Limitations
   - Toy runtime, scalar activation cost, deterministic verifier, legacy event envelope, missing baseline runners, missing oracle regret.

13. Next Steps
   - Execute Phase 1 baseline matrix.
   - Patch target trajectory envelope if needed.
   - Run memory and textual-backprop ablations.
   - Collect trajectories for learned routing.

### enhanced version

The mature report should include:

- Phase 1 equal-budget baseline results.
- Phase 2 memory ablations with no-memory counterfactuals and negative-transfer probes.
- Phase 3 textual-backprop replay and held-out validation.
- Phase 4 learned routing comparison against lexical, embedding, bandit, and imitation routers.
- Cost-frontier curves and route-regret tables.
- Case studies with complete trajectory snippets and failure attribution.

### counterexamples

- A fixed workflow may beat the router on homogeneous tasks.
- A full-history agent may beat structured memory on short tasks.
- Retrieval-memory may explain most gains if routing choices are obvious.
- MoA may win raw quality while losing cost-normalized success.
- Agent-Attention may fail under stale memory, lexical paraphrase mismatch, or budget-blocked verifier calls.

## interfaces

Primary report inputs:

- Literature map: `docs/deliverables/01/*`
- Formal model: `docs/deliverables/02/*`
- Router/gates: `docs/deliverables/03/*`
- Memory: `docs/deliverables/04/*`
- Textual backprop: `docs/deliverables/05/*`
- Runtime: `docs/deliverables/06/runtime_report.md`
- Benchmark/metrics: `docs/deliverables/07/*`
- Baselines/ablations: `docs/deliverables/08/*`
- Decisions: `docs/decision_log.md`

Canonical report artifact should link every empirical claim to one of:

- source literature
- runtime implementation/test
- trajectory/scoring output
- planned experiment
- explicit conjecture

## experiments

1. `phase1_equal_budget_baseline_matrix`
   - Run the six baseline families on `experiments/tasks/phase0_seed_tasks.jsonl`.
   - Score with `docs/deliverables/07/scoring_script.py`.
   - Report success, activation cost, cost-normalized success, module calls, repeated ratio, premature halt, verifier catch, memory reuse, negative transfer, and route entropy.

2. `phase2_memory_transfer_probe`
   - Compare no memory, read-only memory, success-only writes, and success plus failure memory on repeated code/search tasks.
   - Measure useful reuse, harmful reads, cross-task transfer gain, stale memory rate, and negative transfer.

3. `phase3_textual_backprop_replay`
   - Generate local textual gradients for failed trajectories and replay with accept/reject/quarantine rules.
   - Measure replay improvement, held-out regression, rollback frequency, false blame, and repeated failure reduction.

## risks

- Baseline runners are not implemented yet, so no architecture-improvement claim is supported.
- Legacy Phase 0 trajectories lack top-level task/run metadata and full cost deltas.
- Toy verifier does not prove real correctness.
- Memory usefulness labels are still approximate.
- Learned routing needs more trajectories and oracle/proxy route labels than currently exist.

## open_questions

- Should the next implementation patch emit full target trajectory envelopes before baseline runners?
- What is the official Phase 1 task count per family: 20, 30, or 50?
- What total-cost model should combine tokens, tool calls, verifier calls, latency, retries, and human review?
- Should embedding routing be introduced in Phase 1 as an ablation or delayed until Phase 4?
- Who labels citation correctness and ambiguous negative transfer before executable verifiers exist?
