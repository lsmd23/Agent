# Wave 2: Complete Iteration Goals Checklist

Date: 2026-06-30  
Status: **All documented exploration goals executed or explicitly closed**

## Task graph (next_iteration)

| Task | Status | Report |
|------|--------|--------|
| T0 Environment + recon | Done (prior) | `T0_*` |
| T1 TB adapter | Done | `T1_terminal_bench_adapter.md` |
| T2 Smoke matrix | Done | `T2_terminal_bench_smoke_matrix.md` |
| T3 Matched-budget matrix | Done + ACI rerun | `T3_matched_budget_benchmark_matrix.md` |
| T4 Statistics + Pareto | Done | `T4_statistics_and_pareto.md` |
| T5 Code suite expansion | Done (26 tasks, prior) | `T5_local_code_suite_expansion.md` |
| T6 Paper artifact pack | Done (workshop tier) | `T6_paper_artifact_packaging.md` |
| T7 Real-task ablations | Done (diagnostic) | `T7_real_task_ablations.md` |

## Research direction briefs

| Brief | Status | Outcome |
|-------|--------|---------|
| A Oracle route | Done | supports_direction |
| B Cascade | Done | supports_direction |
| C AA ablation | Done | supports_direction |
| D Outcome memory | Done | weak_or_inconclusive |
| E Learned router | Done | weak_or_inconclusive |
| F TB ACI | Done + rerun | supports_direction |
| G Executable backprop | Done | falsified_or_blocked |
| H Expert specialization | Done | falsified_or_blocked |

## Wave 3 tracks (04_exploration_tracks)

| Track | Status |
|-------|--------|
| 1 Cascade | Done |
| 2 AA ablation | Done |
| 3 Oracle matrix | Done |
| 4 MoA fallback | Partial (in cascade) |
| 5 Outcome memory | Done (weak) |
| 6 Learned router | Done (weak) |
| 7 Textual backprop | Done (blocked) |
| 8 TB ACI | Done |
| 9 TB 20+ matrix | **In progress** — 7×5 steps=12 in tmux `tb_full` |
| 10 ADAS search | Deferred (premature) |

## Expert redesign

Documented: `research_directions/07_expert_redesign_proposal.md` — implementation deferred to next code sprint.

## Async jobs

| Session | Job | Expected |
|---------|-----|----------|
| `tb_full` | 7 tasks × 5 baselines, steps=12 | 35 envelopes |

Monitor: `find experiments/llm_runs/terminal_bench/t3_full_steps12 -name '*envelope.json' | wc -l`

## Main-track paper gate

| Criterion | Met? |
|-----------|------|
| Public benchmark E2E | Partial (TB adapter) |
| ≥50 tasks | No (26 code + ≤7 TB) |
| 4+ baselines | Yes |
| AA cost-quality win + CI | Yes on code N=26 only |
| Failure analysis | Yes |

**Verdict:** Workshop/demo ready; main-track blocked on scale + TB stability.

## Recommended post-checklist actions

1. Wait for `tb_full` → update T3 report + abstract if env/pass improves.
2. Implement expert v2 modules per `07_expert_redesign_proposal.md`.
3. Optional LaTeX from `docs/paper_outline.md`.
