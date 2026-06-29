# Runtime Prototype Report

## scope

This deliverable implements the Phase 0 deterministic runtime prototype in `src/agent_attention_runtime.py`. It keeps the existing single-file runtime shape and extends instrumentation for routing, gates, memory reads/writes, verifier checks, halt decisions, reflection, and trajectory JSON export.

Out of scope:

- real LLM, web, shell, or repository editing tools
- learned routing, embeddings, or online policy updates
- strict JSON Schema validation against all Subtask 02 objects
- claims that Phase 0 validation has passed globally

## claims

| Claim | Evidence type | Evidence |
| --- | --- | --- |
| A deterministic toy runtime is sufficient for first-pass inspectability. | 原型 | The CLI runs without external dependencies and emits replayable JSON events. |
| Route decisions expose the required Phase 0 score terms. | 原型 | Each route candidate logs `semantic_match`, `reliability`, `historical_success`, `cost`, `latency`, `risk`, `repetition`, and `memory_bonus`. |
| Memory is constrained to route scoring rather than direct execution control. | 原型 | Retrieved memories affect `score_terms.memory_bonus`; module execution still passes router and budget checks. |
| `memory_bonus` needs hard bounds to avoid stale or unrelated transfer dominating the route. | 文献/猜想/原型 | Subtask 04 policy requires cap `+0.20` and floor `-0.40`; tests cover unrelated memory not creating positive bonus. |
| Budget gating must be logged even in toy mode. | 原型 | Budget rejections include module id, reason, module cost, and budget snapshot. |
| Verifier-gated halting remains heuristic in Phase 0. | 猜想 | The verifier is deterministic and checks only toy failure signals, not external truth. |

## design

### minimal version

- `AgentAttentionRuntime.run()` loops over deterministic steps.
- Memory retrieval uses lexical overlap and usefulness/failure priors.
- Router supports `lexical` and `rule` strategies.
- Route candidates log full score terms and score weights.
- Gates are explicit event payloads: `ToolGate`, `SearchGate`, `MemoryGate`, `VerifierGate`, `HaltGate`, `BudgetGate`, and stubbed read-only `SafetyGate`.
- Toy modules execute deterministic functions for memory, search, code, critic, aggregation, and verification.
- Halt events always include reason, success signal, verifier status, and budget snapshot.
- Reflection writes an auditable `behavior_kv` memory entry with route signature and evidence refs.

### enhanced version

The same interface can later support:

- embedding router as a replacement for lexical `semantic_match`
- learned router policy with policy/version logs
- richer memory quarantine and usefulness updates
- verifier backed by tests, citations, or tool evidence
- strict schema validator over trajectory events
- no-memory and no-verifier counterfactual replay

### counterexamples

- If an unrelated memory shares no route/module terms, it should not create positive `memory_bonus`.
- If a module would exceed remaining budget, it must be rejected or skipped with an explicit budget reason.
- If verifier is disabled, halt still logs `verifier_status: skipped` rather than omitting verifier state.
- If a task needs current evidence but `SearchGate` is closed by weak lexical markers, the runtime may under-route search; this is a known toy-router limitation.

## interfaces

Implemented event kinds:

- `start`
- `memory_retrieval`
- `memory_read`
- `gates`
- `route`
- `budget_gate`
- `module_execution`
- `state_update`
- `verifier_result`
- `halt_gate`
- `reflection`
- `memory_write`
- `finish`

Implemented state fields:

- `goal`
- `step`
- `observations`
- `active_hypotheses`
- `selected_modules`
- `budget_used`
- `max_budget`
- `confidence`
- `risk`
- `failure_signals`
- `memory_reads`
- `memory_writes`
- `verifier_status`
- `verifier_required`
- `final_answer`

Implemented schema-aligned route fields:

- `decision_id`
- `routing_policy`
- `top_k`
- `query`
- `selected_modules`
- `candidates`
- `route_scores`
- `budget_snapshot`
- candidate `score_terms.semantic_match`
- candidate `score_terms.reliability`
- candidate `score_terms.historical_success`
- candidate `score_terms.cost`
- candidate `score_terms.latency`
- candidate `score_terms.risk`
- candidate `score_terms.repetition`
- candidate `score_terms.memory_bonus`
- candidate `selected`
- candidate `reject_reason`
- candidate validity flags for schema, budget, and risk

Implemented memory fields:

- `key`
- `value_summary`
- `memory_type`
- `usefulness_label`
- `retrieval_score`
- `route_signature`
- `evidence_refs`
- `negative_transfer_count`
- `memory_bonus`
- write-side `write_reason`

Known deviations from 02-05:

- Events preserve the existing lightweight `kind/payload` envelope rather than the full Subtask 02 `trajectory_event` schema.
- `event_id` is numeric and local to a run; there is no `run_id`, `task_id`, or `benchmark_id`.
- Cost and latency are scalar toy estimates, not token/tool/verifier/human-review cost objects.
- The verifier is a deterministic toy checker over failure signals, not a real test/citation verifier.
- Memory usefulness is not updated online after later reuse outcomes.
- `failure_memory` is encoded as `memory_type=behavior_kv` with `write_reason=failure`, following the interface cut.
- `rule` routing is a deterministic rule-flavored semantic shortcut, not a separate rule engine.

## experiments

Executable checks added to `tests/test_runtime.py`:

1. `test_trajectory_contains_route_score_terms_and_gate_events`
   - Confirms route candidates contain all required score terms.
   - Confirms explicit gate events are present.

2. `test_budget_gate_rejection_is_logged`
   - Runs a low-budget code task.
   - Confirms budget rejection is logged with a reason.

3. `test_unrelated_memory_does_not_create_positive_memory_bonus`
   - Injects an unrelated memory.
   - Confirms all route candidate `memory_bonus` values are non-positive.

4. `test_halt_event_includes_reason_status_and_budget`
   - Confirms halt payload includes reason, success signal, verifier status, and budget snapshot.

5. `test_memory_can_be_disabled`
   - Runs with `memory_enabled=False`.
   - Confirms no memory read event occurs and retrieval logs disabled status.

Manual demo command:

```bash
python3 src/agent_attention_runtime.py \
  --task "Fix a Python test failure in a small repo" \
  --output experiments/trajectories/runtime_demo.json \
  --max-steps 3 \
  --max-budget 2.0
```

Verification command:

```bash
python3 -m unittest discover -s tests
```

## risks

- Lexical scoring can miss paraphrases and overfit the tiny code/search toy vocabulary.
- Gate labels are heuristic; they are audit events, not calibrated classifiers.
- Budget gating can prevent useful verifier calls under tight budgets.
- The memory bonus route-match heuristic may be too simple for composite route signatures.
- Reflection writes every run, which can create noisy memory if used as a persistent store without later filtering.
- Full schema compliance is not enforced automatically yet.

## open_questions

- Should Phase 0 add a lightweight trajectory validator before synthesis?
- Should BudgetGate downgrade to cheaper alternatives instead of only rejecting over-budget candidates?
- Should memory reads be logged once per step or once per retrieved item in the final event contract?
- Should verifier-required but budget-blocked runs halt immediately as `budget_exhausted` or continue with accepted risk?
- How should `rule` router behavior be distinguished from lexical routing in metrics without adding a larger rule engine?
