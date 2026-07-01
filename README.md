# Agent-Attention Runtime Research

Sparse, logged **module-routing** agent runtime: dynamic activation over agents, tools, memory, verifiers, and halt gates — evaluated against ReAct, fixed workflows, retrieval memory, and MoA under **matched LLM budgets**.

**Last updated:** 2026-07-01  
**Model:** `Qwen3-30B-A3B-Instruct-2507` (Paratera, OpenAI-compatible)  
**Tests:** 120 passing (`python3 -m unittest discover -s tests`)

---

## Headline Results

| Question | Answer |
|----------|--------|
| Does always-on AA tuned beat ReAct/MoA on code tasks? | **No** — 84.6% @ 2.00 calls; below MoA (96.2%) and ReAct on cost-quality Pareto |
| Best policy on 26-task code suite? | **`cascade_react_aa_lite_llm`** — 100% @ 1.50 calls (bootstrap CI 100%–100%) |
| Is routing opportunity real? | **Yes** — oracle gap +0.24 cost-normalized; winner entropy 1.51/2.32 |
| Does TB show AA advantage? | **No** — 7×5 full matrix 3/35 pass; architecture claims blocked |
| Workshop-tier paper pack? | **Ready** — see [paper outline](docs/paper_outline.md) |

**Recommended default deployment policy:** `cascade_react_aa_lite_llm` (ReAct → AA lite → MoA rescue), **not** always-on `agent_attention_llm_tuned`.

---

## Results at a Glance

### 1. Executable code suite (26 tasks) — primary evidence

| Baseline | Success | Calls | Cost-norm | Pareto |
|----------|---------|-------|-----------|--------|
| **`cascade_react_aa_lite_llm`** | **100%** | **1.50** | **0.667** | yes |
| `moa_style_llm_agent` | 96.2% | 2.08 | 0.463 | |
| `single_react_llm_agent` | 88.5% | 1.23 | 0.719 | yes |
| `agent_attention_llm_tuned` | 84.6% | 2.00 | 0.423 | no |
| `fixed_workflow_llm_agent` | 65.4% | 1.19 | 0.548 | yes |

→ **Detail matrix:** [`docs/deliverables/08/result_table_code_suite_matrix.md`](docs/deliverables/08/result_table_code_suite_matrix.md)  
→ **Pareto + bootstrap CI:** [`docs/deliverables/08/result_table_cost_quality_pareto.md`](docs/deliverables/08/result_table_cost_quality_pareto.md)  
→ **T4 report:** [`docs/next_iteration/reports/T4_statistics_and_pareto.md`](docs/next_iteration/reports/T4_statistics_and_pareto.md)

### 2. Terminal-Bench (real terminal tasks)

| Run | Tasks × baselines | Steps | Pass | Env fail | Notes |
|-----|-------------------|-------|------|----------|-------|
| T3 pilot | 3 × 5 = 15 | 8 | 4/15 (27%) | 33% | pre-ACI |
| T3 ACI rerun | 3 × 5 = 15 | 8 | 4/15 (27%) | 20% | invalid-shell 0% |
| **T3 full** | **7 × 5 = 35** | **12** | **3/35 (8.6%)** | **34%** | only `fix-permissions` passes |

| Baseline (7-task full) | Pass |
|------------------------|------|
| fixed_workflow / MoA / AA tuned | 1/7 each |
| single_react / retrieval_memory | 0/7 |

→ **3-task matrix:** [`docs/deliverables/08/result_table_terminal_bench_matrix.md`](docs/deliverables/08/result_table_terminal_bench_matrix.md)  
→ **7-task full matrix:** [`docs/deliverables/08/result_table_terminal_bench_full_steps12.md`](docs/deliverables/08/result_table_terminal_bench_full_steps12.md)  
→ **ACI before/after:** [`experiments/analysis/t3_aci_rerun_comparison.md`](experiments/analysis/t3_aci_rerun_comparison.md)  
→ **T3 report:** [`docs/next_iteration/reports/T3_matched_budget_benchmark_matrix.md`](docs/next_iteration/reports/T3_matched_budget_benchmark_matrix.md)

### 3. Exploration briefs (Wave 3 + T7)

| Brief | Topic | Outcome |
|-------|-------|---------|
| A | Oracle route matrix | supports_direction |
| B | Cascade controller | supports_direction |
| C | AA ablation | supports_direction |
| D | Outcome memory | weak (Δ regret +0.001) |
| E | Learned router | weak (50% held-out route accuracy) |
| F | TB ACI | supports_direction |
| G | Textual backprop | falsified (0/4 accept) |
| H | Expert specialization | falsified (96% redundant activation) |

→ **Synthesis:** [`docs/next_iteration/reports/W1_wave3_exploration_synthesis.md`](docs/next_iteration/reports/W1_wave3_exploration_synthesis.md)  
→ **Completion checklist:** [`docs/next_iteration/reports/W2_complete_iteration_goals.md`](docs/next_iteration/reports/W2_complete_iteration_goals.md)  
→ **T7 ablations:** [`docs/deliverables/08/result_table_real_task_ablations.md`](docs/deliverables/08/result_table_real_task_ablations.md)

---

## Safe vs Unsafe Claims

| Safe to claim | Do not claim |
|---------------|--------------|
| Cascade AA lite wins vs always-on AA on N=26 code suite | Always-on AA beats ReAct or MoA |
| Oracle route opportunity exists on code suite | TB shows AA architecture advantage |
| TB ACI fixes reduced invalid-shell to 0% | Learned router production-ready at N=26 |
| Expert modules need redesign (Brief H) | Main-track A-conference ready |

Governance: [`docs/next_iteration/research_directions/06_claim_governance.md`](docs/next_iteration/research_directions/06_claim_governance.md)  
Claim matrix: [`docs/deliverables/09/claim_evidence_matrix.md`](docs/deliverables/09/claim_evidence_matrix.md)

---

## Documentation Map

| Topic | Entry point |
|-------|-------------|
| **Project status** | [`docs/project_status.md`](docs/project_status.md) |
| **Paper draft pack** | [`docs/paper_outline.md`](docs/paper_outline.md) · [`docs/artifact_reproducibility.md`](docs/artifact_reproducibility.md) |
| **Next-iteration handbook** | [`docs/next_iteration/README.md`](docs/next_iteration/README.md) |
| **Research directions** | [`docs/next_iteration/research_directions/README.md`](docs/next_iteration/research_directions/README.md) |
| **All task reports** | [`docs/next_iteration/reports/README.md`](docs/next_iteration/reports/README.md) |
| **Result tables (08)** | [`docs/deliverables/08/`](docs/deliverables/08/) |
| **Decisions** | [`docs/decision_log.md`](docs/decision_log.md) |
| **Publication gap** | [`docs/publication_gap_assessment.md`](docs/publication_gap_assessment.md) |

### Metrics JSON (regenerable summaries)

```
experiments/metrics/code_full_matrix_summary.json      # 26-task faithful baselines
experiments/metrics/code_cascade_wave3_with_ci.json    # cascade + bootstrap CI
experiments/metrics/t4_pareto_summary.json             # Pareto frontier
experiments/metrics/oracle_route_matrix.json           # Brief A
experiments/metrics/t3_full_steps12_summary.json       # TB 7×5 full
experiments/metrics/t3_aci_rerun_pilot_summary.json    # TB 3×5 ACI rerun
experiments/metrics/real_task_*_summary.json           # T7 ablations
```

Trajectories under `experiments/llm_runs/` are gitignored; regenerate via [`docs/artifact_reproducibility.md`](docs/artifact_reproducibility.md).

---

## Quick Start

```bash
# Tests (120 pass, 2 skip)
python3 -m unittest discover -s tests

# Code suite eval (requires .env — copy from .env.example)
python3 experiments/real_benchmarks/run_real_llm_eval.py --suite code_all --family cascade

# Analysis (replay only, no LLM)
python3 experiments/analysis/t4_statistics.py
python3 experiments/analysis/oracle_route_matrix.py

# Terminal-Bench (Docker required)
bash experiments/terminal_bench/run_tb_full_async.sh
```

---

## Repository Layout

```
src/agent_attention_runtime.py       # core runtime (routing, gates, memory, trajectories)
experiments/cascade/                 # cascade policies + wave3 eval
experiments/analysis/                # oracle route, T4, briefs D/E/G, TB comparison
experiments/real_benchmarks/         # LLM client, executors, unified eval runner
experiments/terminal_bench/          # TB adapter + multi-step shell loop
experiments/metrics/                 # committed summary JSON
docs/next_iteration/                 # task reports + research directions
docs/deliverables/08/                # result tables for paper
tests/                               # unit tests
```

---

## Research Goal

Measure when **sparse cascade routing** improves **cost-adjusted success** vs fixed workflows, ReAct, retrieval memory, and MoA — with executable end-task oracles and matched budgets.

Positioning: [`docs/research_memo.md`](docs/research_memo.md) · [`docs/deliverables/01/gap_analysis.md`](docs/deliverables/01/gap_analysis.md)

---

## Milestone Timeline

| Date | Milestone |
|------|-----------|
| 2026-06-26 | Toy Phases 1–4, real LLM harness, code verifier |
| 2026-06-30 | Wave 3 exploration, cascade eval, TB ACI, T4/T6/T7 |
| 2026-07-01 | TB full 7×5 matrix complete (steps=12); README results refresh |

**Next code sprint:** expert v2 modules per [`docs/next_iteration/research_directions/07_expert_redesign_proposal.md`](docs/next_iteration/research_directions/07_expert_redesign_proposal.md)
