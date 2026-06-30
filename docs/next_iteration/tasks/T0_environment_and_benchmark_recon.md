# T0: Environment And Benchmark Reconnaissance

Suggested agent: Cartographer

## Objective

Establish the exact local execution environment and produce a practical benchmark acquisition plan. This is the required first task before Terminal-Bench, SWE-bench, or any larger executable evaluation.

## Context

Current observed environment:

- WSL2 Linux
- Python 3.10.12
- Git available
- Docker not currently usable inside WSL
- About 7.6GiB RAM
- Large disk headroom
- OpenAI-compatible LLM endpoint configured through `.env` or shell environment

Do not trust this snapshot blindly. Re-check it.

## Required Reads

- `docs/next_iteration/README.md`
- `docs/project_status.md`
- `.env.example`
- `experiments/real_benchmarks/check_llm_environment.py`
- `experiments/real_benchmarks/real_llm_bench_memo.md`

## Required Work

1. Run and record local environment checks:

```bash
pwd
uname -a
python3 --version
git --version
docker --version
df -h .
free -h
python3 -m unittest discover -s tests
python3 experiments/real_benchmarks/check_llm_environment.py --probe-chat
```

2. Inspect official benchmark sources:

- Terminal-Bench / Harbor:
  - `https://github.com/harbor-framework/terminal-bench`
  - `https://github.com/harbor-framework/harbor`
  - `https://www.tbench.ai/`
- SWE-bench:
  - `https://github.com/swe-bench/SWE-bench`
  - `https://www.swebench.com/lite.html`

3. Determine which benchmark path is currently runnable:

- Terminal-Bench through Harbor.
- Terminal-Bench legacy CLI if still supported.
- SWE-bench Lite/Verified.
- Local pytest fixture expansion as a fallback.

4. Produce a benchmark setup memo with exact install commands, expected disk/RAM requirements, Docker requirement, and first smoke command.

## Deliverables

Create:

- `docs/next_iteration/reports/T0_environment_report.md`
- `docs/next_iteration/reports/T0_benchmark_recon.md`

If code/config changes are required, make the smallest possible change and document it.

## Acceptance Criteria

- The report says whether Docker is usable from WSL.
- The report identifies the recommended primary benchmark path.
- The report includes one exact smoke command for the next agent.
- No secret is printed or committed.

## Failure Modes

- Treating a web search result as enough without installing or probing.
- Assuming Terminal-Bench can run without Docker.
- Writing API keys into docs or shell history snippets.
- Cloning large external repos into tracked source paths.
