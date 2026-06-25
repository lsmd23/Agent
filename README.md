# Agent-Attention Runtime Research Seed

This workspace is a small research scaffold for exploring a Transformer/MoE/Memory-inspired agent architecture: fixed workflows are replaced by dynamically routed, sparsely activated agent/tool/memory modules.

## What Is Here

- `docs/research_memo.md`: research framing, related work map, architecture proposal, baselines, ablations, and metrics.
- `docs/experiment_plan.md`: concrete first experiments for code/search/research tasks.
- `docs/subtasks/`: subagent-ready research task pack with one guiding document per subtask.
- `src/agent_attention_runtime.py`: a deterministic toy runtime that models state, routing, module activation, memory retrieval, verification, halting, and trajectory logging.
- `experiments/sample_tasks.jsonl`: example tasks for the toy runtime.
- `tests/test_runtime.py`: sanity tests for routing, memory reuse, and halt behavior.

## Run The Toy Runtime

```bash
python3 src/agent_attention_runtime.py \
  --task "Fix a failing Python test by inspecting code, editing, and verifying" \
  --output experiments/trajectory_demo.json
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## Research Goal

The first target is not to prove that multi-agent systems are better. It is to measure when dynamic routing improves efficiency, stability, and transfer compared with:

- single ReAct-style agent
- fixed planner/executor/critic workflow
- full-history context agent
- retrieval-memory agent
- layered Mixture-of-Agents style aggregation

The toy runtime is deliberately simple so that routing decisions and failure modes are inspectable.
