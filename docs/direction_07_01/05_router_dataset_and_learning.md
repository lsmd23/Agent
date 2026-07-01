# D05: Router Dataset And Learning Brief

## Objective

Build a route-outcome dataset and decide when learned routing is justified.

## Why This Matters

The latest learned route selector is weak at N=26. That does not mean learning is useless; it means the dataset is too small and experts are not yet distinct enough. A future learner needs better labels, more tasks, and leakage controls.

## Required Inputs

- `experiments/metrics/oracle_route_matrix.json`
- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/metrics/code_cascade_wave3_summary.json`
- `docs/next_iteration/reports/T7_real_task_ablations.md`
- task manifests under `experiments/tasks/`

## Dataset Schema

Each row should represent a task-route pair:

```json
{
  "task_id": "string",
  "split": "train|dev|test",
  "task_features": {},
  "route_id": "string",
  "route_success": true,
  "model_calls": 1,
  "total_tokens": 500,
  "latency_ms": 1000,
  "failure_type": null,
  "reward": 0.0,
  "oracle_route": "string",
  "label_source": "executed|replay|oracle_matrix"
}
```

## Feature Families

- prompt length
- repo file count
- failing test length
- error type
- import/config/string/math/task family labels
- direct route confidence if available
- verifier result after direct attempt
- previous route outcome memory

## Research Questions

1. Is there enough data to train anything beyond heuristics?
2. Which features predict escalation need?
3. Does learning beat static cascade triggers on held-out tasks?
4. Does the learner generalize across task families?

## Suggested Experiments

### Experiment A: Dataset Builder

Create a durable route-outcome dataset from existing summaries.

### Experiment B: Baseline Learners

Compare:

- static direct-first cascade
- lexical/static router
- logistic regression or decision tree
- simple threshold policy over direct failure/confidence

### Experiment C: Split Stress Test

Evaluate by:

- random split
- task-family split
- hard-task held-out split

If results only work on random split, do not claim robust learning.

## Acceptance Criteria

`supports_direction` if:

- learned/threshold router reduces held-out regret against static cascade;
- split leakage audit passes;
- labels come from executable outcomes or clearly marked replay.

`weak_or_inconclusive` if:

- learner only marginally beats static policy;
- task count is too small.

`falsified_or_blocked` if:

- labels are dominated by one route;
- train/test leakage cannot be controlled.

## Deliverables

- `docs/direction_07_01/reports/D05_router_dataset_and_learning.md`
- route-outcome dataset JSONL or manifest
- feature/label documentation
- held-out regret table

## Guardrails

- Do not train on test outcomes.
- Do not use task IDs as features.
- Do not present N=26 learned routing as main evidence.
