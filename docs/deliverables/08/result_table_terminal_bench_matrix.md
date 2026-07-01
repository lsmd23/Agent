# Terminal-Bench Matrix Results (T3 Pilot)

Model: `Qwen3-30B-A3B-Instruct-2507` via Paratera.  
Agent: multi-step shell ReAct (`max_shell_steps=8`).  
Tasks: `fix-permissions`, `fibonacci-server`, `configure-git-webserver`.

| Baseline | fix-permissions | fibonacci-server | configure-git-webserver | Total |
|----------|-----------------|------------------|-------------------------|-------|
| single_react_llm_agent | pass | fail (env) | fail (env) | 1/3 |
| fixed_workflow_llm_agent | pass | fail | fail | 1/3 |
| retrieval_memory_llm_agent | pass | fail | fail | 1/3 |
| moa_style_llm_agent | pass | fail | fail (env) | 1/3 |
| agent_attention_llm_tuned | fail (env) | fail (env) | fail | 0/3 |

Source: `experiments/metrics/terminal_bench_matrix_summary.json` (2026-06-30 pilot).

**Full 7-task matrix (steps=12):** [`result_table_terminal_bench_full_steps12.md`](result_table_terminal_bench_full_steps12.md)
