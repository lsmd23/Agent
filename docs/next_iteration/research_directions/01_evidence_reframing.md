# 01 Evidence Reframing

## Scope

This document states what the current project results actually support. It should prevent later agents from over-claiming and help them identify where sparse routing may still become useful.

## Current Empirical Signal

### Supported

The project now supports these claims:

- Agent/tool/memory/verifier/halt modules can be implemented as routeable computation units.
- Real LLM calls can be wrapped in the project trajectory envelope.
- Local executable code tasks can be scored with pytest end-task oracles.
- Terminal-Bench-style execution can be reached through an adapter, but the current agent-computer interface is still fragile.
- Cost, latency, model calls, tokens, and end-task success can be logged per baseline.

### Weakly Supported

These claims have partial support:

- Sparse routing is a useful experimental frame for comparing ReAct, fixed workflows, retrieval memory, MoA, and adaptive activation.
- **Direct-first cascade with AA lite escalation** improves cost-quality on the 26-task code suite (100% @ 1.50 calls vs always-on AA 84.6% @ 2.00).
- Fixed workflow is a weak baseline on the current code suite.
- MoA improves raw accuracy on small code tasks but spends more.
- **Oracle routing would beat any single static baseline** on the current suite (Brief A; gap +3.8% success, +0.24 cost-normalized).

### Not Currently Supported

These claims are not supported by the latest data:

- Current **always-on** `agent_attention_llm_tuned` beats ReAct.
- Current **always-on** `agent_attention_llm_tuned` beats MoA on raw accuracy.
- Current **always-on** `agent_attention_llm_tuned` beats ReAct on cost-normalized success.
- Current AA modules are heterogeneous experts (Brief H: 96% redundant activation).
- Memory improves the local executable code suite.
- Terminal-Bench already shows an AA advantage.

## Diagnosis

The core problem is not that sparse routing is impossible. The problem is that the present router does not yet create enough positive selection value.

The current AA tuned runtime is stuck between two stronger extremes:

- ReAct: cheap and already sufficient for many fixture-aware code patches.
- MoA: expensive but robust through redundancy and aggregation.

AA currently spends near-MoA cost while failing to match MoA robustness. It also spends more than ReAct without enough accuracy gain.

## Why The Current Task Set Is Hard For AA To Win

Many current code tasks include:

- compact repo snapshot
- failing unittest output
- clear patch format
- direct pytest oracle

This setup strongly favors one-shot or low-call ReAct. It does not force the agent to decide among genuinely different experts. Sparse routing becomes valuable only when the task has one or more of:

- ambiguity about which capability is needed
- expensive optional verification
- multiple possible tools with different costs
- long horizon with partial observations
- task families where prior outcome statistics matter
- specialists that are actually heterogeneous

## Reframed Research Question

Old question:

> Does Agent-Attention outperform ReAct, fixed workflows, retrieval memory, and MoA?

Better question:

> Can a sparse routing layer learn when to stay cheap, when to verify, when to consult specialists, and when to escalate to MoA, approaching the oracle route frontier under a matched budget?

## Hypothesis Ladder

Future work should climb this ladder one rung at a time:

1. Route opportunity exists: different baselines win on different tasks.
2. Oracle routing would improve the Pareto frontier.
3. Cheap features can predict part of the oracle route.
4. Feedback memory improves routing on future tasks.
5. Learned or contextual routing beats static lexical routing.
6. Sparse routing approaches MoA raw accuracy at materially lower cost.
7. Sparse routing transfers to harder public executable benchmarks.

If rung 1 or 2 fails, the project should change task mix or expert definitions before training routers.

## Recommended Evidence Labels

Use these labels in future reports:

- `mechanism_validated`: code works but does not imply performance.
- `diagnostic_signal`: route/cost/failure signal useful for designing experiments.
- `pilot_end_task`: executable results with small N.
- `benchmark_evidence`: public benchmark or large fixture suite with confidence intervals.
- `claim_ready`: enough evidence to support a paper claim.

Current AA performance is mostly `pilot_end_task` and `diagnostic_signal`, not `claim_ready`.

**Exception (code suite only):** `cascade_react_aa_lite_llm` reaches `pilot_end_task` with a credible cost-quality win (100% @ 1.50 calls, bootstrap CI in `code_cascade_wave3_with_ci.json`). Still below Level 5 threshold (N=26, no public benchmark).
