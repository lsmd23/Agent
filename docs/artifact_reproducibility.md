# Artifact Reproducibility

Date: 2026-06-30

## Environment

```bash
# WSL2 Linux recommended; Docker required for Terminal-Bench
python3 --version   # 3.10+
git clone <repo> && cd Agent
cp .env.example .env  # fill OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL — never commit .env
source scripts/benchmark-env.sh  # if present
python3 -m unittest discover -s tests
python3 experiments/real_benchmarks/check_llm_environment.py --probe-chat
```

## External benchmarks

```bash
# Terminal-Bench core (gitignored under external/)
# Clone per docs/next_iteration/setup-docker-wsl.md
```

## Regenerate key results (no secrets in output)

### Code suite (26 tasks, requires LLM API)

```bash
python3 experiments/real_benchmarks/run_real_llm_eval.py \
  --suite code_all --family faithful --output-dir experiments/llm_runs/code_full_matrix

python3 experiments/real_benchmarks/run_real_llm_eval.py \
  --suite code_all --family cascade --output-dir experiments/llm_runs/code_cascade_wave3
```

### Analysis (replay only, no LLM)

```bash
python3 experiments/analysis/oracle_route_matrix.py
python3 experiments/cascade/run_cascade_pilot.py --mode replay
python3 experiments/analysis/t4_statistics.py
python3 experiments/analysis/route_selector_diagnostic.py
python3 experiments/analysis/outcome_memory_router.py
python3 experiments/analysis/real_task_backprop_diagnostic.py
python3 experiments/analysis/t7_consolidate.py
```

### Terminal-Bench (Docker + LLM)

```bash
# 3-task ACI pilot
bash experiments/terminal_bench/run_t3_pilot_async.sh

# Full 7-task, 12 steps
bash experiments/terminal_bench/run_tb_full_async.sh
```

## Expected output files

| Artifact | Path |
|----------|------|
| Code matrix summary | `experiments/metrics/code_full_matrix_summary.json` |
| Cascade wave3 + CI | `experiments/metrics/code_cascade_wave3_with_ci.json` |
| T4 Pareto | `experiments/metrics/t4_pareto_summary.json` |
| Oracle routes | `experiments/metrics/oracle_route_matrix.json` |
| T7 ablations | `experiments/metrics/real_task_*_summary.json` |
| TB T3 rerun | `experiments/metrics/t3_aci_rerun_pilot_summary.json` |
| TB full (steps12) | `experiments/metrics/t3_full_steps12_summary.json` |

## Trajectories

`experiments/llm_runs/` and `experiments/trajectories/` are **gitignored**. Summaries under `experiments/metrics/` are durable.

## Tests

```bash
python3 -m unittest discover -s tests   # expect 120+ pass, 2 skip
```

## Secret handling

- Never commit `.env`, API keys, or raw provider responses with credentials.
- Logs may contain prompts — review before sharing.

## Synthesis docs

- Wave 3: `docs/next_iteration/reports/W1_wave3_exploration_synthesis.md`
- T4: `docs/next_iteration/reports/T4_statistics_and_pareto.md`
- T7: `docs/next_iteration/reports/T7_real_task_ablations.md`
- T6: `docs/next_iteration/reports/T6_paper_artifact_packaging.md`
