# Negative Transfer Cases

## scope

This document defines negative-transfer cases for memory KV-cache evaluation. It focuses on when retrieved memory makes the agent worse by activating the wrong route, suppressing fresh evidence, repeating a stale workflow, or importing an incompatible skill.

The cases are designed for log-derived measurement and must align with Subtask 02 `memoryEntry`, `trajectoryEvent`, `failureSignal`, and `routeDecision`.

## claims

- [文献] Reflexion and Voyager show that memory and skills can improve future behavior, but the same mechanism can repeat bad reflections or overgeneralized skills.
- [文献] Routing literature such as FrugalGPT, RouteLLM, RouterBench, MasRouter, and Agent-as-a-Router implies that wrong routing should be measured through regret or counterfactual outcomes, not only final success.
- [实验] Deliberately injected stale, irrelevant, and contradictory memories can measure negative-transfer sensitivity.
- [猜想] The safest memory cache is one that preserves failure memories as avoid signals while preventing them from becoming broad route suppressors.

## design

### minimal version

Negative transfer is present when all are true:

- A memory was read and contributed to route selection or context.
- A later event shows regression: wrong module route, contradiction, verifier failure, test failure, repeated action, stale fact, premature halt, or higher cost without benefit.
- The memory has a plausible causal path through `routeDecision.score_terms.memory_bonus`, selected module, or accepted belief.
- The run emits or references a `failureSignal` with `failure_type: negative_transfer` or a more specific related failure type.

### enhanced version

Classify cases:

| Case ID | Pattern | Expected signal | Mitigation |
| --- | --- | --- | --- |
| `nt_stale_knowledge` | Old fact/API behavior overrides fresh tool or source evidence. | contradiction, verifier_failed, stale_memory_rate | decay, require source refresh, zero positive bonus |
| `nt_wrong_family_episode` | Similar prior task from wrong family activates wrong route. | wrong_route_activation, test_failed | task-family and tool-schema filters |
| `nt_overgeneral_skill` | Reusable skill is applied outside preconditions. | invalid_tool, loop_stuck, test_failed | skill precondition checklist and verifier dry run |
| `nt_failure_overblock` | Failure memory suppresses a now-valid route. | proxy regret, unnecessary cost, low_confidence | freshness decay and promotion after successful replay |
| `nt_success_bias` | Success memory hides known avoid pattern. | verifier_failed, negative_transfer | success-plus-failure retrieval |
| `nt_context_crowding` | Too many memories crowd fresh evidence out of context. | higher token cost, lower success, premature_halt | top-n limit and value summaries |
| `nt_split_leakage` | Memory leaks benchmark answer or task-specific solution. | artificial transfer gain | split isolation and leakage audit |

### counterexamples

- A memory read followed by failure is not automatically negative transfer; the failure may be caused by a tool outage or impossible task.
- A harmful memory that is retrieved but not used should count as retrieval noise, not route-causing negative transfer.
- A failure memory that blocks a dangerous route and increases cost can still be useful if final success or risk reduction improves.
- A stale memory can be harmless if fresh evidence overrides it and no route changes.

## interfaces

Negative-transfer event:

```yaml
negative_transfer_case:
  case_id: string
  task_id: string
  run_id: string
  memory_id: string
  memory_profile: knowledge_memory | episodic_memory | skill_memory | behavior_kv | failure_memory
  source_read_event_id: string
  source_route_decision_id: string | null
  later_failure_signal_id: string
  causal_path: memory_bonus | accepted_belief | selected_workflow | verifier_skip | context_crowding
  usefulness_label_before: useful | harmful | neutral | unknown
  usefulness_label_after: harmful
  negative_transfer_count_after: int
  mitigation_action: decay | quarantine | forget | write_avoid_memory | require_verifier | lower_bonus_cap
```

Subtask 02 alignment:

- `memoryEntry.reuse_outcomes.harmful_count` increments when a case is confirmed.
- `trajectoryEvent.memory_usefulness_label` for the read is updated to `harmful` when evidence is available.
- `failureSignal.failure_type` should be `negative_transfer` when memory is the primary cause; otherwise use `contradiction`, `test_failed`, `verifier_failed`, `loop_stuck`, or `low_confidence` and include the memory id in `candidate_causes`.
- `routeDecision.candidates[].score_terms.memory_bonus` must show whether memory could have changed selection.

Quarantine and forgetting:

```yaml
retention_policy:
  quarantine_if:
    - "negative_transfer_count >= 2"
    - "harmful_count > useful_count and sample_size >= 3"
    - "fresh evidence contradiction is blocking"
  decay_if:
    - "freshness_decay < 0.30"
    - "tool_schema_refs no longer match current registry"
  forget_if:
    - "no evidence refs are recoverable"
    - "split leakage is confirmed"
    - "manual safety or benchmark policy requires removal"
  promote_if:
    - "verifier-approved replay succeeds"
    - "useful_count >= harmful_count + 2 after quarantine"
```

## experiments

1. `injected_negative_memory`: For each task family, seed one useful memory, one irrelevant memory, one stale memory, and one contradictory memory. Compare no memory, unfiltered retrieval, filtered retrieval, and quarantine-aware retrieval. Metrics: negative transfer rate, wrong route activation, verifier catch rate, final success loss, and cost overhead.
2. `failure_memory_overblock`: Seed failure memories for routes that were once bad but are now valid after tool/schema changes. Compare hard blocking, decayed penalty, verifier-required retry, and no failure memory. Metrics: proxy regret, successful route recovery, unnecessary route avoidance, and cross-task transfer gain.
3. `context_crowding_sweep`: Increase retrieved memory count while keeping task evidence constant. Metrics: stale memory rate, fresh-evidence citation accuracy, prompt token cost, premature halt, and useful reuse rate.

## risks

- Causal attribution can be uncertain when several memories and modules are active.
- Negative-transfer probes can overrepresent adversarial memories compared with normal workloads.
- Quarantine can become too aggressive if early experiments are noisy.
- Failure memories can encode obsolete tool limitations and suppress improved routes.
- Split leakage detection needs benchmark metadata that may not exist in all toy tasks.

## open_questions

- What causal standard is enough to confirm negative transfer: route score change, no-memory counterfactual, verifier judgment, or human review?
- Should harmful reads be updated in-place, or should a separate avoid memory be written while preserving the original?
- What default quarantine threshold best balances stability and recall?
- Should failure memories ever apply as hard route blocks, or only as negative `memory_bonus` penalties?
- How should negative transfer be reported when final success is still achieved but cost or latency increases sharply?
