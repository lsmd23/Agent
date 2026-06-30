# T1: Terminal-Bench Adapter

Date: 2026-06-29  
Agent: Bridger

## scope

Build the first Terminal-Bench adapter so Agent-Attention faithful LLM baselines can target TB-style tasks, emit trajectory envelopes, and fall back to the local executable code suite when the TB harness cannot start sandboxes.

## environment_observed

- WSL2, Python 3.10.12 (project tests); Terminal-Bench CLI via uv tool env (Python 3.13)
- Docker Desktop CLI works through `scripts/docker` → Windows `docker.exe`
- **`/var/run/docker.sock` missing** — Python `docker` SDK used by `tb run` fails inside harness trials
- Dataset `terminal-bench-core==0.1.1` downloaded to `external/terminal-bench-core` (80 tasks, `task.yaml` layout)
- LLM API reachable (Paratera-compatible endpoint)

## work_completed

1. Installed Terminal-Bench CLI (`uv tool install terminal-bench`, v0.2.18).
2. Added `scripts/docker` symlink, `scripts/benchmark-env.sh`, and `docs/next_iteration/setup-docker-wsl.md`.
3. Implemented:
   - `experiments/terminal_bench/adapter.py` — task listing, `tb run` command builder, envelope mapping, local fallback
   - `experiments/terminal_bench/faithful_tb_agent.py` — `FaithfulTBAgent` (`BaseAgent`) for `single_react_llm_agent`, `fixed_workflow_llm_agent`, `agent_attention_llm_tuned`
   - `experiments/terminal_bench/run_terminal_bench_smoke.py` — smoke / dry-run entrypoint
4. Added `tests/test_terminal_bench_adapter.py` (7 tests; 2 skip when TB not importable from system Python).
5. Probed `tb run` with oracle agent on `csv-to-parquet` — harness invoked, trial failed with `unknown_agent_error` due to Docker SDK socket (documented).

## commands_run

```bash
ln -sf wsl-docker.sh scripts/docker
uv tool install terminal-bench
tb datasets download -d terminal-bench-core==0.1.1 --output-dir external/terminal-bench-core
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --dry-run
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --mode tb --use-oracle --task-id csv-to-parquet
python3 -m unittest discover -s tests
```

## artifacts_created

| Path | Purpose |
|------|---------|
| `experiments/terminal_bench/adapter.py` | Core adapter + fallback |
| `experiments/terminal_bench/faithful_tb_agent.py` | Custom TB agent |
| `experiments/terminal_bench/run_terminal_bench_smoke.py` | Smoke runner |
| `tests/test_terminal_bench_adapter.py` | Unit tests |
| `scripts/benchmark-env.sh` | PATH + docker notes |
| `scripts/docker` | Docker Desktop wrapper |
| `docs/next_iteration/setup-docker-wsl.md` | WSL Docker integration guide |
| `external/terminal-bench-core/` | Downloaded dataset (gitignored) |

## results

| Check | Result |
|-------|--------|
| Unit tests | **66/66 pass** (2 skipped) |
| List TB tasks | **80 tasks** detected via `task.yaml` |
| `tb run` oracle smoke | Harness started; **0/1 resolved** — Docker SDK socket missing in WSL |
| Local fallback path | Implemented; uses existing `run_faithful_llm` |

**Envelope fields emitted:** `benchmark_id`, `task_id`, `baseline_id`, provider/model (no secrets), `final_success_label`, `failure_type`, `raw_log_dir`, TB return code.

## risks_or_blockers

1. **Primary blocker:** Enable Docker Desktop **WSL Integration** so `/var/run/docker.sock` exists for Python `docker.from_env()`.
2. TB harness failure mode `unknown_agent_error` on smoke until socket fixed (see `results.json` under `experiments/llm_runs/terminal_bench/smoke/`).
3. `FaithfulTBAgent` bridges faithful runtime output → shell commands via follow-up LLM call; may need task-specific command templates after socket fix.

## next_recommended_action

**For T2 agent — after WSL Docker socket fix:**

```bash
source scripts/benchmark-env.sh
python3 experiments/terminal_bench/run_terminal_bench_smoke.py \
  --mode tb \
  --baseline single_react_llm_agent \
  --task-id csv-to-parquet
```

**If socket still missing, run local fallback smoke:**

```bash
python3 experiments/terminal_bench/run_terminal_bench_smoke.py --mode local --limit 1
```

Then expand to 5–10 tasks (`--task-id` list or `--n-tasks 5`) across three baselines.
