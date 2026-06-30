# Decision Log

## Decision: Formal Model Defaults After Literature Map
Date: 2026-06-26
Status: provisional

Chosen: For Subtask 02, model routing units as hierarchical modules: atomic tools/agents/verifiers/memory operations are the default logged unit, while composite workflows are allowed only if they expose child activations or an explicit opaque-cost record. Treat memory as typed (`knowledge_memory`, `episodic_memory`, `skill_memory`, `behavior_kv`) under one memory schema. Treat the first paper/prototype as valid with an auditable heuristic router; learned routing is a Phase 4 extension, not a prerequisite. Cost accounting includes model tokens, tool calls, verifier calls, wall-clock latency, failed retries, and optional human-review time as a separately labeled field. Route regret uses an offline oracle matrix when available; otherwise it is reported as proxy regret or left undefined.

Alternatives:
- Route only over high-level agent modules and hide tools/verifiers inside each agent.
- Require learned router parameters before calling the policy a router.
- Keep memory as one undifferentiated retrieval store.
- Count only model token cost.
- Force every benchmark to supply an oracle route.

Reason: Subtask 01 shows that the strongest comparators separate along routing, memory, aggregation, and evaluation boundaries. Atomic logging preserves inspectability and metric computation, while hierarchical modules keep room for practical coding agents such as a shell-enabled agent. Typed memory prevents knowledge retrieval, episodic reflection, and reusable skills from being evaluated as one blurred mechanism. A heuristic router is enough for Phase 0-1 because the project goal is clean comparison before learned routing.

Risk: The hierarchy may complicate the toy runtime schema; typed memory may overfit the formal model before ablation evidence exists; proxy regret can be weaker than true offline oracle regret.

Rollback: Collapse module hierarchy to flat `module_id` records, merge memory kinds into one `memory_entry.kind`, or restrict regret reporting to RouterBench/CodeRouterBench-style offline matrices if implementation complexity becomes too high.

Affected files: `docs/deliverables/01/*`, `docs/subtasks/02_formal_model.md`, `docs/project_status.md`

## Decision: Wave 2 Interface Defaults
Date: 2026-06-26
Status: provisional

Chosen: For Wave 2, Phase 0-1 uses code/search as the canonical toy suite, with web tasks kept as optional stretch for benchmark design. Route `semantic_match` starts with lexical similarity only; embedding similarity is specified as an enhanced variant and Phase 4/benchmark extension. Verifier-required halt is triggered by any of risk, uncertainty, irreversible action, or previous failure signals crossing threshold. Composite modules must log child activations when feasible; opaque-cost logging is acceptable only for external baselines or wrappers that cannot expose child events. Memory usefulness starts with verifier/outcome labels plus no-memory counterfactuals where available; human review is reserved for ambiguous negative-transfer cases. Phase 0 invariant failures emit warnings plus validation events; they become hard failures for benchmark-required fields after the runtime validator is introduced.

Alternatives:
- Include web tasks in the canonical Phase 0 suite immediately.
- Require embeddings in the first router.
- Require every composite workflow to expose child activations.
- Use human annotation as the primary memory usefulness label.
- Stop the runtime immediately on every invariant failure in Phase 0.

Reason: These defaults let 03/04/05 design independently while keeping the first implementation deterministic, cheap, and auditable. Lexical routing aligns with the existing toy runtime; code/search tasks are already represented in the scaffold; warning-mode invariants keep Phase 0 useful for instrumentation before strict benchmark enforcement.

Risk: Lexical routing may understate routing potential; optional web tasks may delay coverage of navigation failure modes; warning-mode invariants can hide defects if not promoted later.

Rollback: Promote embeddings, web tasks, or hard invariant failures when Subtask 06 runtime work shows the toy suite is too weak or schemas are being violated silently.

Affected files: `docs/deliverables/02/*`, `docs/subtasks/03_router_and_gates.md`, `docs/subtasks/04_memory_kv_cache.md`, `docs/subtasks/05_textual_backprop.md`, `docs/project_status.md`

## Decision: Runtime Prototype Interface Cut
Date: 2026-06-26
Status: accepted

Chosen: Subtask 06 should implement the existing single-file toy runtime first, extending `src/agent_attention_runtime.py` and `tests/test_runtime.py` rather than performing a broad package split. The trajectory should keep compatibility with the current event shape while adding schema-aligned fields where practical. Use `score_terms.repetition` as the canonical serialized key; `repetition_penalty` may appear only as a human-readable alias. Keep `SearchGate` separate from `ToolGate` because current-information policy needs independent false-positive/false-negative metrics. Use `memory_bonus` cap `+0.20` and floor `-0.40`. Encode `failure_memory` as `memory_type=behavior_kv` with `write_reason=failure|negative_transfer` for Phase 0. Keep update lifecycle (`accept|reject|quarantine|rollback`) in the Subtask 05 envelope rather than changing the core Subtask 02 `updateRecord` during Subtask 06. Represent `budget_policy` updates as `router_rule` or `halt_threshold` updates until a later schema revision.

Alternatives:
- Split the runtime immediately into `src/runtime/*`.
- Add `failure_memory` and update lifecycle fields directly to Subtask 02 schemas before implementation.
- Use `memory_bonus` cap `+0.10` for more conservative transfer.
- Merge `SearchGate` into `ToolGate`.
- Treat `budget_policy` as a first-class update target now.

Reason: The current runtime already passes tests and is sufficient for Phase 0 instrumentation. A narrow implementation reduces churn and preserves comparability while still allowing Subtask 06 to add audit fields, gate events, memory labels, reflection/update records, and metrics export. The schema choices follow Wave 2 deliverables without forcing a formal schema migration before the prototype proves which fields are essential.

Risk: Extending a single file can accumulate complexity; `failure_memory` as `behavior_kv` may be semantically awkward; lifecycle fields outside the core update schema may require synthesis cleanup.

Rollback: If Subtask 06 becomes hard to test in one file, split into `src/runtime/*` with compatibility shims. If failure-memory or update lifecycle fields become central to metrics, promote them into `docs/deliverables/02/schemas.json` during synthesis or a schema revision.

Affected files: `src/agent_attention_runtime.py`, `tests/test_runtime.py`, `docs/deliverables/03/*`, `docs/deliverables/04/*`, `docs/deliverables/05/*`

## Decision: Phase 0 Acceptance And Wave 4 Sequencing
Date: 2026-06-26
Status: accepted

Chosen: Accept Subtask 06 as the Phase 0 toy runtime gate. Advance to Experiment Phase 1 readiness and dispatch Subtask 07 before Subtask 08. Although the Wave 4 note allows parallel work, Subtask 08 depends on Subtask 07's benchmark and metrics definitions, so 08 will wait until 07 is accepted.

Alternatives:
- Dispatch 07 and 08 in parallel immediately after 06.
- Hold Phase 0 open until full Subtask 02 JSON Schema validation exists.
- Require real test/citation verifier before accepting Phase 0.

Reason: The runtime now passes 8 tests, supports the CLI, logs route score terms, gates, memory audit events, module execution, verifier results, halt decisions, reflection, and memory writes, and generated main-agent smoke trajectories without budget overrun. Full schema validation and real verifiers are explicitly listed as future work, not Phase 0 blockers.

Risk: Waiting on 07 slows baseline design; accepting Phase 0 with lightweight event envelopes leaves some schema drift for synthesis; deterministic verifiers may under-represent real failure modes.

Rollback: If 07 finds metrics cannot be computed from the current trajectories, return to Subtask 06 for a logging patch before dispatching 08.

Affected files: `docs/deliverables/06/runtime_report.md`, `src/agent_attention_runtime.py`, `tests/test_runtime.py`, `experiments/trajectories/*`, `docs/project_status.md`

## Decision: Baseline And Ablation Scope For First Matrix
Date: 2026-06-26
Status: accepted

Chosen: Subtask 08 should design the first baseline/ablation matrix around the Subtask 07 Phase 0 seed suite and the Subtask 06 legacy trajectory envelope. It should specify fair comparison contracts for Single ReAct, Fixed Workflow, Full-History, Retrieval-Memory, MoA-style, and Proposed Agent-Attention, but implementation may remain design-level unless a tiny runner can be added without changing `src/`. The first matrix must include equal-budget and cost-frontier reporting, and it must preserve known deviations for missing top-level run metadata, full cost deltas, and oracle/proxy regret.

Alternatives:
- Require Subtask 08 to implement all baseline runners immediately.
- Patch Subtask 06 to emit full target envelopes before designing baselines.
- Expand the task suite before defining baseline fairness rules.

Reason: Subtask 07 provides enough schema and metrics to design rigorous baselines now, but the runtime is still a deterministic toy harness. A design-first baseline plan avoids premature implementation while ensuring no future claim can skip fair budget, memory, verifier, and routing ablations.

Risk: Without runners, Phase 1 remains ready but not executed; legacy trajectory deviations may constrain metric precision.

Rollback: If Subtask 08 finds baseline fairness cannot be specified against the current fields, return to Subtask 06/07 for envelope metadata and scoring patches before synthesis.

Affected files: `docs/deliverables/07/*`, `experiments/tasks/phase0_seed_tasks.jsonl`, `docs/subtasks/08_baselines_and_ablations.md`

## Decision: Real LLM Benchmark Track
Date: 2026-06-26
Status: accepted

Chosen: Add a real-model benchmark track using a small GSM8K test sample from the public OpenAI grade-school-math repository. The first real benchmark runner is a direct single-call LLM baseline (`llm_direct_agent`) with exact numeric matching, target-envelope trajectories, and explicit known deviations. The runner supports OpenAI-compatible chat completions via `OPENAI_API_KEY` / `OPENAI_BASE_URL` and local Ollama via `OLLAMA_BASE_URL`.

Alternatives:
- Continue only with deterministic toy baselines.
- Start with HumanEval or SWE-bench before establishing a low-cost model-call harness.
- Use the assistant's own responses as benchmark outputs.

Reason: GSM8K gives a low-cost, public, exact-match benchmark that can run on weak local hardware through a remote API or local small model. It moves the project from instrument-only simulation toward actual model evaluation without requiring code execution sandboxes or large datasets.

Risk: A direct LLM baseline does not evaluate the full Agent-Attention architecture yet; GSM8K is math reasoning rather than tool/memory routing; exact-match evaluation can miss equivalent nonnumeric answers; API keys or local model availability are external blockers.

Rollback: If GSM8K proves too narrow, keep the runner pattern and add HumanEval, frozen-search QA, or SWE-bench Lite once execution/verifier infrastructure is ready.

Affected files: `experiments/real_benchmarks/*`, `experiments/tasks/gsm8k_test_sample.jsonl`, `docs/project_status.md`, `README.md`

## Decision: Real LLM Multi-Baseline + Agent-Attention LLM Runtime
Date: 2026-06-26
Status: accepted

Chosen: Extend the GSM8K real-LLM track with three comparable baselines: `llm_direct_agent` (single-call), `llm_react_agent` (multi-turn scratchpad), and `agent_attention_llm_tuned` (P2 tuned runtime with real LLM module executors for code/search/critic/aggregator). Shared `LLMClient` handles OpenAI-compatible and Ollama backends; `.env` auto-loads credentials. Memory disabled on the math track; lexical router only (learned router deferred). Multi-baseline runner writes per-baseline trajectories and aggregate summary JSON.

Alternatives:
- Keep only `llm_direct_agent` until learned router is ready.
- Use toy deterministic executors with a single real LLM call at the end.
- Run Agent-Attention with full memory/adaptive top-k on GSM8K immediately.

Reason: Wiring real LLM into module executors validates the Agent-Attention trajectory envelope under actual model latency and routing decisions, while direct and ReAct baselines anchor accuracy and cost. Disabling memory on math avoids Phase 2 negative-transfer confounds on a reasoning-only benchmark.

Risk: Lexical router may mis-route math tasks (e.g., critic before code_agent); multi-module AA may increase latency without accuracy gain on easy GSM8K items; API cost scales with module activations.

Rollback: Fall back to direct-only runner; or restrict AA track to toy executors until router quality improves on real LLM.

Affected files: `experiments/real_benchmarks/llm_client.py`, `experiments/real_benchmarks/llm_react_agent.py`, `experiments/real_benchmarks/agent_attention_llm_runtime.py`, `experiments/real_benchmarks/run_gsm8k_multi_baseline.py`, `tests/test_agent_attention_llm.py`, `docs/project_status.md`

## Decision: Unified Real LLM Wiring for All Evaluation Agents
Date: 2026-06-26
Status: accepted

Chosen: Wire real LLM module executors into all evaluation agent families via shared `llm_executors.py` + `faithful_llm_runners.py`. Unified runner `run_real_llm_eval.py` supports 19 baseline IDs across standalone (direct/ReAct), faithful control policies (6+1 tuned), memory ablations (6), and router variants (4). GSM8K uses exact-match oracle; Phase1 uses route-proxy oracle until executable verifiers exist.

Alternatives:
- Keep real LLM only on GSM8K direct/ReAct/AA tuned trio.
- Replace entire runtime with single LLM chat loop per baseline (loses routing instrumentation).
- Delay memory/router LLM variants until Phase1 executable oracles exist.

Reason: User requested real LLM for all evaluation agents. Executor injection preserves routing/memory/gate trajectories while swapping toy module outputs for actual model calls. Unified registry enables comparable multi-family benchmarks under one harness.

Risk: Phase1 route-proxy success can diverge from end-task quality; multi-module LLM calls increase API cost; default AA config may mis-route under real latency (observed 50% on GSM8K smoke vs 100% tuned).

Rollback: Restrict `run_real_llm_eval.py` to `--family standalone` or GSM8K-only suites; revert to toy executors for phase runners.

Affected files: `experiments/real_benchmarks/llm_executors.py`, `experiments/real_benchmarks/faithful_llm_runners.py`, `experiments/real_benchmarks/task_oracles.py`, `experiments/real_benchmarks/real_llm_envelope.py`, `experiments/real_benchmarks/run_real_llm_eval.py`, `tests/test_faithful_llm_runners.py`, `docs/project_status.md`

## Decision: Path A Faithful Baseline Track
Date: 2026-06-26
Status: accepted

Chosen: Pursue Path A (instrumentation-first) with faithful baseline runners implementing distinct control policies: `react_loop`, `static_workflow`, `react_full_history`, `react_loop_with_memory`, `static_all_proposers`, and `lexical_sparse` Agent-Attention. Run Phase 1 matrix on 12 mixed code/search/research tasks before GSM8K or learned routing.

Alternatives:
- Path B GSM8K real-LLM track as primary experiment line.
- Continue Phase 1 toy config-simulation matrix only.
- Jump to Phase 2 memory ablations without baseline execution.

Reason: Faithful control policies enable clean comparison under matched budgets. Path A aligns with the original experiment plan (code/search/research) and produces interpretable trajectories before real-model cost confounds routing conclusions.

Risk: Toy oracle success labels may not reflect real task difficulty; Agent-Attention may appear worse until top-k/budget tuning; harmful memory may remain under-detected in scorer.

Rollback: If faithful runners cannot be maintained, revert to documented config-simulation matrix while preserving trajectory envelope format.

Affected files: `experiments/baselines/*`, `experiments/phase1/phase1_faithful_runner.py`, `experiments/tasks/phase1_tasks.jsonl`, `docs/deliverables/08/result_table_phase1_faithful.md`

## Decision: Phase 1 Faithful Matrix Findings
Date: 2026-06-26
Status: accepted

Chosen: Report Phase 1 faithful results without architecture win claims. Document that `single_react_agent`, `fixed_workflow_agent`, and `full_history_agent` tie at ~92% success; `agent_attention_agent` has lowest proxy regret but 25% success and high budget exhaustion; `moa_style_agent` fails under equal budget (8% success).

Alternatives:
- Frame proxy regret alone as evidence of routing superiority.
- Hide MoA and Agent-Attention failures in summary tables.
- Declare Phase 1 complete and move to Phase 4 learned routing.

Reason: Claim-evidence matrix requires baseline comparison before improvement claims. Observed counterexample (low regret, low success) is scientifically useful and motivates budget/top-k tuning and Phase 2 memory work.

Risk: Negative results may discourage continuation; toy oracle may over-reward simple controllers.

Rollback: Re-run with tuned Agent-Attention (adaptive top-k, stricter budget gate) before finalizing Phase 1 conclusions.

Affected files: `experiments/phase1/phase1_faithful_experiment_memo.md`, `docs/deliverables/08/result_table_phase1_faithful.md`, `experiments/metrics/phase1_faithful_matrix_by_baseline.json`

## Decision: P2 Agent-Attention Tuning
Date: 2026-06-26
Status: accepted

Chosen: Implement P2 tuning as `agent_attention_agent_tuned` with adaptive top-k (k=1–3), strong budget gate (30% remaining budget threshold), and cost-quality frontier (epsilon=0.05). Keep default `agent_attention_agent` unchanged for A/B comparison.

Alternatives:
- Retune only top-k without budget gate.
- Replace lexical router with rule router.
- Skip re-run and tune hyperparameters manually.

Reason: Phase 1 faithful matrix showed default Agent-Attention at 25% success with 83% budget exhaustion despite lowest proxy regret. Tuning targets the observed failure mode (overspending on multi-module activation) per Subtask 03 gate/router design.

Result: On 12 tasks, tuned variant reached 66.7% success (+41.7pp), 0.207 cost-normalized success (+0.141), 2.03 mean cost (−0.90), 0% budget exhaustion. Still below single_react (91.7%).

Risk: Higher proxy regret after tuning; repeated-action ratio increased slightly; toy oracle may still favor simple controllers.

Rollback: Disable adaptive top-k or strong budget gate via runtime config flags if tuned variant regresses on Phase 2 memory tasks.

Affected files: `src/agent_attention_runtime.py`, `experiments/baselines/faithful_runners.py`, `experiments/phase1/phase1_tuned_comparison.py`, `experiments/phase1/phase1_p2_tuning_memo.md`

## Decision: Phase 2 Memory Ablation On Tuned Control
Date: 2026-06-26
Status: accepted

Chosen: Run Phase 2 memory ablations (`aa_no_memory`, `aa_memory_read_only`, `aa_success_only_memory_write`, `aa_unfiltered_memory`, `aa_quarantine_aware`) on P2 tuned control across 12 phase1 tasks. Adjust retrieval ranking to allow harmful memory recall with penalties applied via memory_bonus, not hard retrieval exclusion.

Alternatives:
- Run memory ablations on untuned default Agent-Attention.
- Skip negative-memory probe variants.
- Keep failure penalties in retrieval score threshold.

Reason: Tuned control is the current proposed system. Harmful-memory probe requires retrieved-but-harmful events to test quarantine. Separating retrieval rank from transfer penalties matches memory policy design.

Result: `aa_no_memory` reaches 75% success vs control 66.7%. `aa_unfiltered_memory` logs 4 harmful reads and 12 negative-transfer cases; `aa_quarantine_aware` blocks harmful reads with control-equivalent metrics.

Risk: No-memory win may reflect toy oracle limitations; negative-memory task still 0% success for all variants.

Rollback: Revert retrieval score formula if it over-retrieves harmful memories on non-probe tasks.

Affected files: `experiments/baselines/memory_ablations.py`, `experiments/phase2/phase2_memory_ablation_runner.py`, `experiments/phase2/phase2_memory_ablation_memo.md`

## Decision: Phase 3 Textual Backprop With Conservative Acceptance
Date: 2026-06-26
Status: accepted

Chosen: Implement Subtask 05 pipeline on Phase 2 `aa_tuned_control` failures: attribution → `updateRecord` → bounded `RuntimePatch` → failure replay + held-out validation → `textualUpdateEnvelope` lifecycle. Apply patches via `PatchedTunedRuntime` (router discourage, early-priority, quarantine, halt). Use acceptance gates from `update_acceptance_rules.md` (confidence ≥ 0.70 for accept).

Alternatives:
- Auto-apply all replay-improving patches.
- Skip held-out validation.
- Global prompt rewrite baseline.

Reason: Phase 3 goal is auditable local repair, not aggregate win claims. Conservative gates prevent overfitting to single failed trajectories. Quarantine preserves promising medium-confidence patches for later promotion.

Result: 4 failures processed; 3 replay-improved → quarantined (confidence 0.68); 1 rejected (no replay gain). 0 accepts.

Risk: Confidence heuristic may be miscalibrated; early-priority router patches may not generalize; negative-memory failures need memory-targeted patches beyond router rules.

Rollback: Reject quarantined patches if held-out promotion fails; lower or raise confidence gate after calibration.

Affected files: `experiments/phase3/attribution.py`, `experiments/phase3/runtime_patches.py`, `experiments/phase3/validation.py`, `experiments/phase3/phase3_backprop_runner.py`, `tests/test_textual_backprop.py`, `experiments/phase3/phase3_textual_backprop_memo.md`

## Decision: Phase 4 Learned Routing From Oracle + Trajectory Replay
Date: 2026-06-26
Status: accepted

Chosen: Implement Phase 4 with offline oracle matrix from task `expected_route`, auditable route features, logistic learned router trained on synthetic oracle rows plus Phase 1 faithful trajectories, and a four-way comparison (`lexical`, `rule`, `learned`, `oracle` upper bound) on P2 tuned Agent-Attention.

Alternatives:
- Embedding router first.
- Online bandit updates during runs.
- Train only on failed trajectories.

Reason: Subtask 03/08 specify learned routing as Phase 4 after baselines exist. Oracle matrix enables true regret reporting. Lightweight logistic model keeps training auditable without external ML deps.

Result: `aa_learned_router_replay` reaches 75% success vs lexical control 66.7%; oracle regret 0.221 vs 0.317. Rule router underperforms (41.7%). Oracle upper bound 91.7%.

Risk: Training includes same-task oracle labels (in-distribution). Proxy regret worsens for learned router. Not validated on real LLM.

Rollback: Revert to `aa_lexical_router` as default proposed row if held-out task families regress.

Affected files: `src/agent_attention_runtime.py`, `experiments/phase4/*`, `tests/test_learned_routing.py`, `docs/deliverables/07/scoring_script.py`, `experiments/phase4/phase4_learned_routing_memo.md`

## Decision: Wave 3 Default Policy — Cascade With AA Lite Escalation
Date: 2026-06-30
Status: accepted (pilot N=26 code suite)

Chosen: Default real-LLM routing policy is `cascade_react_aa_lite_llm` (ReAct → AA lite without verifier/memory → MoA rescue), not always-on `agent_attention_llm_tuned`. Register cascade baselines in `run_real_llm_eval.py --family cascade`. Defer Terminal-Bench architecture claims until env failure < 10% on T3 pilot; ACI patches (observation compression, truncated-JSON recovery, re-prompt) are prerequisite, not optional.

Alternatives:
- Continue optimizing always-on AA tuned lexical top-k.
- MoA as default baseline for all tasks.
- Expand TB to 20+ tasks before ACI rerun validation.
- Train learned router (Brief E) before cascade live eval.

Reason: Brief A confirms oracle route opportunity (+0.24 cost-normalized gap). Brief B/C live eval shows cascade beats always-on AA (100% @ 1.50 vs 84.6% @ 2.00). Brief H falsifies current expert heterogeneity (96% redundant activation). T3 ACI rerun fixes invalid-shell (0%) and reduces env failures (33%→20%) but pass count unchanged — bottleneck is agent capability on hard TB tasks, not shell parsing.

Result: `experiments/metrics/code_cascade_wave3_with_ci.json`; T3 rerun `t3_aci_rerun_pilot_summary.json` (4/15 pass). Synthesis: `docs/next_iteration/reports/W1_wave3_exploration_synthesis.md`.

Risk: N=26 local fixtures; cascade may not transfer to TB/SWE-bench. AA lite is a hand-tuned ablation, not learned routing.

Rollback: Revert default recommendation to `single_react_llm_agent` if cascade regresses on held-out task families or TB re-pilot.

Affected files: `experiments/cascade/*`, `experiments/ablations/*`, `experiments/real_benchmarks/run_real_llm_eval.py`, `experiments/terminal_bench/{adapter,tb_shell_loop,t3_aci_comparison}.py`, `docs/next_iteration/research_directions/*`, `docs/project_status.md`
