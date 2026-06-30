# Next Iteration Agent Handbook

Date: 2026-06-29

This directory is the handoff pack for the next research iteration. It is written for future agents that will be manually dispatched by the project owner.

The goal of the next iteration is to move Agent-Attention from a promising research scaffold to a publication-grade empirical system. The central shift is:

> from toy/proxy validation to real, executable, matched-budget agent benchmarks.

## Required First Read

Every dispatched agent must read these files before doing task work:

1. `README.md`
2. `docs/project_status.md`
3. `docs/publication_gap_assessment.md`
4. `docs/decision_log.md`
5. The assigned task file under `docs/next_iteration/tasks/`
6. Any source files named in that task file

For exploratory direction-setting rather than strict task execution, use:

- `docs/next_iteration/research_directions/README.md`

## Current Local Environment

Known environment snapshot:

- OS: WSL2 Linux, kernel `6.6.114.1-microsoft-standard-WSL2`
- Python: `3.10.12`
- Git: available, `2.34.1`
- Docker: Docker Desktop binary visible under Windows path, but Docker is not currently available inside this WSL distro
- RAM: about `7.6GiB`
- Disk under workspace root: about `949GiB` free
- LLM API: OpenAI-compatible Paratera endpoint is expected via `.env`; never print or commit secrets

Agents must re-check the environment at start because these details can change.

```bash
pwd
python3 --version
git --version
docker --version
python3 -m unittest discover -s tests
python3 experiments/real_benchmarks/check_llm_environment.py --probe-chat
```

If Docker is unavailable, the Terminal-Bench/SWE-bench agents must first document the blocker and either:

- fix WSL Docker integration if allowed by the local environment, or
- create a no-Docker smoke path using the existing local pytest fixture suite, while clearly marking that Terminal-Bench execution is blocked.

## Research Target

Proposed paper direction:

> Agent-Attention: Cost-Aware Sparse Routing for Modular Language Agents

Minimum publishable claim:

> Under matched budgets, a sparse module-routing agent can improve the cost-quality Pareto frontier or reliability of long-horizon executable tasks compared with fixed workflows, ReAct-style agents, retrieval-memory agents, and all-agent aggregation.

Do not claim general superiority unless supported by end-task metrics.

## Evidence Policy

Use this hierarchy:

1. Executable end-task success from public benchmark harnesses.
2. Executable local fixture success, such as pytest.
3. Exact-match public datasets such as GSM8K/HumanEval/MBPP.
4. Route-proxy metrics.
5. Toy simulation metrics.

Only levels 1-3 can support main paper performance claims. Levels 4-5 are diagnostics.

## External Benchmark Priority

Primary benchmark:

- Terminal-Bench: realistic command-line agent tasks with sandboxed terminal execution and test scripts. Official repo: `https://github.com/harbor-framework/terminal-bench`; docs: `https://www.tbench.ai/`.

Secondary benchmark:

- SWE-bench Lite / Verified if Terminal-Bench is blocked or too expensive. Official repo: `https://github.com/swe-bench/SWE-bench`.

Controlled low-cost benchmark:

- Existing GSM8K harness.
- Optional HumanEval/MBPP, if an agent adds execution-safe scoring.

Agents must browse or inspect official repositories before implementing adapters because benchmark CLIs and dataset versions may change.

## Task Graph

```text
T0 environment and benchmark reconnaissance
  -> T1 Terminal-Bench adapter
      -> T2 smoke matrix
          -> T3 matched-budget full/subset matrix
              -> T4 statistics and Pareto analysis
                  -> T6 paper artifact pack

T0
  -> T5 local executable code-suite expansion
      -> T3/T4

T3/T4
  -> T7 router, memory, and textual-backprop real-task ablations
      -> T6
```

## Dispatch Table

| Task | Suggested agent | Purpose | Depends on |
|------|-----------------|---------|------------|
| T0 | Cartographer | Environment + benchmark reconnaissance | none |
| T1 | Bridger | Terminal-Bench adapter | T0 |
| T2 | Faraday | Smoke matrix over 5-10 tasks | T1 |
| T3 | Curie | Matched-budget benchmark matrix | T2 |
| T4 | Noether | Statistics, CI, Pareto plots/tables | T3 |
| T5 | Turing | Expand local executable code suite | T0 |
| T6 | Scribe | Paper artifact and reproducibility pack | T4, T5, T7 |
| T7 | Hopper | Router/memory/textual-backprop ablations | T3 |

The names are only labels. The owner can assign any agent to any task.

## Shared Output Contract

Each task agent must deliver:

- `scope`
- `environment_observed`
- `work_completed`
- `commands_run`
- `artifacts_created`
- `results`
- `risks_or_blockers`
- `next_recommended_action`

For code changes, the agent must also run:

```bash
python3 -m unittest discover -s tests
```

For benchmark changes, the agent must include a smoke command that can be rerun by the next agent.

## Repository Hygiene

- Never commit `.env`, API keys, raw external benchmark caches, or generated long trajectories.
- Store external clones under `external/` or another clearly named ignored/cached location.
- Store durable summaries under `experiments/metrics/`.
- Store task manifests under `experiments/tasks/`.
- Store docs under `docs/deliverables/` or `docs/next_iteration/`.
- If trajectories are too large, keep only a manifest plus regeneration command.

## Go/No-Go Gate For Main-Track Paper

Main-track candidate only if all are true:

- At least one realistic public benchmark is running end to end.
- At least 50 tasks, or a clearly justified official benchmark subset, are evaluated.
- At least 4 baselines are compared under matched budgets.
- Agent-Attention has a clear cost-quality or reliability win with confidence intervals.
- Failure analysis explains when Agent-Attention fails.

If these are not met, frame the work as a workshop/system/demo paper.
