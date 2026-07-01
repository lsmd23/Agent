# Project Status

Last updated: 2026-06-30

## Milestone: Iteration Goals Complete (Workshop Tier)

All `docs/next_iteration` tasks T0–T7 and research briefs A–H executed. Completion checklist: `docs/next_iteration/reports/W2_complete_iteration_goals.md`.

**Default routing policy:** `cascade_react_aa_lite_llm` (100% @ 1.50 mean calls, N=26 code suite).

## What Works

### Code suite (26 tasks, real LLM + replay analysis)

| Component | Result |
|-----------|--------|
| Cascade AA lite | 100% @ 1.50 calls — **Pareto frontier** |
| Oracle route gap | +0.24 cost-normalized |
| Always-on AA tuned | 84.6% — refuted as default |
| T4 bootstrap CI | `t4_code_suite_with_ci.json` |
| Brief E router | weak — 50% held-out route accuracy |
| Brief D memory | weak — Δ regret +0.001 |
| Brief G backprop | 0/4 accept |

### Terminal-Bench

| Run | Status |
|-----|--------|
| T3 pilot + ACI rerun | 4/15 pass; invalid-shell 0% |
| Full 7×5 steps=12 | **Running** in tmux `tb_full` |

### Tests

```bash
python3 -m unittest discover -s tests   # 120 pass, 2 skip
```

## Key Docs

| Doc | Purpose |
|-----|---------|
| `W2_complete_iteration_goals.md` | Full checklist |
| `T4_statistics_and_pareto.md` | CI + Pareto |
| `T6_paper_artifact_packaging.md` | Paper pack |
| `T7_real_task_ablations.md` | Router/memory/backprop |
| `docs/paper_outline.md` | Draft paper |
| `docs/artifact_reproducibility.md` | Reproduce results |
| `research_directions/07_expert_redesign_proposal.md` | Next code sprint |
| `docs/direction_07_01/README.md` | Next subagent exploration pack |

## Blocked / Deferred

- Main-track paper (need ≥50 public tasks).
- Expert v2 implementation (Brief H redesign doc only).
- ADAS workflow search (track 10).

## Async

```bash
tmux attach -t tb_full
find experiments/llm_runs/terminal_bench/t3_full_steps12 -name '*envelope.json' | wc -l  # target 35
```
