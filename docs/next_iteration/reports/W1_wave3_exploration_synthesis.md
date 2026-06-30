# W1: Wave 3 Exploration Synthesis

Date: 2026-06-30  
Status: **Complete** — research-direction briefs A/B/C/F/H executed; cascade live eval + T3 ACI rerun done.

## scope

First pass through `docs/next_iteration/research_directions/`: falsify or support ranked tracks using the existing 26-task code matrix, cascade pilots, and Terminal-Bench T3 pilot (with ACI rerun).

## brief_outcomes

| Brief | Question | Outcome | Key artifact |
|-------|----------|---------|--------------|
| A | Route opportunity on code suite? | **supports_direction** | `experiments/analysis/oracle_route_audit.md` |
| B | Direct-first cascade? | **supports_direction** (replay + live) | `experiments/analysis/cascade_pilot_audit.md` |
| C | Which AA components hurt? | **supports_direction** | `experiments/analysis/aa_ablation_audit.md` |
| F | TB failures: ACI vs architecture? | **supports_direction** | `experiments/analysis/tb_aci_audit.md` |
| H | Real expert specialization? | **falsified_or_blocked** | `experiments/analysis/expert_specialization_audit.md` |
| D/E/G | Outcome memory / learned router / backprop | **not started** | — |

## code_suite_headline_results

26-task matched-budget matrix (`experiments/metrics/code_full_matrix_summary.json`):

| Policy | Accuracy | Mean calls | Cost-norm |
|--------|----------|------------|-----------|
| `cascade_react_aa_lite_llm` | **100%** | **1.50** | **0.6667** |
| `moa_style_llm_agent` | 96.2% | 2.08 | 0.4630 |
| `single_react_llm_agent` | 88.5% | 1.23 | 0.7187 |
| `cascade_react_moa_llm` | 92.3% | 1.65 | 0.5581 |
| `agent_attention_llm_tuned` | 84.6% | 2.00 | 0.4231 |

Oracle route matrix: 100% oracle success vs 96.2% best single baseline; route opportunity gap **+0.24** cost-normalized; winner entropy **1.51/2.32**.

**Recommended default policy:** `cascade_react_aa_lite_llm` (ReAct → AA lite → MoA), not always-on AA tuned.

## terminal_bench_headline_results

T3 pilot (3 tasks × 5 baselines) before and after ACI patches:

| Metric | Before | After ACI rerun |
|--------|--------|-----------------|
| Total pass | 4/15 | 4/15 |
| Environment failure | 5/15 (33%) | 3/15 (20%) |
| Agent failure | 6/15 | 8/15 |
| Invalid-shell step rate | ~4% (pre-patch trajectories) | **0%** (63 logged steps) |
| AA tuned pass | 0/3 | 1/3 |

See `experiments/analysis/t3_aci_rerun_comparison.md`.

**TB routing claims remain blocked** until agent failures on hard tasks drop and N ≥ 20 on stable manifest.

## reframed_thesis (safe to claim)

> Route opportunity exists on the local code suite; always-on lexical AA tuned is not the default winner. A direct-first cascade with a **lite AA escalation slot** reaches oracle-like success at lower cost than MoA. Terminal-Bench comparisons require ACI-stable eval first; current bottleneck is agent capability on multi-step server tasks, not shell parsing.

## unsafe_thesis (do not claim)

- Always-on `agent_attention_llm_tuned` beats ReAct or MoA.
- AA modules are heterogeneous experts (96% redundant activation).
- TB pilot shows AA advantage.
- Learned router validated on 26 tasks alone.

## open_tracks (next dispatch)

1. **Brief E** — lightweight router on oracle labels (diagnostic only at N=26).
2. **Brief D** — outcome-memory router (no answer leakage).
3. **T4** — bootstrap CI + Pareto from wave3 + code matrix summaries — **Done** (`T4_statistics_and_pareto.md`).
4. **TB** — raise `max_shell_steps` to 12 on server tasks; re-run 3×5 after env rate < 10%.
5. **Expert redesign** — Brief H falsified current modules; need distinct specialist prompts/tools before routing can win on TB.

## artifacts_index

| Path | Purpose |
|------|---------|
| `experiments/metrics/code_cascade_wave3_summary.json` | Live cascade eval |
| `experiments/metrics/oracle_route_matrix.json` | Brief A |
| `experiments/metrics/aa_ablation_pilot.json` | Brief C |
| `experiments/metrics/t3_aci_rerun_pilot_summary.json` | TB ACI rerun |
| `experiments/analysis/wave3_cascade_comparison.md` | Cascade report |
| `docs/next_iteration/research_directions/` | Direction library (updated 2026-06-30) |

## commands

```bash
# Regenerate T3 before/after comparison (after rerun completes)
python3 experiments/terminal_bench/t3_aci_comparison.py

# Async T3 rerun
bash experiments/terminal_bench/run_t3_pilot_async.sh

# Cascade wave3 report
python3 experiments/cascade/wave3_comparison_report.py
```
