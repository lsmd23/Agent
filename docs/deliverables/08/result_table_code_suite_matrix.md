# Code Suite Matrix (26 tasks × baselines)

Model: `Qwen3-30B-A3B-Instruct-2507` | End-task: pytest executable oracle

Source: `experiments/metrics/code_full_matrix_summary.json` + `code_cascade_wave3_summary.json`

## Fixed baselines

| Baseline | Accuracy | Mean calls | Cost-norm |
|----------|----------|------------|-----------|
| `moa_style_llm_agent` | 96.2% (25/26) | 2.08 | 0.463 |
| `single_react_llm_agent` | 88.5% (23/26) | 1.23 | 0.719 |
| `retrieval_memory_llm_agent` | 84.6% (22/26) | 1.35 | 0.629 |
| `agent_attention_llm_tuned` | 84.6% (22/26) | 2.00 | 0.423 |
| `fixed_workflow_llm_agent` | 65.4% (17/26) | 1.19 | 0.548 |

## Cascade policies (Wave 3 live eval)

| Baseline | Accuracy | Mean calls | Cost-norm | Bootstrap CI |
|----------|----------|------------|-----------|--------------|
| **`cascade_react_aa_lite_llm`** | **100% (26/26)** | **1.50** | **0.667** | 100%–100% |
| `cascade_react_aa_moa_llm` | 100% (26/26) | 1.69 | 0.591 | 100%–100% |
| `cascade_react_moa_llm` | 92.3% (24/26) | 1.65 | 0.558 | 80.8%–100% |

## Oracle routing (Brief A, replay)

| Metric | Value |
|--------|-------|
| Oracle success | 100% (26/26) |
| Best single baseline | MoA 96.2% |
| Route opportunity gap (cost-norm) | +0.243 |
| Winner entropy | 1.51 / 2.32 |

Source: `experiments/metrics/oracle_route_matrix.json`

## Pareto frontier (T4)

Non-dominated on success ↑ vs mean calls ↓:

- `cascade_react_aa_lite_llm`
- `single_react_llm_agent`
- `fixed_workflow_llm_agent`

Always-on `agent_attention_llm_tuned` is **not** on the frontier.

Full table: [result_table_cost_quality_pareto.md](result_table_cost_quality_pareto.md)

## Real-task ablations (T7, replay)

| Ablation | Outcome | Key metric |
|----------|---------|------------|
| Learned route selector (Brief E) | weak | held-out regret 0.177 vs static 0.181 |
| Outcome memory (Brief D) | weak | Δ regret +0.001 vs cascade |
| Textual backprop (Brief G) | blocked | 0/4 accept |

Details: [result_table_real_task_ablations.md](result_table_real_task_ablations.md)
