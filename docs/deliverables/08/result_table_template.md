# Result Table Template

## scope

This document defines result tables for baseline and ablation reporting. Tables are designed to be filled directly from `docs/deliverables/07/scoring_script.py` output, with optional task-schema joins for task family, expected route, and negative-transfer probe labels.

The template supports both target envelopes and Subtask 06 legacy trajectories. It must preserve known deviations instead of silently filling missing metadata, cost deltas, or oracle/proxy regret.

## claims

- [文献] Agent and routing comparisons need success, cost, latency, module calls, memory, verifier, and regret views, not just final accuracy.
- [原型] The current scoring script emits per-run and aggregate sections that can populate these tables without reading hidden prompts.
- [实验] Existing trajectories under `experiments/trajectories/` can be scored and produce baseline-compatible fields, although they currently represent only the proposed toy runtime.
- [猜想] A table that reports deviations and counterexample task families will prevent premature claims that the proposed system wins broadly.

## design

### minimal version

Use this table for the first baseline matrix. Each row is one aggregate over a fixed task set and budget.

| System | Task Set | Runs | Success | Cost-Normalized Success | Cost | Latency | Module Calls | Repeated Ratio | Premature Halt | Verifier Catch | Memory Reuse | Negative Transfer | Route Entropy | Oracle Regret | Proxy Regret | Known Deviations |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `single_react_agent` | `phase0_seed` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | N/A | N/A | N/A | N/A | N/A | TBD |
| `fixed_workflow_agent` | `phase0_seed` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | N/A | N/A | N/A | N/A | N/A | TBD |
| `full_history_agent` | `phase0_seed` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | N/A | N/A | N/A | N/A | N/A | TBD |
| `retrieval_memory_agent` | `phase0_seed` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | N/A | N/A | N/A | TBD |
| `moa_style_agent` | `phase0_seed` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | N/A | N/A | N/A | N/A | N/A | TBD |
| `agent_attention_agent` | `phase0_seed` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

Use this table for ablations. Each row is one aggregate over the same tasks as the control.

| Control | Ablation | Changed Variable | Runs | Success | Cost-Normalized Success | Cost | Module Calls | Repeated Ratio | Premature Halt | Budget Exhaustion | Verifier Catch | Memory Reuse | Negative Transfer | Route Entropy | Route Reject | Oracle Regret | Proxy Regret | Interpretation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `agent_attention_default_phase0` | `aa_no_memory` | `memory_policy=none` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | N/A | 0 | TBD | TBD | TBD | TBD | TBD | TBD |
| `agent_attention_default_phase0` | `aa_no_verifier` | `verifier_policy=none` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | 0 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `agent_attention_default_phase0` | `aa_verifier_always_on` | `verifier_policy=always_on` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `agent_attention_default_phase0` | `aa_top1` | `top_k_policy=top1` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### enhanced version

Enhanced reports add:

- Task-family breakdown table: code, search, mini-research, and later web tasks separately.
- Counterexample table: rows where proposed loses to a baseline or ablation under matched budgets.
- Cost-frontier table: one row per system and cost ceiling.
- Memory-transfer table: useful, neutral, harmful, unknown, and stale memory labels.
- Verifier-confusion table: verifier true catch, false alarm, false miss, and inconclusive rates once target envelopes include oracle outcomes.
- Regret table: true oracle regret and proxy regret never mixed in one numeric column.
- Confidence interval columns once each task family has enough runs.

### counterexamples

Report these explicitly:

| Counterexample Class | Trigger | Required Report Fields |
| --- | --- | --- |
| Fixed workflow wins | `fixed_workflow_agent.success >= proposed.success` and lower cost. | task family, budget, route entropy, failure reason. |
| Full history wins | `full_history_agent` succeeds where structured state/memory fails. | context size, truncation flag, repeated ratio, final success. |
| Retrieval-only explains gain | `retrieval_memory_agent` matches proposed within tolerance. | memory reuse, negative transfer, module calls, route entropy. |
| MoA raw success wins | `moa_style_agent` higher success but higher cost. | raw success, cost-normalized success, latency, module calls. |
| Proposed negative transfer | `agent_attention_agent` reads harmful/stale memory and regresses. | harmful reads, negative transfer cases, wrong-route module, verifier catch. |
| Proposed under-routes | Top-1/adaptive misses needed verifier/search/code module. | oracle/proxy regret, selected modules, premature halt, failure reason. |

## interfaces

### scoring JSON to table mapping

| Table Column | `scoring_script.py` Field | Notes |
| --- | --- | --- |
| `System` | `run.baseline_id` or external manifest baseline id | Legacy 06 defaults to `agent_attention_agent`. |
| `Task Set` | external manifest or `run.benchmark_id` | Legacy 06 may be null. |
| `Runs` | `aggregate.run_count` | Per-system aggregate. |
| `Success` | `aggregate.success_rate` | Mean `final.task_success`. |
| `Cost-Normalized Success` | `aggregate.mean_cost_normalized_success` | Uses toy activation cost for legacy 06. |
| `Cost` | `aggregate.mean_activation_cost` | Replace with full total cost once target `cost_delta` is available. |
| `Latency` | target-envelope `events[].latency_ms` aggregate | Not emitted as aggregate by the current script; use `TBD` or extend scorer later. |
| `Module Calls` | `aggregate.mean_module_calls` | From allowed budget gates or finish-selected fallback. |
| `Repeated Ratio` | `aggregate.mean_repeated_action_ratio` | Module ID proxy under legacy logs. |
| `Premature Halt` | `aggregate.premature_halt_rate` | Approximate under legacy logs. |
| `Budget Exhaustion` | `aggregate.budget_exhaustion_rate` | Include budget rejections. |
| `Verifier Catch` | `total_verifier_catches / total_verifier_failures` or per-run `verifier.verifier_catch_rate` | Conservative when correction events are absent. |
| `Memory Reuse` | per-run `memory.useful_memory_reuse_rate` or weighted aggregate | Current aggregate reports counts, so weighted calculation may be external. |
| `Negative Transfer` | `aggregate.total_negative_transfer_cases` | Count, not rate. |
| `Route Entropy` | `aggregate.mean_route_entropy` | Only meaningful for routed or module-logged systems. |
| `Route Reject` | `aggregate.mean_route_reject_rate` | Requires route candidates. |
| `Oracle Regret` | per-run `routing.oracle_route_regret_mean` | Null unless target route oracle fields exist. |
| `Proxy Regret` | per-run `routing.proxy_route_regret_mean` | Never mix with oracle regret. |
| `Known Deviations` | `aggregate.known_deviations` | Must be printed, not hidden. |

### per-run detail template

| Run ID | Task ID | Family | System | Ablation | Success Label | Failure Reason | Cost | Calls | Repeated Ratio | Loop Stuck | Premature Halt | Budget Exhaustion | Verifier Calls | Verifier Catch Rate | Memory Reads | Useful Reads | Harmful Reads | Negative Transfer | Activated Modules | Deviations |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| TBD | `phase0_seed_code_fix_001` | `code_agent_task` | `agent_attention_agent` | control | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### recommended JSON summary shape

```yaml
result_table_record:
  system: string
  task_set: string
  task_family: string | all
  baseline_id: string
  ablation_id: string | null
  control_id: string | null
  changed_variable: string | null
  run_count: int
  success_rate: number
  cost_normalized_success: number
  activation_cost: number
  latency_ms: number | null
  module_calls: number
  repeated_action_ratio: number
  premature_halt_rate: number
  budget_exhaustion_rate: number
  verifier_catch_rate: number | null
  useful_memory_reuse_rate: number | null
  negative_transfer_cases: int
  route_entropy: number | null
  route_reject_rate: number | null
  oracle_route_regret: number | null
  proxy_route_regret: number | null
  known_deviations: [string]
  interpretation: string
```

## experiments

1. `populate_existing_proposed_row`
   - Run `python3 docs/deliverables/07/scoring_script.py experiments/trajectories/*.json --output experiments/metrics/phase0_existing_all.json`.
   - Fill an `agent_attention_agent` aggregate row from the output.
   - Expected result: row has non-null success, cost, calls, repeated ratio, memory, verifier, route entropy, route reject, and known deviations; task metadata may remain null under legacy logs.

2. `baseline_table_smoke`
   - After baseline runners exist, score one trajectory per required baseline on `phase0_seed_code_fix_001`.
   - Fill the minimal baseline table.
   - Pass condition: every row has success, cost, calls, halt, verifier, and deviations fields; route/memory fields can be `N/A` only when the baseline lacks the mechanism by design.

3. `counterexample_table_smoke`
   - Use `phase0_seed_negative_memory_001` with useful and harmful memory injections.
   - Fill the counterexample table if `aa_no_memory` beats full proposed or if proposed reads harmful memory.
   - Pass condition: negative transfer is visible in table fields rather than buried in narrative.

## risks

- Current scorer aggregate does not emit latency or weighted memory reuse; those cells need target-envelope aggregation or an external post-processor.
- Legacy 06 trajectories lack task metadata, so task-family tables require an external manifest.
- Route entropy can look better when a baseline logs fewer modules; interpret only alongside success and cost.
- `N/A`, `null`, and `TBD` must be distinct: not applicable, unavailable in logs, and not yet run.
- Averages over tiny Phase 0 seed tasks are smoke tests, not effect-size claims.

## open_questions

- Should the scoring script be extended to emit latency aggregates and weighted memory reuse for direct table filling?
- Should result tables use mean and confidence interval columns immediately, or only after Phase 1 has at least 20 tasks per family?
- Should `full_history_agent` be reported under `single_agent` family or as a separate family in normalized output?
- What tolerance defines "retrieval-only explains the gain" in counterexample reporting?
- Should budget exhaustion be a failure class, a process warning, or both in final tables?
