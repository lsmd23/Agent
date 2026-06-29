# Memory Policy

## scope

This document defines when the Agent-Attention runtime reads, writes, updates, decays, quarantines, or forgets memory KV-cache entries. It covers `knowledge_memory`, `episodic_memory`, `skill_memory`, `behavior_kv`, and `failure_memory` as an operational alias encoded through the Subtask 02 `behavior_kv` memory type.

The policy is limited to design and log contracts under `docs/deliverables/04/`. It does not modify Subtask 02 schemas, runtime code, tests, `docs/decision_log.md`, or `docs/project_status.md`.

## claims

- [文献] Reflexion supports verbal episodic memory from feedback; Voyager supports reusable skill memory; Memory Networks support explicit read/write separation.
- [原型] Subtask 02 already requires memory reads, memory writes, usefulness labels, failure signals, route decisions, and score term logging, so policy enforcement can be log-derived.
- [实验] The proposed policy is testable through no-memory, read-only, success-only, and success-plus-failure ablations.
- [猜想] More memory is not necessarily better; filtered, decayed, and quarantined memory should improve stability more than unbounded recall.

## design

### minimal version

Read memory only when one of these conditions is true:

- The router query has `action_need: memory_read`.
- The active subgoal matches a known task family and there is no fresh external evidence yet.
- A failure signal appears and the system needs avoid patterns or verifier checklists.
- Halt is being considered and the verifier needs prior success/failure constraints.

Write memory only when at least one condition is true:

- The task succeeds and the route is reusable, with evidence refs to verifier result, tool output, or final trajectory event.
- The task fails with a clear failure attribution.
- A verifier catches a key error that should become a checklist or avoid pattern.
- A read memory causes negative transfer and must be recorded as a harmful avoid case.

Do not write:

- Unverified intermediate guesses.
- Full raw trajectories.
- Failure complaints without attribution.
- Benchmark answer content that would leak across train/test splits.

### enhanced version

Memory is separated by profile but persisted under the Subtask 02 schema:

| Profile | 02 `memory_type` | Main value | Default read filter | Default write reason |
| --- | --- | --- | --- | --- |
| `knowledge_memory` | `knowledge_memory` | accepted facts and source-backed constraints | task family, tool schema, source recency | `success`, `manual_seed`, `uncertainty` |
| `episodic_memory` | `episodic_memory` | compact trajectory and route outcome | task signature, route signature, failure/success features | `success`, `failure`, `negative_transfer` |
| `skill_memory` | `skill_memory` | reusable procedure or skill reference | task family, tool schema, verifier compatibility | `success`, `manual_seed` |
| `behavior_kv` | `behavior_kv` | route preference, avoid pattern, verifier choice | route signature, failure features | `success`, `failure`, `negative_transfer` |
| `failure_memory` | `behavior_kv` | failure mode and mitigation or avoid route | failure signature, route signature | `failure`, `negative_transfer` |

Read pipeline:

1. Build a memory query from goal hash, task signature, active subgoal, failure signals, uncertainty ids, tool schema refs, and route history.
2. Apply hard filters: benchmark split, memory profile, tool schema compatibility, quarantine status, and task-family scope.
3. Rank with Phase 0 lexical matching. Enhanced runs may add embedding or hybrid retrieval, but must log retriever type.
4. Apply usefulness prior, freshness decay, route match, and negative-transfer penalty.
5. Pass only top-n summaries into route scoring; do not inject raw full histories.

Write pipeline:

1. Compress the trajectory into causal facts: trigger, route, key tool/verifier result, outcome, and reuse condition.
2. Validate that evidence refs are present and point to source events.
3. Select memory profile and 02 `memory_type`.
4. Initialize `reuse_outcomes.last_outcome` to `unknown` unless the write is a negative-transfer record.
5. Emit a `trajectoryEvent` with `action_type: memory_write`, `memory_ids_written`, `memory_usefulness_label`, and evidence refs.

### counterexamples

- A memory read before fresh source lookup can bias a citation-heavy task toward outdated facts.
- A skill memory for `pytest` can harm a JavaScript repo if the tool schema filter is ignored.
- A failure memory can over-block a route when a tool has been fixed since the original failure.
- A broad task signature like `coding` retrieves too many unrelated workflows; a narrow signature like one exact issue id prevents transfer.

## interfaces

Each read/write must be auditable through these joined records:

```yaml
memory_entry:
  memory_id: string
  memory_type: knowledge_memory | episodic_memory | skill_memory | behavior_kv
  key:
    task_signature: string
    route_signature: [string]
    tool_schema_refs: [string]
    failure_success_features: [string]
  value:
    trajectory_summary: string
    accepted_facts: [string]
    successful_workflow: [string]
    useful_reflection: string
    reusable_skill_ref: string | null
  provenance:
    source_run_id: string
    evidence_refs: [evidenceRef]
    created_at: string
  write_reason: success | failure | uncertainty | negative_transfer | manual_seed
  reuse_outcomes:
    useful_count: int
    harmful_count: int
    neutral_count: int
    last_outcome: useful | harmful | neutral | unknown
```

```yaml
memory_operation_audit:
  operation_id: string
  operation_type: read | write | promote | decay | quarantine | forget
  memory_id: string
  key_summary: string
  value_summary: string
  evidence_refs: [evidenceRef]
  route_signature: [string]
  usefulness_label: useful | harmful | neutral | unknown | not_applicable
  negative_transfer_count: int
  trajectory_event_id: string
  route_decision_id: string | null
```

`routeDecision` alignment:

- Retrieved memories can affect only `score_terms.memory_bonus`.
- Default `memory_bonus` is capped at `+0.20` and can be negative down to `-0.40`.
- Fresh external evidence, verifier failure, or contradiction sets positive memory contribution to `0`.
- Candidate modules must still pass schema, budget, and risk checks.

`failureSignal` alignment:

- A harmful memory read must create or reference a failure signal with `failure_type: negative_transfer` when it causes wrong route activation, stale fact adoption, repeated action, verifier failure, or test failure.
- `candidate_causes` must include the memory id and the route decision id when available.

## experiments

1. `write_policy_acceptance`: Run 40 synthetic tasks with successful routes, clear failures, verifier catches, ambiguous failures, and unrelated intermediate notes. Compare accepted writes against expected policy labels. Metrics: memory write acceptance rate, invalid write rejection rate, evidence-ref coverage, and value-summary compression ratio.
2. `read_timing_ablation`: Compare no memory, read at task start, read after decomposition, read only after failure, and read before halt. Use code/search tasks. Metrics: success, token cost, retrieval precision, useful reuse, stale memory rate, and negative transfer.
3. `memory_bonus_cap_ablation`: Replay identical route decisions with caps `0.00`, `0.10`, `0.20`, and uncapped. Metrics: wrong route activation, cross-task transfer gain, cost delta, and verifier catch rate.

## risks

- Memory can leak benchmark answers if split isolation is not enforced.
- A strong memory bonus can overpower fresh evidence and make old trajectories look authoritative.
- Quarantine can hide useful memories after noisy failures.
- Human labels for usefulness can be expensive and inconsistent.
- Logging every memory operation increases event volume and may require summarization discipline.

## open_questions

- Should `failure_memory` become a first-class Subtask 02 enum or remain encoded as `behavior_kv`?
- What exact default should be used for `memory_bonus` cap in the first runtime: `0.10` or `0.20`?
- Should memory reads happen before or after first decomposition for citation-heavy research tasks?
- What confidence threshold is enough to promote a quarantined memory back to active use?
- Should usefulness labels be updated online during a run, only after halt, or both?
