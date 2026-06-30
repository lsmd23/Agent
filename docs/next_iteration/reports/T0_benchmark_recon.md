# T0 Benchmark Reconnaissance

Date: 2026-06-29  
Agent: Cartographer  
Companion: `T0_environment_report.md`

## scope

Inspect official Terminal-Bench / Harbor and SWE-bench sources, compare requirements against the observed WSL2 environment, and recommend the primary benchmark path plus one exact smoke command for the next agent.

## environment_observed

See `T0_environment_report.md`. Summary relevant to benchmarks:

- Docker Desktop: usable via Windows binary, not default WSL `docker`
- RAM: 7.6 GiB (tight)
- Disk: 949 GiB free (good)
- pip/uv: missing
- Existing local executable harness: working (6 code tasks, unittest verifier)
- Remote LLM API: working (Qwen3-30B via OpenAI-compatible endpoint)

## work_completed

1. Read project docs: `docs/next_iteration/README.md`, `docs/project_status.md`, `.env.example`, `real_llm_bench_memo.md`.
2. Inspected official Terminal-Bench README (`harbor-framework/terminal-bench` on GitHub).
3. Inspected SWE-bench installation/requirements via official docs (`swebench.com`).
4. Mapped each benchmark path to current runnable / blocked / fallback status.
5. Drafted install + smoke plan for T1 without cloning large repos into tracked paths.

## commands_run

Documentation and environment probes only for external benchmarks (no benchmark repo cloned into tracked tree). See environment report for shell commands.

Official sources consulted:

- Terminal-Bench repo: https://github.com/harbor-framework/terminal-bench
- Harbor (successor framework): https://github.com/harbor-framework/harbor
- Terminal-Bench docs: https://www.tbench.ai/
- SWE-bench repo: https://github.com/swe-bench/SWE-bench
- SWE-bench Lite: https://www.swebench.com/lite.html
- SWE-bench installation: https://www.swebench.com/SWE-bench/installation/
- SWE-bench Docker guide: https://www.swebench.com/SWE-bench/guides/docker_setup/

## artifacts_created

- `docs/next_iteration/reports/T0_benchmark_recon.md` (this file)
- `docs/next_iteration/reports/T0_environment_report.md`

## results

### Benchmark path assessment

| Path | Docker required | Official requirements | Current status | Recommendation |
|------|-----------------|----------------------|----------------|----------------|
| **Terminal-Bench (`tb`)** | Yes (sandboxed terminal) | `pip install terminal-bench`, `uv`, Docker; dataset `terminal-bench-core` v0.1.1 | **Blocked on pip/uv install**; Docker reachable via wrapper; RAM may limit concurrency | **Primary target** once pip + docker alias installed |
| **Harbor framework** | Yes | New official runner for Terminal-Bench 2.0; adapter-based | Same blockers as above; inspect after `terminal-bench` smoke | **Primary long-term**; start with legacy `tb` CLI for T1 if Harbor docs lag |
| **Terminal-Bench legacy in-repo harness** | Yes | Clone + Docker | Not probed (avoid large tracked clone); use pip package first | Defer |
| **SWE-bench Lite / Verified** | Yes | Python 3.9+, Docker, **16 GiB RAM**, **120 GiB Docker disk**, x86_64 | **Blocked on RAM** (7.6 GiB) and pip; Docker otherwise OK | **Secondary** — use cloud/modal or upgrade RAM before local full eval |
| **Local pytest fixture suite** | No | Existing repo fixtures + unittest verifier | **Runnable now**; v2 real-LLM end-task 95.2% (40/42) | **Immediate fallback + T5 expansion** |
| **GSM8K harness (existing)** | No | Remote/local LLM | Runnable | Sanity check only (evidence level 3) |

### Recommended primary benchmark path

**Primary (publication target): Terminal-Bench via `terminal-bench` pip package (`tb run`), with Harbor as the follow-on framework once the adapter exists.**

Reasons:

- Matches paper direction: realistic executable terminal agent tasks with test scripts.
- Lower immediate setup than SWE-bench full Docker image farm for a first end-to-end path.
- Aligns with task graph T1 → T2 → T3.

**Parallel controlled path (no Docker): expand local executable code suite (T5)** while Terminal-Bench tooling is being wired. This keeps iteration unblocked and produces level-2 evidence (executable local fixtures).

**Defer SWE-bench Lite locally** until RAM ≥ 16 GiB or evaluation runs on Modal/cloud (`--modal true` per upstream docs).

### Benchmark setup memo

#### A. Terminal-Bench (recommended next)

**Prerequisites**

| Item | Requirement | Current |
|------|-------------|---------|
| Python | 3.10+ | OK |
| pip or uv | Required | **Install needed** |
| Docker | Required | OK via `scripts/wsl-docker.sh` |
| RAM | Not officially specified; plan for 1–2 concurrent sandboxes on 8 GiB host | Tight — start with `--n-concurrent 1` |
| Disk | Task images + logs | OK (949 GiB free on host) |

**Suggested install (run in WSL, caches under `external/`, not committed)**

```bash
cd /home/myuser/Agent
sudo apt update && sudo apt install -y python3-pip
pip3 install uv terminal-bench
mkdir -p external
alias docker="$PWD/scripts/wsl-docker.sh"
tb run --help
```

**First smoke after install**

```bash
tb run \
  --agent terminus \
  --model openai/Qwen3-30B-A3B-Instruct-2507 \
  --dataset-name terminal-bench-core \
  --dataset-version 0.1.1 \
  --n-concurrent 1 \
  --limit 1
```

Adjust model string and API env vars to match the project's OpenAI-compatible `.env` (never commit secrets). If `tb` cannot use the Paratera endpoint out of the box, T1 should add an adapter config rather than hardcoding keys.

**Expected artifacts**

- Terminal-Bench run logs under user cache / cwd (keep out of git)
- Adapter code under `experiments/` (T1 deliverable)

#### B. SWE-bench Lite (secondary, currently poor fit locally)

**Install sketch**

```bash
git clone https://github.com/swe-bench/SWE-bench.git external/SWE-bench
cd external/SWE-bench && pip3 install -e .
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Lite \
  --predictions_path gold \
  --max_workers 1 \
  --run_id validate-gold
```

**Blockers today:** 7.6 GiB RAM vs 16 GiB recommended; Docker Desktop disk image may need expansion to ~120 GiB inside Docker settings; first run downloads/builds many images.

#### C. Local pytest fallback (runnable now)

**Install:** none (stdlib unittest).

**Smoke**

```bash
python3 experiments/real_benchmarks/validate_code_fixtures.py
```

**Single-task real-LLM executable smoke**

```bash
python3 experiments/real_benchmarks/run_real_llm_eval.py \
  --tasks experiments/tasks/phase1_code_tasks.jsonl \
  --family faithful \
  --baselines single_react_llm_agent \
  --limit 1 \
  --output-dir experiments/llm_runs/t0_smoke \
  --summary-output experiments/metrics/t0_local_code_smoke.json
```

### Evidence hierarchy mapping

| Benchmark | Evidence level | Paper use |
|-----------|----------------|-----------|
| Terminal-Bench end-task pass | 1 | Main table candidate |
| Local pytest fixtures | 2 | Controlled ablations / development |
| GSM8K exact match | 3 | Sanity only |
| Phase1 route-proxy | 4–5 | Diagnostics appendix |

## risks_or_blockers

1. **Terminal-Bench not yet installed** — T1 must install and probe; do not claim end-to-end Terminal-Bench runs until `tb run` succeeds.
2. **RAM headroom** — concurrent sandboxes + LLM calls on 7.6 GiB may OOM; use concurrency 1.
3. **SWE-bench local eval** — officially resource-heavy; not recommended as first path on this machine.
4. **API/model adapter unknown** — Terminal-Bench default agents may expect Anthropic/OpenAI URLs; Paratera endpoint may need custom agent wiring in T1.
5. **No external clones in repo yet** — intentional; keep caches in `external/` (gitignored).

## next_recommended_action

**Assign T1 (Terminal-Bench adapter)** with this exact first command after pip install:

```bash
alias docker='/home/myuser/Agent/scripts/wsl-docker.sh'
pip3 install terminal-bench
tb run --help
```

If `tb run` cannot start sandboxes or install fails, T1 must:

1. Document the blocker in `docs/next_iteration/reports/T1_terminal_bench_adapter.md`
2. Ship adapter skeleton + **local pytest fallback** smoke using:

```bash
python3 experiments/real_benchmarks/validate_code_fixtures.py
```

**Parallel track:** dispatch **T5** to expand local fixtures toward ≥50 tasks while T1 unblocks Terminal-Bench.
