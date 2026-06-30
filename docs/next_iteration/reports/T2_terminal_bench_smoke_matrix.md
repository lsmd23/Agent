# T2: Terminal-Bench Smoke Matrix

Date: 2026-06-30  
Status: **Complete** — oracle validated; faithful baselines end-to-end on 5 tasks × 3 baselines (15 runs).

## scope

Run a tiny real benchmark matrix (5 tasks × 3 baselines) to validate adapter, logging, and end-task scoring.

## environment_observed

| Check | Status |
|-------|--------|
| `/var/run/docker.sock` | **Present** (WSL integration enabled) |
| `docker ps` (CLI) | OK |
| Python docker SDK (`tb` uv env) | **OK** (docker group; agent uses `sg docker` fallback) |
| LLM API | OK — `Qwen3-30B-A3B-Instruct-2507` via Paratera |

## work_completed

1. Oracle smoke on `fix-permissions`: **1/1 resolved** (`1782790169`, ~48s).
2. Fixed faithful TB agent: load `.env`, pass `model_name` kwarg, shell command bridge (no longer executes Python `# file:` patches as shell).
3. Faithful smoke on `fix-permissions` (3 baselines):
   - `single_react_llm_agent`: **pass** (~49s)
   - `fixed_workflow_llm_agent`: **pass** (~57s)
   - `agent_attention_llm_tuned`: **fail** (~51s)
4. Full T2 matrix: **5 tasks × 3 baselines = 15 runs** (~24 min wall time).

## commands_run

```bash
cd /home/myuser/Agent
source scripts/benchmark-env.sh

# Oracle validation
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --mode tb --use-oracle --task-id fix-permissions

# Faithful smokes
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --mode tb --task-id fix-permissions --baseline single_react_llm_agent
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --mode tb --task-id fix-permissions --baseline agent_attention_llm_tuned
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --mode tb --task-id fix-permissions --baseline fixed_workflow_llm_agent

# Full matrix
python3 experiments/terminal_bench/run_terminal_bench_matrix.py \
  --summary-output experiments/metrics/terminal_bench_smoke_summary.json
```

## results

### Oracle (harness validation)

| Run | Task | Result |
|-----|------|--------|
| `1782790169` | fix-permissions | **1/1 resolved** |

### Faithful matrix (5 tasks × 3 baselines)

Tasks: `fix-permissions`, `fibonacci-server`, `configure-git-webserver`, `count-dataset-tokens`, `download-youtube`

| Baseline | End-task pass | Mean latency |
|----------|---------------|--------------|
| single_react_llm_agent | **1/5 (20%)** | 90.9s |
| fixed_workflow_llm_agent | **1/5 (20%)** | 136.3s |
| agent_attention_llm_tuned | **0/5 (0%)** | 60.2s |

**Only shared pass:** `fix-permissions` (single_react + fixed_workflow).

Per-run detail: `experiments/metrics/t2_matrix_run.log`  
Summary JSON: `experiments/metrics/terminal_bench_smoke_summary.json`

### Local executable matrix (prior, 5 × 3)

| Baseline | End-task pass |
|----------|---------------|
| single_react_llm_agent | 5/5 |
| fixed_workflow_llm_agent | 1/5 |
| agent_attention_llm_tuned | 5/5 |

Summary: `experiments/metrics/t2_local_code_matrix_summary.json`

## interpretation

- **Harness + scoring pipeline is validated** (oracle 100%, faithful runs complete without infra errors).
- **Faithful→shell bridge works on simple tasks** (`fix-permissions` = chmod) but fails on multi-step terminal tasks (server setup, git, token counting, youtube download).
- Gap vs local code suite: code tasks use patch extraction + pytest; TB tasks need iterative shell ReAct (currently single-shot command batch after one faithful trajectory).
- `agent_attention_llm_tuned` underperforms on TB despite strong local code results — likely routing overhead + weaker command bridge for terminal tasks.

## next_recommended_action

1. **T3 prep:** add multi-step TB agent loop (observe shell output → replan) instead of single command batch.
2. **Improve command bridge:** task-specific prompts, reject prose, validate commands before send.
3. **Expand matrix** once multi-step agent lands; keep no-apt tasks for CI stability.
4. Optional: run full local code eval on `phase1_code_all.jsonl` (26 × 3) in parallel track.

## T3 justified?

**Yes for infrastructure** — TB end-to-end runs are stable.  
**Partial for science** — need multi-step terminal agent before matched-budget TB comparison is meaningful.
