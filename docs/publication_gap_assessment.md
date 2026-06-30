# Publication Gap Assessment

Date: 2026-06-29 (Wave 3 update: 2026-06-30)

## Wave 3 Progress (2026-06-30)

Since this assessment, the project completed research-direction wave 3:

- **26-task code suite** with oracle route matrix and live cascade eval; `cascade_react_aa_lite_llm` reaches 100% @ 1.50 calls with bootstrap CI.
- **First credible cost-quality win** vs always-on AA tuned on executable tasks (still N=26, local fixtures only).
- **Terminal-Bench T3** multi-step loop + ACI patches; rerun confirms shell parsing fixed (0% invalid-shell) but pass rate still 4/15 — not yet paper-grade.
- **93 unit tests** passing (was 57).
- **Expert specialization falsified** — current modules are not heterogeneous enough for routing claims on TB.

Remaining main-track gaps: public benchmark at scale (≥50 tasks), TB env stability, learned router held-out eval, outcome-memory ablation. See `docs/next_iteration/reports/W1_wave3_exploration_synthesis.md`.

## Executive Judgment

The project is no longer just a toy scaffold: it now has a working runtime, trace schema, faithful baselines, real LLM calls, executable code-task oracles, and 57 passing unit tests. However, for a top-tier conference paper, the empirical evidence is still preliminary. The current state is closer to a strong workshop/demo submission or internal technical report than a full A-conference paper.

If the target is ICLR/NeurIPS/ICML/ACL/EMNLP main track, the main gap is not writing polish. It is benchmark scale, task realism, statistical credibility, and a sharper novelty claim against existing agent architectures.

## Current Evidence Inventory

### Strengths

- Runtime: sparse module routing over agents, memory, verifier, tools, halt/budget/safety gates.
- Logging: target-envelope style trajectories and cost/accounting hooks.
- Baselines: direct LLM, ReAct-style, fixed workflow, full-history, retrieval-memory, MoA-style, Agent-Attention default/tuned, memory ablations, router variants.
- Real model track: Qwen3-30B via OpenAI-compatible endpoint; GSM8K and Phase1 runs exist.
- Executable scoring: 6 code tasks now use pytest-based end-task oracles.
- Tests: `python3 -m unittest discover -s tests` passes 93 tests (2 skipped).

### Local Results That Are Paper-Usable With Caveats

- GSM8K exact-match real LLM: 20 tasks, multiple baselines. Useful as sanity check only because GSM8K barely stresses agent routing.
- Phase1 code executable eval: 6 code tasks x 7 baselines. Useful as pilot evidence, but too small and too easy after fixture-aware prompting.
- Phase1 route-proxy eval: useful for mechanism diagnostics, not as primary performance evidence.
- Phase2-4 toy/memo results: useful for architecture explanation and ablation planning, not for final claims.

## Comparison Against Representative A-Conference Agent Work

### ReAct

ReAct's contribution is a simple reason-act loop evaluated across QA/fact verification and interactive decision-making environments. The paper's strength is not just the loop; it shows task-level gains in multiple environments and compares against reasoning-only/acting-only baselines.

Gap: Agent-Attention has richer routing instrumentation, but lacks similarly convincing cross-domain end-task wins.

### Reflexion

Reflexion introduces verbal reinforcement through episodic memory and evaluates over reasoning, coding, and decision-making tasks with ablations on feedback and memory use.

Gap: Agent-Attention has textual backprop and memory quarantine, but the evidence is mostly replay/proxy. It needs repeated-trial improvement on real tasks with held-out regression checks.

### MetaGPT / AutoGen

These works sell system/framework value: composable multi-agent workflows, role/SOP structure, code, examples, and broad task demonstrations.

Gap: Agent-Attention can compete as a framework only if the API, reproducibility, and examples become clean enough for other researchers to run. Right now it is a research repo, not yet a public framework.

### AFlow / ADAS

These works optimize or discover agentic workflows and report results across several public datasets, with explicit cost or search-efficiency claims.

Gap: Agent-Attention's learned router is currently trained/evaluated on small replay-derived data. To compete here, the router must be trained on substantially more trajectories and evaluated out-of-domain.

### AgentBench / WebArena / SWE-bench / OSWorld / Terminal-Bench

Recent benchmark papers emphasize realistic interactive environments, execution-based validation, long horizons, and failure analysis. Terminal-Bench 2.0 has 89 hard CLI tasks with per-task environments and tests; SWE-bench has thousands of real GitHub issue tasks; OSWorld and WebArena use realistic computer/web environments.

Gap: Agent-Attention currently uses 6 executable code tasks and 20 GSM8K items. This is orders of magnitude smaller and less realistic.

## What Is Missing For A-Conference Level

### 1. A Sharper Thesis

Current possible thesis:

> Cost-aware sparse activation over agent modules can match or improve fixed multi-agent workflows by selectively routing to tools, memory, verifiers, and aggregators, while preserving inspectable trajectories and reducing unnecessary model calls.

This is viable, but must be converted into falsifiable claims:

- Claim A: comparable or better task success under matched token/call budget.
- Claim B: better cost-quality Pareto than fixed workflow and MoA.
- Claim C: router learns transferable activation patterns across task families.
- Claim D: memory quarantine/textual backprop reduces repeated failure without negative transfer.

### 2. Real Benchmarks

Minimum credible main-track empirical package:

- One primary long-horizon benchmark: Terminal-Bench, SWE-bench Lite, WebArena, AgentBench, or OSWorld.
- One secondary controlled benchmark: HumanEval/MBPP or GSM8K/MATH for easier reproducibility.
- At least 50-100 real task instances for the primary claim, unless the benchmark itself is expensive and the paper clearly justifies a fixed subset.
- 3-5 strong baselines: ReAct, fixed workflow, retrieval-memory ReAct, MoA/committee, AutoGen/MetaGPT-style workflow if feasible.
- Matched budgets: same max model calls, max tokens, timeout, and tools.

### 3. Statistics And Reproducibility

Needed:

- Bootstrap confidence intervals over tasks.
- Paired significance tests where each baseline sees the same task set.
- Cost metrics: model calls, prompt tokens, completion tokens, wall-clock latency, timeout rate.
- Failure taxonomy applied to real trajectories.
- Frozen prompts/configs and exact model versions.
- Full trajectory release or deterministic regeneration script.

### 4. Stronger Router Evidence

Needed:

- Train router on one split, test on held-out tasks.
- Compare lexical/rule/learned/oracle routers under identical budgets.
- Report oracle gap, regret, and calibration.
- Show that learned routing improves beyond hand tuning, not just replay over known failures.

### 5. Memory And Textual Backprop Evidence

Needed:

- Repeated-trial experiments where prior failures are converted into memory/update rules.
- Held-out regression suite where bad memories can hurt.
- Ablations: no memory, read-only, success-only, unfiltered, quarantine-aware.
- Clear acceptance criteria for updates.

## Compute And Data Reality Check

The project does not need large-scale model training, but it does need substantially more inference and environment execution.

Likely feasible with limited local compute:

- GSM8K/MBPP/HumanEval using remote API.
- Small SWE-bench Lite or Terminal-Bench subset.
- Code-task fixture expansion with local pytest or Docker.

Likely difficult without more budget/infrastructure:

- Full Terminal-Bench with many baselines and repeated seeds.
- WebArena/OSWorld at scale, due environment setup and long interactive trajectories.
- Multi-model comparison across GPT/Claude/Gemini/Qwen/open-weight models.
- Training large neural routers. A small sklearn/logistic or gradient-boosted router is enough for now.

## Should We Run Terminal-Bench?

Yes, if the paper is about agent architecture for terminal/code/tool execution. Terminal-Bench is directly aligned with this project's routing story: command-line tools, long horizons, execution-based verification, and cost/time tradeoffs.

Recommended staged plan:

1. Terminal-Bench smoke: 5-10 tasks, 3 baselines, verify adapter works.
2. Terminal-Bench core subset: 20-30 tasks, 4 baselines, one model, matched budget.
3. Full Terminal-Bench 2.x: all tasks, 4 baselines, one strong model.
4. Add multi-model only after the full single-model story is stable.

If budget blocks full Terminal-Bench, use a pre-registered subset and state it honestly. Do not present subset results as benchmark-wide SOTA.

## Recommended Paper Organization

### Paper Title Direction

Agent-Attention: Cost-Aware Sparse Routing for Modular Language Agents

### Contributions

1. A sparse agent runtime that activates only needed modules among reasoning agents, tools, memory, verifiers, and aggregators.
2. A trajectory schema for route decisions, budget/cost accounting, memory reads/writes, verifier outcomes, and halt reasons.
3. Learned and rule-based router variants with oracle-regret diagnostics.
4. Memory quarantine and textual-backprop update policy for reducing repeated failures.
5. Evaluation on realistic executable agent tasks under matched budgets.

### Suggested Sections

1. Introduction: why fixed workflows and all-agent MoA are wasteful or brittle.
2. Related Work: ReAct, Reflexion, AutoGen, MetaGPT, LATS, ADAS/AFlow, benchmark papers.
3. Method: state, modules, router score, gates, memory, verifier, halt, cost objective.
4. Experimental Setup: benchmarks, models, baselines, budgets, metrics.
5. Results: primary benchmark, cost-quality Pareto, router ablation, memory/backprop ablation.
6. Analysis: failure modes, learned router behavior, oracle gap.
7. Limitations: small model set, benchmark scope, endpoint variability.

## Go / No-Go Criteria

Workshop-ready:

- Current repo plus one polished report and cleaned scripts.

Main-track submission candidate:

- At least one realistic benchmark with >=50 tasks or full accepted benchmark subset.
- End-task execution metrics, not route-proxy.
- Matched-budget baselines.
- Confidence intervals.
- One result where Agent-Attention is clearly better on cost-quality Pareto or reliability.

No-go for A-conference:

- Only GSM8K.
- Only route-proxy success.
- Only 6 code fixtures.
- No matched cost budget.
- No public benchmark adapter.
