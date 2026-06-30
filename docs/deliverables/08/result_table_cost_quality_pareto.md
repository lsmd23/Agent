# Cost–Quality Pareto Table (26-Task Code Suite)

Task-bootstrap accuracy CIs; cost = mean model calls per task. Pareto frontier = non-dominated on (success ↑, calls ↓).

Model: `Qwen3-30B-A3B-Instruct-2507` | Tasks: 26

| Baseline | Success (95% CI) | Mean calls | Cost-norm (95% CI) | Pareto |
|----------|------------------|------------|--------------------|--------|
| `cascade_react_aa_lite_llm` | 100.0% [100.0%, 100.0%] | 1.5 | 0.8686 [0.7564, 0.9679] | yes |
| `cascade_react_aa_moa_llm` | 100.0% [100.0%, 100.0%] | 1.69 | 0.7897 [0.6615, 0.8974] |  |
| `moa_style_llm_agent` | 96.2% [88.5%, 100.0%] | 2.08 | 0.4679 [0.4231, 0.5000] |  |
| `cascade_react_moa_llm` | 92.3% [80.8%, 100.0%] | 1.65 | 0.8013 [0.6667, 0.9231] |  |
| `single_react_llm_agent` | 88.5% [76.9%, 100.0%] | 1.23 | 0.8333 [0.6923, 0.9615] | yes |
| `retrieval_memory_llm_agent` | 84.6% [69.2%, 96.2%] | 1.35 | 0.7372 [0.5833, 0.8846] |  |
| `agent_attention_llm_tuned` | 84.6% [69.2%, 96.2%] | 2.0 | 0.4231 [0.3462, 0.4808] |  |
| `fixed_workflow_llm_agent` | 65.4% [46.2%, 80.8%] | 1.19 | 0.5705 [0.3910, 0.7436] | yes |

## Interpretation

- **Pareto frontier** baselines are not strictly dominated on success vs mean calls.
- Always-on `agent_attention_llm_tuned` is **not** on the frontier; cascade policies are.
- N=26 local fixtures — use as pilot evidence only.
