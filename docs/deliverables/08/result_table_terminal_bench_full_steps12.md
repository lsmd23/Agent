# Terminal-Bench Full Matrix (7 tasks × 5 baselines)

Model: `Qwen3-30B-A3B-Instruct-2507` | `max_shell_steps=12` | no-apt manifest

Source: `experiments/metrics/t3_full_steps12_summary.json` (2026-07-01)

| Baseline | fix-permissions | fibonacci-server | configure-git-webserver | count-dataset-tokens | download-youtube | blind-maze-explorer-5x5 | cartpole-rl-training | Total |
|----------|---|---|---|---|---|---|---|-------|
| single_react_llm_agent | fail (envi) | fail (envi) | fail (envi) | fail (envi) | fail (envi) | fail (envi) | fail (agen) | 0/7 |
| fixed_workflow_llm_agent | pass | fail (envi) | fail (envi) | fail (agen) | fail (envi) | fail (envi) | fail (agen) | 1/7 |
| retrieval_memory_llm_agent | fail (envi) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | 0/7 |
| moa_style_llm_agent | pass | fail (agen) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | 1/7 |
| agent_attention_llm_tuned | pass | fail (envi) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | fail (agen) | 1/7 |

## Aggregate

- Total pass: **3/35**
- Failure categories: {'environment_failure': 12, 'agent_failure': 20, 'none': 3}

## Comparison

| Run | Tasks | Steps | Pass rate |
|-----|-------|-------|-----------|
| T3 pilot (original) | 3 | 8 | 4/15 (27%) |
| T3 ACI rerun | 3 | 8 | 4/15 (27%) |
| **T3 full (this run)** | **7** | **12** | **3/35 (8.6%)** |

Only `fix-permissions` had any passes (3/5 baselines).

See also: [T3 report](../../next_iteration/reports/T3_matched_budget_benchmark_matrix.md)
