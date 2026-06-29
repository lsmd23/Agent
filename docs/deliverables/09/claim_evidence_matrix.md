# Claim Evidence Matrix

## scope

This document classifies project claims by evidence level: literature-supported, prototype-validated, experiment-observed, planned experiment, or conjecture. It prevents speculative architecture claims from being reported as conclusions.

## claims

The matrix itself is the deliverable claim: every major project assertion must be traceable to evidence or explicitly marked as conjecture.

## design

### minimal version

| Claim | Evidence level | Evidence | Status |
| --- | --- | --- | --- |
| ReAct-style single agents are required baselines. | 文献支持 | Subtask 01 literature table; ReAct and SWE-agent entries. | accepted |
| Fixed planner/executor/critic workflows are required baselines. | 文献支持 | HuggingGPT, MetaGPT, planner workflow comparators in Subtasks 01 and 08. | accepted |
| MoA-style aggregation is a required comparator but not the same as sparse routing. | 文献支持 | Subtask 01 MoA and LLM-Blender analysis; Subtask 08 baseline specs. | accepted |
| Memory must be evaluated for both positive transfer and negative transfer. | 文献支持 / 需实验 | Reflexion, Voyager, Memory Networks; Subtasks 04 and 07 metrics. | accepted as design, not result |
| Agent-Attention can be formalized as state, module pool, router, gates, memory, verifier, halt, reflection, and textual update. | 原型可验证 | Subtask 02 schemas; Subtasks 03-05 designs. | accepted |
| A deterministic toy runtime can log route/gate/memory/verifier/halt/reflection events. | 实验 | Subtask 06 tests and trajectories. | accepted for Phase 0 |
| Phase 0 runtime obeys budget limits in smoke checks. | 实验 | Main-agent smoke trajectories and Subtask 06 budget tests. | accepted for toy runs |
| Existing trajectories can be scored for a Phase 0 metric subset. | 实验 | Subtask 07 scoring script scored 5 trajectories. | accepted |
| The current runtime improves over fixed workflows. | 需实验 | No baseline runners or baseline results yet. | not claimed |
| The current runtime improves over retrieval-memory baselines. | 需实验 | Requires Phase 1/2 ablations. | not claimed |
| Textual backprop improves replay or held-out tasks. | 需实验 | Subtask 05 protocol only; no runs yet. | not claimed |
| Learned routing can reduce regret relative to lexical routing. | 猜想 / 需实验 | Phase 4 plan only. | not claimed |

### enhanced version

Use four report labels:

- `literature-supported`: cite paper/system/benchmark; no local empirical claim.
- `prototype-validated`: implemented and tested in toy runtime.
- `experiment-observed`: supported by trajectory/scoring outputs.
- `conjecture`: plausible mechanism or hypothesis awaiting experiment.

### counterexamples

- A passing runtime test is not evidence that the architecture beats ReAct.
- A high route score is not evidence of a correct route without oracle/proxy outcome.
- Memory reads labeled useful in toy runs are not evidence of robust transfer without no-memory counterfactuals.
- Verifier pass in toy runtime is not evidence of real-world correctness.

## interfaces

Every report claim should include:

```yaml
claim:
  id: string
  statement: string
  evidence_level: literature_supported | prototype_validated | experiment_observed | planned_experiment | conjecture
  evidence_refs: [string]
  required_metrics: [string]
  caveats: [string]
  allowed_report_wording: string
```

## experiments

1. `claim_audit_before_public_report`
   - Review every conclusion sentence and assign one evidence level.
   - Fail the audit if any proposed improvement claim lacks baseline or ablation evidence.

2. `metric_traceability_check`
   - For every experiment-observed claim, identify scorer output fields and trajectory paths.
   - Fail if the claim requires unavailable oracle fields without marking a deviation.

## risks

- The architecture vocabulary can make conjectures sound more mature than they are.
- Phase 0 instrumentation success can be mistaken for task-performance success.
- Baseline design can be mistaken for baseline execution.

## open_questions

- What evidence threshold is required for a claim to move from planned experiment to experiment-observed?
- Should literature-supported claims include exact source versions or commit hashes for code-based comparators?
- How should human-rubric claims be labeled before inter-annotator agreement is measured?
