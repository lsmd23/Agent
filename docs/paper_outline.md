# Paper Outline (Draft)

Date: 2026-06-30  
Status: Workshop / short-paper tier — honest about N=26 code + TB pilot limits.

## Title (working)

**Cost-Aware Cascade Routing for Modular Language Agents**

## Abstract skeleton

We study sparse module routing for language agents under matched LLM budgets. We build an instrumented runtime with trajectory envelopes, executable pytest oracles on 26 local code tasks, and a Terminal-Bench adapter with multi-step shell control. Always-on lexical Agent-Attention underperforms ReAct and MoA on cost-quality; oracle route analysis confirms a meaningful opportunity gap (+0.24 cost-normalized). A direct-first cascade with a lite escalation slot achieves **100% success at 1.50 mean calls**, beating always-on AA tuned (84.6% @ 2.00) with bootstrap CI on the code suite. Diagnostic router, outcome-memory, and textual-backprop pilots on the same suite show weak or null gains at N=26. Terminal-Bench pilots (3–7 tasks) remain inconclusive for architecture claims; ACI patches stabilize shell parsing but agent failures dominate on server tasks. We release scripts, manifests, and reproducibility instructions.

## Contributions

1. **Runtime + envelope schema** for routeable modules with cost accounting.
2. **Oracle route matrix + cascade controller** — first positive cost-quality result vs always-on AA on executable code tasks.
3. **Negative results** — always-on AA tuned, redundant experts (Brief H), weak learned router at N=26, outcome memory Δ regret ≈ 0.
4. **Terminal-Bench ACI** — multi-step loop + compression/truncation recovery; separates env vs agent failures.
5. **Reproducible artifact pack** — see `docs/artifact_reproducibility.md`.

## Section outline

1. **Introduction** — fixed workflows vs MoA waste; cascade routing hypothesis.
2. **Related work** — ReAct, Reflexion, MoA, FrugalGPT/RouteLLM, SWE-agent, Terminal-Bench.
3. **Method** — modules, cascade policy (`react → aa_lite → moa`), verifier, metrics.
4. **Experimental setup** — Qwen3-30B, 26 code tasks, TB no-apt manifest, matched budgets.
5. **Results** — code matrix, Pareto (T4), cascade wave3, oracle gap, TB pilot taxonomy.
6. **Ablations** — AA components, route selector (E), outcome memory (D), backprop (G).
7. **Limitations** — N=26, single model/provider, TB pilot, expert redesign pending.
8. **Conclusion** — cascade + lite escalation as default; learned routing needs scale.

## Result table index

| Table | Source |
|-------|--------|
| Code suite baselines | `docs/deliverables/08/result_table_cost_quality_pareto.md` |
| Real-task ablations | `docs/deliverables/08/result_table_real_task_ablations.md` |
| TB matrix | `docs/deliverables/08/result_table_terminal_bench_matrix.md` |
| Claim evidence | `docs/deliverables/09/claim_evidence_matrix.md` |

## Limitations (must include)

- 26 local pytest fixtures — not a public benchmark at scale.
- Single LLM model (Qwen3-30B via Paratera).
- TB N ≤ 7 tasks in current runs.
- Learned router / outcome memory / backprop not production-ready.
- Expert modules not heterogeneous (Brief H).

## Target venue

- **Workshop / demo:** current evidence sufficient with honest framing.
- **Main track:** blocked until ≥50 public executable tasks + TB stability.
