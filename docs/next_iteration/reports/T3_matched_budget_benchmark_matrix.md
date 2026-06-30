# T3: Matched-Budget Benchmark Matrix (Pilot)

Date: 2026-06-30  
Status: **Pilot complete** — multi-step shell agent + 3 tasks × 5 baselines (15 runs). Full 7-task manifest ready.

## scope

First publication-relevant Terminal-Bench matrix under matched budgets, using pre-registered no-apt subset.

## key_change

Replaced single-shot faithful→shell bridge with **multi-step observe→act loop** (`experiments/terminal_bench/tb_shell_loop.py`):

- Up to 8 shell steps per task
- Baseline-specific prompts (ReAct, fixed workflow phases, memory, MoA, AA)
- Terminal output fed back each turn via `session.get_incremental_output()`

## matched_budget

| Parameter | Value |
|-----------|-------|
| Model | `Qwen3-30B-A3B-Instruct-2507` (Paratera) |
| max_shell_steps | 8 |
| max_tokens_per_call | 512 |
| timeout_s | 900 |
| n_concurrent | 1 |

Manifest: `experiments/tasks/terminal_bench_subset_manifest.json`

## pilot_results (3 tasks × 5 baselines)

| Baseline | Pass rate | Mean latency |
|----------|-----------|--------------|
| single_react_llm_agent | 1/3 (33%) | 121s |
| fixed_workflow_llm_agent | 1/3 (33%) | 194s |
| retrieval_memory_llm_agent | 1/3 (33%) | 194s |
| moa_style_llm_agent | 1/3 (33%) | 126s |
| agent_attention_llm_tuned | 0/3 (0%) | 120s |

**Shared pass:** `fix-permissions` (4/4 non-AA baselines; AA failed env on this run).

| Task | Passes (of 5 baselines) |
|------|-------------------------|
| fix-permissions | 4 |
| fibonacci-server | 0 |
| configure-git-webserver | 0 |

Failure breakdown: 4 pass, 5 environment, 6 agent (pilot).

## artifacts

- Summary: `experiments/metrics/terminal_bench_matrix_summary.json`
- Run log: `experiments/metrics/t3_pilot_run.log`
- Trajectories: `experiments/llm_runs/terminal_bench/t3/`
- Runner: `experiments/terminal_bench/run_t3_matrix.py`

## commands

```bash
cd /home/myuser/Agent
source scripts/benchmark-env.sh

# Pilot (3 tasks)
python3 experiments/terminal_bench/run_t3_matrix.py --limit-tasks 3

# Full manifest (7 tasks × 5 baselines ≈ 38 min)
python3 experiments/terminal_bench/run_t3_matrix.py
```

## interpretation

- Multi-step loop **fixes simple tasks** consistently (fix-permissions 4/5 vs 1–2/5 in T2 single-shot).
- Harder tasks still fail: server/git setup needs more steps or stronger models.
- Several failures are **environment** (apt/ghcr during test setup) — not agent quality.
- T3 is **pilot-only** (< 20 tasks); full manifest expansion or TB subset registration needed for publication.

## next

1. ~~Re-run T3 pilot with ACI patches~~ **Done** — see `experiments/analysis/t3_aci_rerun_comparison.md` (4/15 pass, env 33%→20%, invalid-shell 0%).
2. Run full 7-task manifest after env failure < 10% on pilot.
3. **T4:** bootstrap CIs from `per_task` rows in summary JSON.
4. Increase `max_shell_steps` to 12 for server tasks; log `parse_status` in envelopes.
5. **Brief E/D:** learned router diagnostic + outcome memory (next wave).

## aci_rerun (2026-06-30)

Post-patch 3×5 matrix (`experiments/metrics/t3_aci_rerun_pilot_summary.json`):

| Metric | Before | After |
|--------|--------|-------|
| Pass | 4/15 | 4/15 |
| Env failure | 5/15 | 3/15 |
| Agent failure | 6/15 | 8/15 |
| Invalid-shell step rate | ~4% | 0% |
| AA tuned | 0/3 | 1/3 |

Async rerun: `bash experiments/terminal_bench/run_t3_pilot_async.sh`

## acceptance vs T3 criteria

| Criterion | Status |
|-----------|--------|
| Same tasks all baselines | Yes (pilot subset) |
| Same model/budget | Yes |
| End-task from TB verifier | Yes |
| ≥ 20 tasks | **No** — pilot 3/7; explain in report |
| 4+ baselines | Yes (5) |
