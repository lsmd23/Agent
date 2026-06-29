# Retrieval Ablation

## scope

This document specifies experiments and metrics for measuring whether memory retrieval helps Agent-Attention routes. It evaluates retrieval strategies over the unified Subtask 02 memory schema, with separate analysis for `knowledge_memory`, `episodic_memory`, `skill_memory`, `behavior_kv`, and failure memories encoded as `behavior_kv`.

The scope is log-derived evaluation. It does not assume memory is beneficial by default and does not require a Python prototype.

## claims

- [文献] Retrieval memory, Reflexion, Voyager, and Memory Networks support external memory, but the literature warns indirectly through failures that irrelevant or stale retrieval can harm behavior.
- [原型] Subtask 02 route and trajectory logs contain enough fields to compute retrieval precision, useful reuse, stale memory, negative transfer, and transfer gain.
- [实验] A controlled memory corpus with useful, irrelevant, stale, and adversarial entries can isolate retrieval quality from base model quality.
- [猜想] Task-family filtering plus success-and-failure memory should beat unfiltered semantic retrieval under equal budgets.

## design

### minimal version

Run each task under the same activation budget with these retrieval variants:

| Variant | Description |
| --- | --- |
| `no_memory` | No memory read and `memory_bonus = 0`. |
| `knowledge_only` | Read only `knowledge_memory`. |
| `episodic_only` | Read only `episodic_memory`. |
| `skill_only` | Read only `skill_memory`. |
| `behavior_kv_only` | Read only route-conditioned behavior and failure profiles. |
| `success_only` | Exclude writes with `write_reason: failure` or `negative_transfer`. |
| `success_plus_failure` | Include positive and avoid memories. |
| `lexical_hybrid_filtered` | Phase 0 lexical retrieval with task-family, tool-schema, route-signature, and quarantine filters. |

The minimum retriever is lexical overlap over task signature, active subgoal, failure features, route signature, and tool schema refs. Enhanced variants may add embeddings or learned rerankers if they preserve the same audit records.

### enhanced version

Add retrieval controls:

- `embedding_unfiltered`: embedding ranking without task-family filters.
- `hybrid_filtered`: lexical prefilter plus embedding rerank.
- `verifier_approved_only`: only memories whose evidence refs include verifier pass or successful executable feedback.
- `fresh_only`: exclude memories beyond profile half-life.
- `quarantine_aware`: allow quarantined avoid memories to contribute negative penalties but not positive bonuses.
- `counterfactual_labeling`: run paired no-memory replay where feasible to label usefulness.

### counterexamples

- Embedding retrieval may select a semantically similar task with different tool constraints.
- Success-only retrieval may miss the exact avoid pattern needed after a failure signal.
- Task-family filtering may be too strict for cross-task skill transfer.
- Fresh-only retrieval can discard stable skills such as a general test-first workflow.

## interfaces

Each ablation run must emit these records:

```yaml
retrieval_run:
  run_id: string
  variant_id: string
  task_id: string
  benchmark_id: string
  retriever_type: none | lexical | embedding | hybrid | learned_reranker
  memory_profiles_enabled:
    - knowledge_memory
    - episodic_memory
    - skill_memory
    - behavior_kv
    - failure_memory
  filters:
    task_family: boolean
    tool_schema: boolean
    route_signature: boolean
    freshness: boolean
    quarantine: boolean
    verifier_approved: boolean
  top_n_requested: int
  top_n_used: int
  memory_bonus_cap: float
```

Read events must be joinable to Subtask 02:

```yaml
trajectoryEvent:
  action_type: memory_read
  memory_ids_read: [string]
  memory_usefulness_label: useful | harmful | neutral | unknown
  evidence_refs: [evidenceRef]
```

```yaml
routeDecision:
  candidates:
    - module_id: string
      score_terms:
        memory_bonus: float
      score_weights:
        memory_bonus: float
```

Metrics:

```yaml
useful_reuse_rate: "count(memory_read labels useful) / count(memory_read labels useful|harmful|neutral)"
retrieval_precision: "useful_reads / (useful_reads + harmful_reads + neutral_reads)"
negative_transfer_rate: "harmful_reads causing failureSignal.negative_transfer / memory_reads"
stale_memory_rate: "reads with freshness_decay below threshold or contradiction from fresh evidence / memory_reads"
cross_task_transfer_gain: "success_or_cost_normalized_success(memory_variant) - success_or_cost_normalized_success(no_memory)"
wrong_route_activation_rate: "route decisions where selected module was selected only after harmful memory_bonus and later failed"
memory_cost_overhead: "extra prompt tokens + retrieval latency + verifier calls versus no_memory"
write_acceptance_rate: "accepted memory writes / candidate memory writes"
```

## experiments

1. `memory_transfer_matrix`: Build repeated task families for Python test fixes, citation-heavy research answers, and multi-source search synthesis. Compare `no_memory`, `knowledge_only`, `episodic_only`, `trajectory_plus_failure`, and `all_profiles_filtered`. Metrics: task success, cost-normalized success, useful reuse rate, retrieval precision, cross-task transfer gain, and memory cost overhead.
2. `retriever_strategy_ablation`: On the same memory corpus, compare lexical, embedding, hybrid, task-family filtered, success-only, success-plus-failure, and verifier-approved retrieval. Metrics: retrieval precision, stale memory rate, negative transfer rate, verifier catch rate, and wrong route activation rate.
3. `top_n_pressure_test`: Sweep top-n from 1, 3, 5, 10, and 20 under a fixed context budget. Metrics: useful reuse, harmful reads, prompt token overhead, route entropy, and final success.

## risks

- Retrieval precision can look high if ambiguous unknown labels are excluded too aggressively.
- Counterfactual no-memory replay may be expensive or nondeterministic.
- Embedding retrieval quality depends on model choice, which may change over time.
- Cross-task transfer gain can be inflated if train/test task signatures leak benchmark-specific answers.
- Verifier-approved-only retrieval can be too conservative and miss useful but unverified behavioral memories.

## open_questions

- Should `unknown` usefulness labels count against retrieval precision or be reported separately?
- What is the canonical task-family set for Phase 0: Python test fix, citation-heavy research, multi-source search, or code/search only?
- Should embedding retrieval be allowed in Phase 0 experiments or reserved for Phase 4?
- What threshold defines stale memory: age, contradiction rate, tool schema version drift, or all three?
- How many no-memory counterfactual replays are enough to label useful reuse reliably?
