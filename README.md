# Agent-Attention Runtime Research

Research scaffold for a **sparse, logged module-routing agent runtime**: dynamic activation over agents, tools, memory, verifiers, and halt gates (vs fixed workflows or always-on MoA).

## Current Milestone (2026-06-29)

| Track | Status | Evidence |
|-------|--------|----------|
| Toy runtime + gates/routing | Done | `src/agent_attention_runtime.py`, 49 tests |
| Phase 1–4 (toy, route-proxy) | Done | faithful baselines, memory ablations, textual backprop, learned router |
| Real LLM harness | Done | 19 baselines, OpenAI-compatible + Ollama |
| Full real-LLM matrix | Done | 344 runs; summaries in `experiments/metrics/` |
| Publication-grade end-task eval | **Next** | executable code verifier, larger benchmarks |

**Canonical status:** [`docs/project_status.md`](docs/project_status.md)  
**Real vs toy comparison:** [`docs/deliverables/08/result_table_real_vs_toy.md`](docs/deliverables/08/result_table_real_vs_toy.md)

## Quick Start

```bash
# Tests
python3 -m unittest discover -s tests

# Toy Phase 1 faithful matrix (route-proxy, no API)
python3 experiments/phase1/phase1_faithful_runner.py

# Real LLM (requires .env — copy from .env.example)
python3 experiments/real_benchmarks/run_real_llm_eval.py --suite gsm8k --family faithful --limit 5

# Compare real LLM summaries vs toy Phase 1–4
python3 experiments/real_benchmarks/compare_real_vs_toy.py
```

## Repository Layout

```
src/agent_attention_runtime.py     # core runtime (routing, gates, memory, trajectories)
experiments/baselines/             # faithful baseline runners
experiments/phase{1,2,3,4}/        # toy experiment runners + memos
experiments/real_benchmarks/       # LLM client, executors, unified eval runner
experiments/tasks/                 # phase1 + GSM8K task JSONL
experiments/metrics/               # committed summary JSON (trajectories gitignored)
docs/deliverables/                 # result tables, scoring scripts
docs/decision_log.md               # architecture decisions
tests/                             # unit tests
```

## Evaluation Notes

- **Toy Phases 1–4** use **route-proxy success** (module routing vs expected_route) — mechanism validation, not end-task performance.
- **GSM8K real LLM** uses **exact numeric match** — end-task metric, but routing rarely matters on easy math items.
- **Phase1 real LLM** still uses route-proxy; interpret Pass+Partial together (see comparison doc).
- Trajectories under `experiments/llm_runs/` and `experiments/trajectories/` are **regenerable** and gitignored; summaries are committed.

## Research Goal

Measure when **dynamic sparse routing** improves **cost-adjusted success and stability** vs:

- single ReAct agent
- fixed planner/executor/critic workflow
- full-history context
- retrieval-memory ReAct
- MoA-style all-proposer aggregation

See `docs/research_memo.md` and `docs/deliverables/01/gap_analysis.md` for positioning.
