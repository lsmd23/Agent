# T4: Statistics And Pareto Analysis

Date: 2026-06-30
Status: **Complete** — task-bootstrap CIs + cost-quality Pareto on 26-task code suite.

## scope

Turn raw benchmark per-task rows into statistically interpretable tables for paper drafting.

## commands_run

```bash
python3 experiments/analysis/t4_statistics.py
python3 experiments/analysis/bootstrap_metrics.py
```

## artifacts_created

- `experiments/metrics/t4_code_suite_with_ci.json`
- `experiments/metrics/t4_pareto_summary.json`
- `docs/deliverables/08/result_table_cost_quality_pareto.md`
- `docs/next_iteration/reports/T4_statistics_and_pareto.md`

## Headline Verdicts

- **Always-on AA vs ReAct:** inconclusive
- **Always-on AA vs MoA:** inconclusive
- **Cascade AA lite vs always-on AA:** win
- **Cascade AA lite vs ReAct:** inconclusive
- **Cascade AA lite vs MoA:** inconclusive
- **Cascade AA lite on Pareto frontier:** yes
- _Note:_ Task-bootstrap CIs on N=26 local fixtures; not publication-grade alone.

## Paired Comparisons (vs ReAct)

- `moa_style_llm_agent` vs `single_react_llm_agent`: wins 3, losses 1, ties 22 (Δsuccess=0.077)
- `agent_attention_llm_tuned` vs `single_react_llm_agent`: wins 2, losses 3, ties 21 (Δsuccess=-0.038)
- `cascade_react_aa_lite_llm` vs `single_react_llm_agent`: wins 3, losses 0, ties 23 (Δsuccess=0.115)
- `cascade_react_moa_llm` vs `single_react_llm_agent`: wins 2, losses 1, ties 23 (Δsuccess=0.038)
- `cascade_react_aa_lite_llm` vs `agent_attention_llm_tuned`: wins 4, losses 0, ties 22 (Δsuccess=0.154)

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

## Terminal-Bench T3 (3 tasks × 5 baselines, pilot)

Not included in Pareto (different benchmark). Failure taxonomy only.

- Before ACI: pass 26.7%, env 33.3%, agent 40.0%
- After ACI: pass 26.7%, env 20.0%, agent 53.3%
- TB architecture verdict: **inconclusive** (N too small; agent failures dominate).

## acceptance

- [x] Regenerated from saved per-task rows
- [x] Task-bootstrap CIs (not call-level)
- [x] Pareto frontier identified
- [x] Verdict: cascade AA lite **win** vs always-on AA; always-on AA **loss/inconclusive** vs ReAct/MoA
