# Phase 1 Faithful Baseline Experiment Memo

Date: 2026-06-26  
Path: A (instrumentation-first)  
Evidence level: experiment-observed on deterministic toy runtime

## What We Ran

- **Tasks**: 12 (`experiments/tasks/phase1_tasks.jsonl`) — code / search / mini-research mix
- **Baselines**: 6 faithful control policies (`experiments/baselines/faithful_runners.py`)
- **Runs**: 72 trajectories in `experiments/trajectories/phase1_faithful_matrix/`
- **Scorer**: `docs/deliverables/07/scoring_script.py`

## Key Results

| Baseline | Success | Cost-Norm Success | Mean Cost | Proxy Regret |
|----------|---------|-------------------|-----------|--------------|
| single_react_agent | 91.7% | 0.348 | 1.60 | 0.463 |
| fixed_workflow_agent | 91.7% | 0.316 | 1.90 | 0.377 |
| full_history_agent | 91.7% | 0.348 | 1.60 | 0.463 |
| retrieval_memory_agent | 83.3% | 0.318 | 1.60 | 0.463 |
| moa_style_agent | 8.3% | 0.017 | 3.10 | 0.718 |
| agent_attention_agent | 25.0% | 0.066 | 2.93 | 0.225 |

## Claims We Can Make

- Faithful baseline runners produce **distinct trajectories** with different routing policies logged.
- Equal-budget comparison shows **ReAct-style single controller is strongest** on toy oracle labels.
- Agent-Attention achieves **lower proxy route regret** but **worse task success** — routing quality ≠ task success under current toy scoring.
- MoA-style parallel activation is **cost-prohibitive** under matched budgets.

## Claims We Cannot Make

- Agent-Attention beats ReAct or fixed workflow (it loses on success and cost-normalized success).
- Memory improves outcomes (retrieval-memory below ReAct).
- Negative transfer is measurable (scorer reports 0 harmful reads).
- Any result transfers to real LLM/code execution.

## Recommended Next Tasks

1. **Phase 2 memory ablation** on `phase0_seed_negative_memory_001` with `aa_no_memory`, quarantine policy.
2. **Agent-Attention tuning**: adaptive top-k, stronger budget gate, or task-conditioned activation.
3. **Executable verifier** for code tasks to replace route-oracle success labels.
4. **Subagent dispatch**: memory ablation implementation + harmful memory labeling fix.
