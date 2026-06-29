# Baseline Specs

## scope

This document defines the first fair baseline set for Agent-Attention Phase 0-1 experiments. It covers the required systems: `single_react_agent`, `fixed_workflow_agent`, `full_history_agent`, `retrieval_memory_agent`, `moa_style_agent`, and `agent_attention_agent`.

The scope is design-level and executable-contract level. It does not implement runners, modify `src/`, modify `tests/`, or claim that the proposed system wins. All baselines must run the same tasks from `experiments/tasks/phase0_seed_tasks.jsonl` or later task files, under matched budget ceilings from `docs/deliverables/07/task_schema.json`, and emit trajectories scoreable by `docs/deliverables/07/scoring_script.py`.

## claims

- [文献] ReAct-style loops are strong single-controller baselines because they expose thought/action/observation cycles and can use the same tools as routed systems.
- [文献] Fixed planner/executor/critic workflows are practical comparators from HuggingGPT/MetaGPT-style systems and can outperform routing on homogeneous tasks.
- [文献] Full-history prompting is a common context-management baseline; it tests whether structured state and compact memory outperform simple transcript stuffing.
- [文献] Retrieval memory and Reflexion/Voyager-style episodic memory can improve transfer, so the proposed system must be separated from a single-agent-plus-memory explanation.
- [文献] MoA-style candidate generation and aggregation can improve open-ended output quality, but it is not sparse routing and must be charged for all candidate and aggregator calls.
- [原型] Subtask 06 legacy trajectories already expose route, gate, budget, memory, verifier, halt, and finish events that can score the proposed prototype.
- [实验] The Subtask 07 scoring API can compute success, activation cost, module calls, repeated ratio, premature halt, memory reuse, negative transfer, verifier catch, route entropy, and regret fields when present.
- [猜想] The first credible positive result is likely cost-normalized success, stability, or observability under matched success, not broad raw-success dominance.

## design

### minimal version

All baselines share:

- Same task prompt, task family, split, success oracle, memory fixture, and negative-transfer probe from the task record.
- Same budget ceilings: `max_steps`, `max_module_calls`, `max_tool_calls`, `max_verifier_calls`, `max_tokens`, `max_latency_ms`, and `max_activation_cost`.
- Same allowed external tools where the baseline can fairly express them.
- Same final success oracle and same scoring script.
- Same target trajectory envelope where possible; legacy Subtask 06 `kind/payload` lists are accepted only with known deviations.
- Same random seed or deterministic replay marker for stochastic controllers.

| Baseline | Question Answered | Allowed Modules/Tools | Routing Policy | Memory Policy | Verifier Policy | Halt Policy |
| --- | --- | --- | --- | --- | --- | --- |
| `single_react_agent` | Does one strong recurrent agent already solve the task cheaply? | Agent controller plus task tools: code/search/verifier if available. | None; next action chosen inside one loop. Log static route placeholder when possible. | None for default run. No cross-task memory. | Same verifier budget as proposed, called by the agent or at final answer when required by task. | Agent decides stop, but must log halt reason and remaining budget. |
| `fixed_workflow_agent` | Does a hand-written workflow beat dynamic routing? | Planner, executor/tool user, critic/verifier, summarizer/aggregator. | Static stage order: planner -> executor -> critic -> summarizer. | None by default; fixed context passed between stages. | Critic/verifier stage always runs unless budget blocks it. | Stop after workflow completion or budget exhaustion. |
| `full_history_agent` | Is full transcript context enough without structured state/memory? | Single controller and same task tools. | None; all prior events are appended to context. | Full in-run history only; no cross-task memory. | Same verifier access as `single_react_agent`; final verifier required on high-risk or executable tasks. | Stop from agent decision or max context/budget. |
| `retrieval_memory_agent` | Are gains explained by memory rather than routing? | Single controller, task tools, memory read/write module. | None except fixed memory retrieval before each step or before first step. | Read/write behavior memory under Subtask 04 policy; run no-memory paired control. | Same verifier access as `single_react_agent`. | Stop from agent decision; memory cannot override verifier-required halt. |
| `moa_style_agent` | Does fixed multi-agent aggregation outperform sparse routing when charged fairly? | Fixed N proposer agents, optional critic/ranker, aggregator, verifier. | Static all-proposer activation followed by aggregation. | None in minimal run; optional memory only in enhanced matched-memory variant. | Verifier runs after aggregation when task requires it or under matched final-verifier policy. | Stop after aggregation plus verifier or budget exhaustion. |
| `agent_attention_agent` | Does sparse module routing over agents/tools/memory/verifier/halt improve cost, stability, or transfer? | Memory, code/search agents, critic, aggregator, verifier, halt/budget gates. | Rule, lexical, embedding, learned, or adaptive top-k variants. Default Phase 0 is lexical adaptive/top-k with logged score terms. | Behavior KV plus typed memory, with usefulness and negative-transfer labels. | Conditional verifier gate by risk, uncertainty, irreversible action, failure signal, or halt attempt. | Halt gate with verifier-required status and budget snapshot. |

### enhanced version

Enhanced baseline reporting adds:

- Equal-budget view: every system obeys the task budget exactly.
- Cost-frontier view: vary cost ceilings to show success versus activation cost, especially for MoA and full-history systems.
- Matched-memory view: `retrieval_memory_agent` and `agent_attention_agent` use the same memory corpus and read/write policy, while memory-disabled variants are paired.
- Matched-verifier view: compare default verifier policy, no verifier, and final-only verifier for every system that can express it.
- Oracle-route view: when `expected_route.oracle_available` is true, report route precision or oracle/proxy regret separately from final success.
- Legacy-normalized view: wrap Subtask 06 list trajectories into the target envelope for reporting, but preserve deviations.

### counterexamples

- `fixed_workflow_agent` should beat routing on tasks where the same static route is always optimal and router overhead has no value.
- `full_history_agent` may win on short tasks because no summarization or memory-retrieval error is introduced.
- `retrieval_memory_agent` may match the proposed system when memory is the only useful extra computation and routing decisions are obvious.
- `moa_style_agent` may improve raw rubric quality on open-ended mini-research tasks, while losing cost-normalized success.
- `agent_attention_agent` may fail on stale-memory tasks if memory bonus overwhelms risk, on paraphrased tasks if lexical routing misses intent, or under tight budgets if useful verifier calls are blocked.

### baseline fairness contract

| Field | Requirement |
| --- | --- |
| Task set | Use identical `task_id` set and task split for all applicable baselines. Report exclusions from `baseline_applicability`. |
| Budget | Use task-level ceilings. If a baseline naturally needs more parallel calls, report both equal-budget and cost-frontier results. |
| Tool access | Do not deny a baseline a tool that the proposed system can use, unless the baseline definition explicitly lacks that capability and the exclusion is named. |
| Model strength | Use the same base model or matched capability tier for all agents. If MoA uses multiple models, charge all calls and report the model mix. |
| Prompt/context | Keep task instructions and success criteria equivalent. Full-history may receive full in-run history but not cross-task memory. |
| Memory | Memory-enabled baselines use the same memory corpus, provenance, quarantine labels, and train/test split rules. |
| Verifier | Verifier access and budget must be identical unless the ablation row changes verifier policy. |
| Logging | Every baseline must emit final status, cost, calls, verifier status, halt reason, and enough selected action/module data for scoring. |

### baseline-specific logging and fairness risks

| Baseline | Same Task/Budget Rule | Required Trajectory Logging | Main Fairness Risks |
| --- | --- | --- | --- |
| `single_react_agent` | Run every applicable task with the same task-level ceilings. Tool calls count against the same module/tool budget. | Thought/action/observation or action summaries, tool calls, verifier calls, cost, halt reason, final label, repeated action hash or module proxy. | Weak prompting can make the baseline too easy to beat; hidden internal action choices can hide repeated loops unless logged. |
| `fixed_workflow_agent` | Each stage must fit inside the same total budget, not receive per-stage budgets in addition to the task budget. | Stage id, role/module id, stage output summary, tool calls, critic/verifier result, cost per stage, final halt. | Static stages can be penalized if the budget is too small for the workflow; report cost-frontier results too. |
| `full_history_agent` | Full-history retransmission counts against token/context cost on every step. | Context size or truncation flag, action summaries, tool/verifier calls, cost, halt reason, final label. | Can look cheap if retransmitted context tokens are not counted; can look weak if context truncation is silent. |
| `retrieval_memory_agent` | Uses the same task budget plus the same memory corpus and memory retrieval cost accounting as proposed. | Memory reads/writes, memory usefulness labels, tool/verifier calls, cost, halt reason, final label. | If memory corpus differs from proposed, gains cannot be attributed; success-only memory can hide failure-memory benefits. |
| `moa_style_agent` | All proposer, critic/ranker, aggregator, and verifier calls count against the same budget and latency report. | Proposer ids, candidate outputs or hashes, rank/fuse decisions, aggregator output, verifier result, per-agent cost. | Equal-budget settings may constrain MoA's natural operating point; unconstrained runs must still report full cost. |
| `agent_attention_agent` | Uses identical task budgets; every routed module, memory call, verifier call, and rejected budget decision is charged or logged. | Route candidates, selected modules, score terms, gate decisions, memory reads/writes, verifier result, halt reason, known deviations. | Proposed can appear better if baselines lack equivalent tools, if legacy cost is treated as real token/API cost, or if missing regret is ignored. |

## interfaces

### baseline config

```yaml
baseline_config:
  baseline_id: single_react_agent | fixed_workflow_agent | full_history_agent | retrieval_memory_agent | moa_style_agent | agent_attention_agent
  family: single_agent | fixed_workflow | full_history | retrieval_memory | moa | agent_attention
  controller_policy: prompt | program | static_workflow | static_all_agents | heuristic_router | learned_router
  routing_policy: none | static | rule | lexical | embedding | learned | adaptive
  module_pool:
    - agent
    - tool
    - memory
    - verifier
    - aggregator
    - halt
  allowed_module_ids: [string]
  activation_budget:
    max_steps: int
    max_module_calls: int
    max_tool_calls: int
    max_verifier_calls: int
    max_tokens: int
    max_latency_ms: int
    max_activation_cost: number
  memory_policy:
    mode: none | full_in_run_history | read_only | read_write | success_only_write | behavior_kv
    corpus_id: string | null
    top_n: int | null
    write_policy: none | all_runs | success_only | success_plus_failure
    quarantine_aware: boolean
  verifier_policy:
    mode: none | final_only | conditional | always_on
    required_on_halt: boolean
    max_verifier_calls: int
  trajectory_logging_requirements:
    target_envelope_required: boolean
    legacy_06_allowed: boolean
    required_fields:
      - final_success_label
      - failure_reason
      - selected_modules
      - action_payload_hash
      - cost_delta_or_legacy_module_cost
      - verifier_result
      - halt_reason
      - memory_usefulness_label
      - route_candidates_when_available
  fairness_risks: [string]
```

### trajectory alignment

Baselines should write `docs/deliverables/07/trajectory_schema.json` target envelopes:

```yaml
schema_version: agent_attention.benchmark_trajectory.v0.1
run_id: string
task_id: string
benchmark_id: string
baseline_id: string
runtime_config:
  baseline_config_ref: string
  budget: object
  seed: int | null
module_registry_snapshot: [object]
events: [trajectory_event]
final_answer: string
final_success_label: pass | fail | partial | unknown
failure_reason: string | null
metrics_summary: object
```

Legacy Subtask 06 event lists are allowed for `agent_attention_agent` Phase 0 smoke scoring only. Known deviations that must be surfaced in any result table:

- `legacy_06_event_list_no_top_level_run_metadata`
- `legacy_06_uses_scalar_activation_cost_not_full_cost_delta`
- `legacy_06_lacks_task_schema_join`
- `legacy_06_lacks_oracle_route_regret`
- `oracle_route_regret_unavailable`
- `proxy_route_regret_unavailable`

### scoring fields

The result template must be fillable from `scoring_script.py`:

- `final.task_success`, `final.success_label`, `final.failure_reason`
- `process.activation_cost`, `process.cost_normalized_success`, `process.module_calls`, `process.verifier_calls`
- `process.repeated_action_ratio`, `process.invalid_tool_call_ratio`, `process.loop_stuck`, `process.budget_exhaustion`, `process.step_exhaustion`, `process.premature_halt`
- `routing.route_entropy`, `routing.route_reject_rate`, `routing.selected_route_score_mean`, `routing.selected_route_cost_mean`, `routing.oracle_route_regret_mean`, `routing.proxy_route_regret_mean`
- `memory.memory_reads`, `memory.useful_memory_reuse_rate`, `memory.negative_transfer_cases`
- `verifier.verifier_catch_rate`

## experiments

1. `equal_budget_phase0_baseline_matrix`
   - Run all six baselines on the four Phase 0 seed tasks when applicable.
   - Controls: same model tier, same tools, same memory fixtures, same budget ceilings, same success oracles.
   - Metrics: success, cost-normalized success, activation cost, latency when available, module calls, repeated ratio, premature halt, verifier catch, memory reuse, negative transfer, route entropy/regret where available.
   - Expected interpretation: proposed wins only if it improves cost/stability or success under matched budget without hiding legacy deviations.

2. `cost_frontier_moa_and_full_history`
   - Sweep activation budgets for `full_history_agent`, `moa_style_agent`, and `agent_attention_agent`.
   - Controls: same task set and verifier policy; report equal-budget row plus unconstrained or frontier rows.
   - Metrics: success versus activation cost, latency, module calls, cost-normalized success, premature halt, budget exhaustion.
   - Counterexample target: MoA may dominate raw success at high cost; full-history may dominate short easy tasks.

3. `memory_explanation_control`
   - Compare `single_react_agent`, `retrieval_memory_agent`, `agent_attention_agent:no_memory`, and full `agent_attention_agent`.
   - Controls: same memory corpus, same top-n where memory is enabled, same harmful/stale memory injections.
   - Metrics: useful reuse, negative transfer, wrong-route activation, verifier catch, success/cost delta versus no-memory.

## risks

- Baselines can be made artificially weak through poor prompts or missing tools; maintain prompt parity and tool parity.
- Equal-budget MoA can be unfair if the only realistic MoA setting exceeds the seed budget; therefore report cost frontiers too.
- Full-history baselines may exceed context windows on later tasks; log truncation and resulting missing history.
- Legacy Subtask 06 trajectories lack top-level run metadata and full cost deltas, so Phase 0 comparisons are approximate.
- Route regret is unavailable unless target envelopes include oracle/proxy route fields or offline outcome matrices.
- Memory-enabled baselines can leak answers across train/test if provenance and split filters are not enforced.

## open_questions

- Should `full_history_agent` and `moa_style_agent` be added to `task_schema.json.baseline_applicability` in a later schema revision, or mapped to existing applicability keys during ingestion?
- What is the official Phase 1 task count: 20, 30, or 50 tasks per family?
- What shared model tier and prompt budget should be used for all baselines?
- Should full-history cost include only new prompt tokens or the full retransmitted transcript each step?
- Should MoA be configured as parallel proposers plus one aggregator, or layered proposer/aggregator rounds?
- Who labels memory usefulness and negative transfer when executable feedback is unavailable?
