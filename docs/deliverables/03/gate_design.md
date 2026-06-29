# Gate Design

## scope

This document specifies the Phase 0-1 gates used by the Agent-Attention router: `ToolGate`, `SearchGate`, `MemoryGate`, `VerifierGate`, `HaltGate`, `SafetyGate`, and `BudgetGate`. Gates are cheap decision functions that constrain routing, trigger required modules, or stop execution.

Each gate includes inputs, outputs, thresholds, trajectory event fields, failure modes, and independent metrics. All fields align with Subtask 02 state, module, memory, trajectory, failure, and halt schemas.

## claims

- [文献] Toolformer and tool-use benchmarks motivate explicit tool-call gating and invalid-call metrics.
- [文献] Reflexion, Voyager, and memory-network style systems motivate separate memory read/write gates and negative-transfer labels.
- [文献] FrugalGPT, RouteLLM, RouterBench, MasRouter, and Agent-as-a-Router motivate budget-aware and regret-aware routing rather than always using the strongest module.
- [原型] Subtask 02 already requires verifier, halt, budget, memory, and route events to be computable from JSON logs.
- [猜想] Gate accuracy must be measured independently; otherwise final success hides false positives that waste cost and false negatives that cause failures.

## design

### minimal version

All gates return:

```yaml
gate_decision:
  gate_id: string
  gate_type: ToolGate | SearchGate | MemoryGate | VerifierGate | HaltGate | SafetyGate | BudgetGate
  decision: open | closed | require | block | stop | continue
  confidence: float
  threshold: float
  reasons: [string]
  required_modules: [module_id]
  blocked_modules: [module_id]
```

Gate decisions are deterministic in Phase 0-1. They run before final module selection, except `HaltGate`, which runs after aggregation and verification status updates.

### enhanced version

Enhanced gates may use calibration curves, learned classifiers, route regret, no-memory counterfactuals, or per-task-family thresholds. Enhanced gates must keep the same output contract and log model/policy version when learned.

### counterexamples

- `VerifierGate` always open can increase cost and latency while adding weak or redundant checks.
- `HaltGate` with a low threshold can stop with plausible language but unsatisfied success criteria.
- `SearchGate` opened by any recency word can waste cost on stable facts or local-code tasks.
- `MemoryGate` can cause negative transfer when stale memories share vocabulary but not causal structure.
- `BudgetGate` can over-suppress recovery steps after an early mistake, converting recoverable failures into final failures.

### gate specifications

| Gate | Inputs | Output | Default thresholds | Trajectory event fields | Failure modes | Independent metrics |
| --- | --- | --- | --- | --- | --- | --- |
| `ToolGate` | `state.goal`, `active_subgoal`, `uncertainties`, `failure_signals`, candidate tool schemas, `budget_status` | `open` with allowed tool modules, or `closed` | open if `action_need in {external_execution, file_inspect, test_run, api_call}` or missing evidence needs executable observation; close if answer can be derived from current state and no tool uncertainty severity >= medium | `event_type: route_decision`, `action_type: no_op`, `candidate_modules`, `selected_modules`, `route_scores`, `error_type`, `cost_delta.tool_calls` later | false positive wastes tool calls; false negative causes hallucination or unsupported answer; schema mismatch; repeated invalid calls | tool gate precision/recall, invalid tool call ratio, cost saved, errors introduced, tool false-negative failure rate |
| `SearchGate` | `state.goal`, recency markers, citation/evidence need, known-source confidence, web/search module registry, budget | `open` with search/retrieval modules, or `closed` | open if query asks latest/current/legal/price/news/source quotes, or `evidence_needed` is external and confidence < 0.70; close for local repo/code-only tasks unless docs are missing | `event_type: route_decision`, `selected_modules`, `route_scores.semantic_match`, `cost_delta.tool_calls`, `latency_ms`, `evidence_refs` from search result events | unnecessary search cost; stale source selection; missing required current info; source over-trust; search loop | search precision/recall, citation correctness, search cost per successful task, stale-source rate, search false-negative error count |
| `MemoryGate` | `memory_candidates`, retrieval scores, memory type, reuse outcomes, task split, failure signals, negative-transfer labels | `open_read`, `open_write`, `closed`, or `block_memory_id` | read if top memory score >= 0.65 and harmful rate <= 0.20; write on success/failure/uncertainty/negative_transfer with evidence refs; block if train/test leakage or harmful_count > useful_count with similar route | `event_type: memory_read | memory_write | route_decision`, `memory_ids_read`, `memory_ids_written`, `memory_usefulness_label`, `error_type: negative_transfer`, `evidence_refs` | stale memory; irrelevant lexical match; benchmark leakage; harmful skill reuse; write amplification | memory retrieval precision, useful memory reuse rate, harmful memory read rate, negative transfer cases, write usefulness after reuse |
| `VerifierGate` | risk score, uncertainty severity, halt attempt, executable change flag, previous failures, benchmark requirements, budget | `require` verifier modules, or `closed` | require if halt attempt, risk >= 0.50, uncertainty severity >= medium, irreversible/executable change, contradiction, or previous failure signal severity >= warning; close for low-risk intermediate steps when BudgetGate blocks optional verifier | `event_type: verifier_result`, `verifier_result`, `cost_delta.verifier_calls`, `failure_signal.failure_type: verifier_failed`, `correction_of_event_ids` | verifier always on raises cost; weak verifier false pass; false fail causes loops; verifier unavailable | verifier catch rate, false pass rate, false fail rate, cost per caught error, correction success after verifier fail |
| `HaltGate` | `state.goal.success_criteria`, `verification_status`, `blocking_uncertainties`, active failures, budget snapshot, latest aggregate | `stop` or `continue` with `halt_reason` | stop only if success criteria pass, no blocking uncertainty, no active blocking/fatal failure, and verifier pass/not_required; continue if verifier required, needs more work, blocked uncertainty, or recoverable failure | `event_type: halt`, `action_type: halt`, full `halt_decision`, `success_signal`, `verifier_result`, `budget_snapshot`, `error_type: premature_halt` when detected | premature halt; endless continue; budget-exhausted halt misclassified as success; verifier-required halt skipped | premature stopping rate, unnecessary continuation count, final success calibration, halt false positive/negative, budget-exhausted outcome rate |
| `SafetyGate` | risk labels, irreversible action flag, external side-effect flag, human-review policy, user constraints, failure signals | `require_human`, `block`, or `allow` | require human if action is irreversible or risk >= 0.80; block if violates explicit constraints or safety policy; allow low-risk read-only actions | `event_type: route_decision | failure_update`, `error_type`, `cost_delta.human_review_minutes`, `failure_signal.failure_type`, blocked module IDs | over-blocking safe work; under-blocking side effects; hidden human-review cost; unclear user confirmation state | safety block precision, human-review minutes, risky-action false negative count, accepted-risk outcomes |
| `BudgetGate` | remaining tokens/time/tool/verifier/retry/monetary/human-review budget, expected route cost, recovery value, risk | `allow`, `downgrade`, or `block_high_cost` | block high-cost route when expected cost > 30% remaining budget unless risk_high or verifier_required; downgrade if cheaper candidate within `epsilon_quality = 0.05`; always allow required halt check | `event_type: route_decision`, `budget_snapshot`, `cost_delta`, reject reason `budget_exceeded` or `dominated_by_cheaper_candidate`, `halt_reason: budget_exhausted` | over-spending; under-spending on needed verifier/recovery; starvation of high-value module; hidden latency | budget overrun rate, cost saved, success lost from budget blocks, cost-normalized success, high-cost false block rate |

## interfaces

### gate-to-router API

```yaml
apply_gates:
  input:
    state_t: state
    route_query: query
    candidate_modules: [module]
    memory_candidates: [memory_entry]
    budget_status: budget_state
  output:
    gate_decisions: [gate_decision]
    allowed_modules: [module_id]
    required_modules: [module_id]
    blocked_modules:
      - module_id: string
        blocked_by: gate_type
        reason: string
    forced_halt_decision: halt_decision | null
```

### schema alignment

- Gate outputs become candidate validity flags and reject reasons in `route_decision.candidates`.
- Required verifier modules are added to `selected_modules` if `BudgetGate` permits.
- `HaltGate` emits the Subtask 02 `halt_decision` object.
- Memory decisions use the Subtask 02 `memory_entry` and `trajectory_event.memory_*` fields.
- Budget decisions use `state.budget`, `route_decision.budget_snapshot`, and `trajectory_event.cost_delta`.

## experiments

1. `gate_accuracy_suite`: Build labeled synthetic code/search tasks with known required tools, search, memory, verifier, and halt. For each gate compute true positives, false positives, false negatives, cost saved, errors introduced, and downstream success delta.
2. `verifier_halt_threshold_sweep`: Sweep `VerifierGate` and `HaltGate` thresholds across low/medium/high. Metrics: premature stopping rate, verifier catch rate, unnecessary continuation count, verifier cost, final success, and false pass rate.
3. `budget_gate_cost_sensitive`: Compare no budget gate, budget gate with downgrade, and budget gate with hard block under matched budgets. Metrics: budget overrun rate, cost-normalized success, success lost from budget blocks, and high-cost false block rate.

## risks

- Gate labels may be noisy; false positive/negative estimates need oracle fixtures, verifier outcomes, or human review for ambiguous cases.
- Gates can interact in hard-to-debug ways, for example `BudgetGate` suppressing `VerifierGate` and increasing premature halt.
- Thresholds may be task-family-specific; a single default can underperform on web/search versus coding.
- Logging gate decisions as route events may inflate event counts unless metrics distinguish decision overhead from module execution.
- Human review cost can become invisible if not kept in `human_review_minutes`.

## open_questions

- Should `SearchGate` be a specialized `ToolGate` mode or remain a separate gate for current-information policy?
- Which gate thresholds should become benchmark-required defaults versus tunable runtime config?
- When `BudgetGate` blocks a required verifier, should the runtime halt as `budget_exhausted`, continue with accepted risk, or ask for human confirmation?
- How should gate labels be produced for ambiguous tasks where the correct route is only known after execution?
