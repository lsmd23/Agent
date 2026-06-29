# Error Taxonomy

## scope

This document defines the failure taxonomy for baseline and ablation analysis. It is intended for qualitative error review and for metric joins against `docs/deliverables/07/trajectory_schema.json`, `docs/deliverables/07/metrics_definitions.md`, and Subtask 06 legacy event lists.

The taxonomy covers required categories: bad route, bad memory, bad module output, bad aggregation, verifier miss, verifier false alarm, premature halt, budget exhausted, loop stuck, and external tool failure. It also adds schema/logging errors and benchmark-oracle ambiguity because these are known risks in the current Phase 0 setup.

## claims

- [文献] Agent benchmark work shows final success is insufficient; trajectory failure modes are needed to separate planning, tool, memory, verifier, and halt failures.
- [文献] Memory and reflection systems require explicit negative-transfer labels because helpful and harmful reuse can both look like high confidence.
- [原型] The Subtask 06 runtime exposes route candidates, budget gates, memory reads, verifier results, halt reasons, and failure signals that can seed this taxonomy.
- [实验] Subtask 07 scoring already counts loop stuck, budget exhaustion, premature halt, invalid tool calls, verifier catch, memory reuse, negative transfer, and route entropy where fields exist.
- [猜想] Many proposed-system failures will be mixed-cause; the taxonomy therefore supports one primary label plus secondary contributing labels.

## design

### minimal version

Each failed or suspicious run receives:

- One `primary_error_type`.
- Zero or more `secondary_error_types`.
- Evidence event IDs or legacy event IDs.
- A confidence label: `high`, `medium`, or `low`.
- A counterfactual hint: which baseline or ablation would help diagnose the cause.

| Error Type | Definition | Observable Signals | Scoring/Schema Mapping | Diagnostic Ablation |
| --- | --- | --- | --- | --- |
| `bad_route` | Router selects the wrong module, wrong order, or wrong top-k for the task. | Expected route not selected, discouraged module activated, high route regret, wrong-route failure signal. | `routing.activated_modules`, route candidates, `expected_route`, `oracle_route_regret_mean`, `proxy_route_regret_mean`. | `aa_rule_router`, `aa_embedding_router`, `aa_top1`, `aa_top2`. |
| `bad_memory` | Memory retrieval, bonus, or write policy causes irrelevant, stale, or harmful transfer. | Harmful read, stale memory, wrong-route memory, negative-transfer failure. | `memory.harmful_memory_reads`, `memory.negative_transfer_cases`, `memory_usefulness_label=harmful`, `error_type=negative_transfer`. | `aa_no_memory`, `aa_memory_read_only`, `aa_success_only_memory_write`. |
| `bad_module_output` | Correct module is activated but returns invalid, incomplete, unsupported, or low-quality output. | Verifier fail after module call, invalid tool call, contradiction, failed test/citation rubric. | `error_type=invalid_tool|contradiction|low_confidence`, `verifier_result=fail`, task oracle fail. | Stronger module prompt, fixed workflow, verifier always-on. |
| `bad_aggregation` | Aggregator combines outputs incorrectly, drops evidence, resolves conflicts poorly, or amplifies a wrong consensus. | Good candidate output exists but final aggregate fails; conflicting evidence collapsed without uncertainty. | `event_type=aggregate`, final fail, evidence refs, module outputs when logged. | MoA-style comparator, no aggregator route, critic-before-aggregate. |
| `verifier_miss` | Verifier passes or is skipped while final oracle fails. | `verifier_result=pass|skipped` and `final_success_label=fail`; unsupported final answer. | verifier statuses plus final oracle; current legacy logs undercount. | `aa_verifier_always_on`, verifier checklist update. |
| `verifier_false_alarm` | Verifier flags a correct or acceptable output and causes waste or wrong correction. | `verifier_result=fail` but task oracle passes or correction regresses. | target oracle plus verifier result; requires richer target envelope or human review. | `aa_no_verifier`, threshold/checklist ablation. |
| `premature_halt` | System stops before satisfying task oracle while budget or useful actions remain. | Halt reason `answer_ready|success` with fail/partial oracle, remaining budget, missing required module. | `process.premature_halt`, `halt_gate.payload.reason`, final label. | `aa_no_halt_gate`, verifier always-on. |
| `budget_exhausted` | System cannot activate needed modules because budget is exhausted or rejected. | Budget rejection, halt reason `budget_exhausted`, final failure after blocked verifier/tool. | `process.budget_exhaustion`, `budget_gate.decision=reject`. | `aa_no_budget_gate`, cost-frontier sweep, no-cost-penalty control. |
| `loop_stuck` | Repeated actions/modules fail to make progress. | High repeated ratio, repeated payload hash/module ID, halt reason loop stuck. | `process.loop_stuck`, `process.repeated_action_ratio`, `error_type=loop_stuck`. | `aa_no_repetition_penalty`, fixed workflow baseline. |
| `external_tool_failure` | External tool/search/test/API fails independently of route correctness. | Timeout, tool exception, unavailable source, flaky test. | `error_type=timeout|invalid_tool`, tool event payload, failure signals. | Retry policy, frozen source snapshot, executable fixture replay. |
| `schema_or_logging_gap` | Metric cannot be computed because required metadata or fields are missing. | Null task ID, missing cost delta, missing oracle regret, absent action hash. | `known_deviations`, null metric fields. | Target-envelope migration, manifest join. |
| `oracle_or_rubric_ambiguity` | Failure label is uncertain because oracle is human/rubric-based or criteria conflict. | `success_label=partial|unknown`, rubric disagreement, missing citation evaluator. | task `success_oracle.oracle_type`, final label, reviewer notes. | Human calibration, frozen evidence snapshots, stricter task schema. |

### enhanced version

Enhanced analysis adds:

- Primary/secondary cause graph: route -> memory -> module -> aggregation -> verifier -> halt.
- Per-task-family confusion matrix for failures.
- Verifier false-positive/false-negative table once task-oracle joins exist.
- Memory counterfactual labels from paired no-memory replay.
- Route oracle labels from offline outcome matrices.
- Severity scoring:

```yaml
severity:
  high: final failure or harmful external action
  medium: final partial success, large cost regression, or repeated instability
  low: final pass with inefficiency or logging gap
```

### counterexamples

- A wrong final answer after a correct route should not be labeled `bad_route`; label `bad_module_output`, `bad_aggregation`, or `verifier_miss`.
- A harmful memory read that does not affect route, output, or cost should be labeled secondary, not primary.
- A budget-exhausted run may be caused by MoA over-activation rather than budget policy; primary cause can be `bad_route` or `bad_aggregation` with `budget_exhausted` secondary.
- A verifier failure followed by final success is a catch, not a false alarm.
- A low route entropy run is not automatically a bad route; it may reflect a homogeneous task family.

## interfaces

### error annotation record

```yaml
error_annotation:
  annotation_id: string
  run_id: string | null
  trajectory_path: string
  task_id: string | null
  benchmark_id: string | null
  baseline_id: string
  ablation_id: string | null
  primary_error_type:
    bad_route | bad_memory | bad_module_output | bad_aggregation |
    verifier_miss | verifier_false_alarm | premature_halt |
    budget_exhausted | loop_stuck | external_tool_failure |
    schema_or_logging_gap | oracle_or_rubric_ambiguity | none
  secondary_error_types: [string]
  evidence_event_ids: [string]
  legacy_event_ids: [int]
  evidence_fields:
    final_success_label: pass | fail | partial | unknown
    failure_reason: string | null
    activated_modules: [string]
    verifier_statuses: [string]
    memory_usefulness_labels: [string]
    known_deviations: [string]
  confidence: high | medium | low
  severity: high | medium | low
  counterfactual_needed:
    - no_memory
    - no_verifier
    - fixed_workflow
    - full_history
    - moa_style
    - oracle_route_replay
  reviewer_notes: string
```

### automatic pre-label rules

These rules create candidate labels for human review:

| Rule | Candidate Label |
| --- | --- |
| `process.budget_exhaustion == true` | `budget_exhausted` |
| `process.loop_stuck == true` or `repeated_action_ratio > 0.60` | `loop_stuck` |
| `process.premature_halt == true` | `premature_halt` |
| `memory.negative_transfer_cases > 0` or harmful memory read | `bad_memory` |
| `invalid_tool_call_ratio > 0` or `error_type=invalid_tool` | `external_tool_failure` or `bad_module_output`, depending on tool availability |
| final fail with verifier pass/skipped | `verifier_miss` |
| verifier fail followed by final pass | verifier catch, not an error unless cost regression is severe |
| missing task/run metadata or null regret/cost fields | `schema_or_logging_gap` secondary |

### alignment with 07 metrics

| Metric | Error Types It Helps Diagnose |
| --- | --- |
| `success` | Any primary error when failed; no error when passed unless process regression is severe. |
| `cost` and `activation_cost` | budget exhausted, over-activation, verifier false alarm, MoA cost failure. |
| `latency/activation cost` | verifier always-on cost, MoA cost, external tool timeout. |
| `module_calls` | over-routing, no halt gate, MoA over-activation. |
| `repeated_ratio` | loop stuck, no repetition penalty failure. |
| `premature_halt` | premature halt, verifier miss. |
| `verifier_catch` | verifier effectiveness; low catch with failures suggests verifier miss. |
| `memory_reuse` | useful transfer or bad memory when harmful. |
| `negative_transfer` | bad memory, wrong-route memory. |
| `route_entropy` | over- or under-routing; interpret with success/cost. |
| `route_regret` | bad route when oracle/proxy available. |

### legacy deviations

Subtask 06 legacy logs constrain taxonomy confidence:

- Missing top-level run metadata can make task-family and baseline grouping ambiguous.
- Scalar toy cost can identify relative activation cost inside toy runs, not real token/API latency cost.
- Missing oracle/proxy regret means many `bad_route` labels are inferred from expected routes or final outcomes.
- Missing action hashes means loop-stuck detection can use repeated module IDs only.
- Verifier catch is conservative because explicit correction events are not always logged.

## experiments

1. `failure_label_smoke_on_existing_trajectories`
   - Score all existing trajectories in `experiments/trajectories/`.
   - Apply automatic pre-label rules to failed or deviation-heavy runs.
   - Expected output: at least `schema_or_logging_gap` secondary labels for legacy metadata/cost/regret deviations; no forced final-failure label for passing runs.

2. `negative_transfer_annotation_probe`
   - Run memory-enabled proposed and `aa_no_memory` on `phase0_seed_negative_memory_001`.
   - Label any harmful read, search-only wrong route, or final regression as `bad_memory` primary or secondary.
   - Metrics: negative transfer cases, useful reuse, wrong-route activation, verifier catch, final success delta.

3. `verifier_halt_error_probe`
   - Compare `aa_no_verifier`, control, and `aa_verifier_always_on` on code/search tasks.
   - Label final failures with skipped/pass verifier as `verifier_miss`; label fail-with-remaining-budget as `premature_halt`.
   - Metrics: premature halt, verifier catch, verifier calls, activation cost, success.

4. `budget_loop_probe`
   - Compare control, `aa_no_budget_gate`, `aa_no_halt_gate`, and `aa_no_repetition_penalty` under tight budgets.
   - Label budget rejections, max-step exhaustion, and repeated route loops.
   - Metrics: budget exhaustion, step exhaustion, repeated ratio, loop stuck, cost-normalized success.

## risks

- Automatic labels can confuse symptoms with causes; keep human review or counterfactual replay for primary labels.
- Legacy logs can undercount verifier misses and repeated actions because they lack full oracle/action-hash fields.
- Rubric-based tasks may have ambiguous final labels, especially mini-research and citation tasks.
- Mixed-cause failures are likely; forcing one primary label may hide interactions.
- Negative transfer can be rare without deliberate probes and paired no-memory controls.

## open_questions

- Should `schema_or_logging_gap` appear in the same error table as behavioral failures, or only in a data-quality appendix?
- What threshold should turn high cost with final success into a reportable error?
- Should verifier false alarms require an external oracle pass, or can human review mark them?
- How many counterfactual no-memory replays are needed before labeling `bad_memory` high confidence?
- Should bad aggregation be separated into `conflict_resolution_error`, `evidence_drop`, and `consensus_drift` after MoA runs exist?
