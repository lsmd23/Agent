# T0 Environment Report

Date: 2026-06-29  
Agent: Cartographer  
Task: `docs/next_iteration/tasks/T0_environment_and_benchmark_recon.md`

## scope

Re-verify the WSL2 execution environment for the next publication iteration: OS, Python, Git, Docker, memory/disk, test suite, and LLM API connectivity. No secrets were printed or committed.

## environment_observed

| Resource | Observed value | Notes |
|----------|----------------|-------|
| Workspace | `/home/myuser/Agent` | Git repo on `main` |
| OS | WSL2 Linux `6.6.114.1-microsoft-standard-WSL2`, x86_64 | `Linux LAPTOP-FJCGEMA0` |
| Python | **3.10.12** (`/usr/bin/python3`) | Meets SWE-bench 3.9+ requirement |
| pip / uv | **Not installed** in WSL | `pip3`, `python3 -m pip`, and `uv` unavailable |
| Git | **2.34.1** | Available |
| Docker (WSL `PATH`) | **Not found** | `docker --version` fails |
| Docker Desktop (Windows) | **Available and running** | Client+server via `docker.exe`; `hello-world` succeeded |
| CPU | **32 logical cores** | Adequate for harness concurrency in theory |
| RAM | **7.6 GiB total**, ~5.8 GiB available | Below SWE-bench recommended 16 GiB |
| Swap | 2.0 GiB | Present, unused at check time |
| Disk (workspace mount) | **949 GiB free** of 1007 GiB | Meets large benchmark cache needs on host disk |
| GPU | None | `nvidia-smi` unavailable |
| Unit tests | **57/57 pass** | `python3 -m unittest discover -s tests` |
| Ollama | Reachable at `http://localhost:11434` | Model `llama3.1:8b`; CLI not in WSL PATH |
| OpenAI-compatible API | **Configured** | `api_key_set=true`, base URL Paratera-compatible endpoint, model `Qwen3-30B-A3B-Instruct-2507` |
| Chat probe | **OK** | Latency ~791 ms, output `OK` (no key printed) |

### Docker verdict for WSL

**Partially usable today.**

- Native WSL `docker` is **not** on `PATH`.
- Docker Desktop **is** usable from WSL through the Windows binary:

```bash
"/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" version
"/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" run --rm hello-world
```

Both succeeded during T0. For repeatable use, add repo helper `scripts/wsl-docker.sh` or symlink/alias `docker` to that binary.

Docker is **not** absent; it is **not integrated into the default WSL shell PATH**.

## work_completed

1. Re-ran all required environment commands from the T0 task file.
2. Probed Docker Desktop through the Windows executable from WSL.
3. Ran full unit test suite and LLM environment check with `--probe-chat`.
4. Validated local executable code fixture harness still passes.
5. Saved machine-readable environment snapshot to `experiments/metrics/t0_environment_check.json`.
6. Added `scripts/wsl-docker.sh` wrapper and `external/` gitignore entry for future benchmark clones.

## commands_run

```bash
pwd
uname -a
python3 --version
git --version
docker --version                    # failed: not in PATH
df -h .
free -h
nproc
python3 -m unittest discover -s tests
python3 experiments/real_benchmarks/check_llm_environment.py --probe-chat \
  --json-output experiments/metrics/t0_environment_check.json
python3 experiments/real_benchmarks/validate_code_fixtures.py
"/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" version
"/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe" run --rm hello-world
```

## artifacts_created

- `docs/next_iteration/reports/T0_environment_report.md` (this file)
- `docs/next_iteration/reports/T0_benchmark_recon.md`
- `experiments/metrics/t0_environment_check.json`
- `scripts/wsl-docker.sh`

## results

| Check | Result |
|-------|--------|
| Tests | PASS (57/57) |
| LLM chat probe | PASS |
| Local code fixtures | PASS (5/5 broken-fail, golden-pass) |
| Docker Desktop from WSL | PASS (`hello-world`) |
| Native WSL docker CLI | FAIL (not installed on PATH) |
| Package installer (pip/uv) | FAIL (missing) |

## risks_or_blockers

1. **Missing pip/uv** — cannot install `terminal-bench`, `harbor`, or `swe-bench` until `python3-pip` or `uv` is installed.
2. **Low RAM (7.6 GiB)** — below SWE-bench official guidance (16 GiB+). Terminal-Bench sandboxes may also be tight with concurrent runs.
3. **Docker PATH friction** — agents/scripts that call bare `docker` will fail unless wrapper or PATH fix is applied.
4. **No GPU** — local Ollama is CPU-only; large real-agent runs should prefer configured remote API (already working).
5. **Push auth** — unrelated to benchmarks, but GitHub push from Cursor agent shell still lacks credentials; use local terminal.

## next_recommended_action

**For T1 (Terminal-Bench adapter):**

1. Install tooling:

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install uv  # optional but recommended by Terminal-Bench docs
export PATH="$PWD/scripts:$PATH"   # after adding docker wrapper to PATH via alias below
alias docker='/home/myuser/Agent/scripts/wsl-docker.sh'
```

2. Install harness (probe only, do not commit external caches):

```bash
mkdir -p external && pip3 install terminal-bench
tb run --help
```

3. If Terminal-Bench install/run fails on RAM or sandbox issues, **stop and implement adapter skeleton + local pytest fallback** per T1 instructions.

**Immediate no-Docker smoke for any agent (runnable now):**

```bash
python3 experiments/real_benchmarks/validate_code_fixtures.py
```
