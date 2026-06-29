# Roadmap

## scope

This document turns the synthesis into an ordered implementation and experiment roadmap. It starts from the current state: Subtasks 01-08 are complete, Phase 0 toy runtime validation has passed, and Phase 1 baseline work is ready but not executed.

## claims

| Claim | Evidence type | Current support |
| --- | --- | --- |
| The next blocking work is baseline execution, not more architecture design. | 原型/实验 | Subtasks 07-08 define benchmark, scoring, baseline specs, and ablation matrix. |
| A trajectory envelope patch would reduce scoring deviations before Phase 1. | 原型 | Subtask 07 scorer reports legacy metadata/cost/regret deviations. |
| Memory, textual backprop, and learned routing should remain gated by baseline results. | 需实验 | Research memo and experiment plan require baseline before improvement claims. |

## design

### minimal version

#### Week 1: Phase 1 Baseline Readiness Patch

Goals:

- Add or wrap target trajectory envelopes with `run_id`, `task_id`, `benchmark_id`, `baseline_id`, `runtime_config`, `final_success_label`, and `known_deviations`.
- Preserve legacy scoring compatibility.
- Add a small manifest linking existing trajectories to seed tasks.

Success criteria:

- `scoring_script.py` returns fewer known deviations for new runs.
- Existing tests remain green.
- No architecture improvement claim is made.

#### Week 2: Phase 1 Static Router Baselines

Goals:

- Implement or simulate first baseline runners for:
  - `single_react_agent`
  - `fixed_workflow_agent`
  - `retrieval_memory_agent`
  - `agent_attention_agent`
- Keep `full_history_agent` and `moa_style_agent` as design-level or minimal harnesses if implementation is too costly.

Success criteria:

- Same seed tasks, same budget ceilings, same scorer.
- Result table includes proposed wins and losses.
- Cost-normalized success is reported with known deviations.

#### Week 3: Phase 2 Memory KV-cache Ablation

Goals:

- Run no-memory, read-only, success-only write, success-plus-failure memory.
- Add injected harmful/stale memory probes.

Success criteria:

- Report useful memory reuse, harmful reads, negative transfer, stale memory, and transfer gain.
- Memory usefulness labels are tied to verifier/outcome/counterfactual evidence.

#### Week 4: Phase 3 Textual Backpropagation Replay

Goals:

- Implement failure attribution records and local textual gradients.
- Replay failed trajectories with accept/reject/quarantine/rollback lifecycle.

Success criteria:

- Every update has evidence refs and rollback condition.
- Replay improvement and held-out regression are both reported.
- Global prompt rewrite is only a control, not default.

#### Week 5+: Phase 4 Learned Routing

Goals:

- Collect enough target-envelope trajectories.
- Compare lexical, embedding, contextual bandit, imitation-learned, and agentic router policies.

Success criteria:

- Router regret or proxy regret is reported separately.
- Learned router is compared against lexical and rule baselines under equal budgets.
- Negative transfer and cost regressions are reported, not hidden.

### enhanced version

Later extensions:

- Real code-task verifier using test execution.
- Frozen search/citation snapshots for reproducible research tasks.
- Cost model that combines tokens, tool calls, verifier calls, latency, retries, and human review.
- Web task stretch suite after SearchGate is validated.
- Schema validator integrated into tests.

### counterexamples

- Jumping directly to learned routing would skip the clean comparison requirement.
- Expanding benchmark size before schema metadata is fixed can multiply noisy trajectories.
- Reporting only cost-normalized success can hide raw failure rate; report both.

## interfaces

Roadmap gates:

| Gate | Required inputs | Pass condition |
| --- | --- | --- |
| Phase 1 readiness | 06 runtime, 07 scorer, 08 baseline specs | New or normalized trajectories score with task/baseline metadata. |
| Phase 1 baseline | baseline runners or faithful simulations | At least single ReAct, fixed workflow, retrieval-memory, and proposed runs are scored under matched budgets. |
| Phase 2 memory | memory policy and seed negative-transfer tasks | Memory metrics include useful reuse and negative transfer. |
| Phase 3 textual backprop | failure attribution/update lifecycle | Local updates improve replay or are rejected/quarantined with evidence. |
| Phase 4 learned routing | sufficient trajectory dataset | Learned routes compared to rule/lexical/embedding with regret/cost metrics. |

## experiments

1. `phase1_minimal_matrix`
   - Run 4 seed tasks x 4 initial systems: single ReAct, fixed workflow, retrieval-memory, proposed.
   - Use equal budgets and `scoring_script.py`.

2. `trajectory_envelope_delta`
   - Score the same task under legacy and target envelopes.
   - Confirm metric values are stable while known deviations drop.

3. `memory_negative_transfer_seed`
   - Use `phase0_seed_negative_memory_001`.
   - Compare no memory, unfiltered memory, quarantine-aware memory, and proposed memory policy.

## risks

- Baseline implementation effort can swamp research scope.
- Seed suite is too small for stable quantitative claims.
- Toy activation cost may diverge from real model/tool cost.
- Human-rubric tasks need calibration before strong claims.

## open_questions

- Should Phase 1 require all six baseline families or start with four executable ones plus two design-level cost-frontier specs?
- Should target envelope patch happen before or during baseline runner work?
- What is the smallest benchmark expansion that can expose routing rather than task-family keyword matching?
