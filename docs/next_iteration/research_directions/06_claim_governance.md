# 06 Claim Governance

## Scope

This document defines which claims future agents may make from which evidence. It is meant to protect the project from overclaiming while preserving promising negative results.

## Claim Levels

### Level 0: Implementation Claim

Allowed wording:

> We implemented a sparse modular routing runtime with real LLM executors and executable scoring.

Required evidence:

- code paths
- unit tests
- runnable commands

Current status: supported.

### Level 1: Diagnostic Claim

Allowed wording:

> The current benchmark exposes cost, routing, memory, verifier, and failure signals useful for analyzing modular agents.

Required evidence:

- per-task logs
- cost metrics
- failure taxonomy

Current status: supported.

### Level 2: Negative/Boundary Claim

Allowed wording:

> On the current fixture-aware code suite, the current AA tuned policy does not outperform ReAct or MoA.

Required evidence:

- matched tasks
- matched model/provider
- raw success
- cost metrics
- paired table

Current status: supported by the 26-task code suite.

### Level 3: Opportunity Claim

Allowed wording:

> The task suite contains a route opportunity gap: an oracle router would outperform any single static policy.

Required evidence:

- oracle route matrix
- winner entropy
- oracle vs best single-policy frontier

Current status: **supported** (Brief A, 2026-06-30; `oracle_route_matrix.json`).

### Level 3b: Cascade Policy Claim (code suite, pilot N)

Allowed wording:

> A direct-first cascade with lite AA escalation improves cost-quality vs always-on AA tuned on the current fixture-aware code suite.

Required evidence:

- matched tasks and model
- cascade vs always-on AA table
- bootstrap CI if available

Current status: **supported** by `code_cascade_wave3_with_ci.json` (N=26, pilot only — not Level 5).

### Level 4: Router Improvement Claim

Allowed wording:

> A learned or feedback-updated router reduces regret compared with lexical/static routing.

Required evidence:

- train/test split
- held-out route regret
- confidence intervals if task count is sufficient
- no leakage audit

Current status: not yet established.

### Level 5: End-Task Performance Claim

Allowed wording:

> Under matched budgets, the proposed routing policy improves the cost-quality frontier on executable tasks.

Required evidence:

- executable end-task scoring
- at least 50 tasks or justified public benchmark subset
- 4+ baselines
- confidence intervals
- cost and raw success both reported

Current status: not established.

### Level 6: General Agent Architecture Claim

Allowed wording:

> Sparse module routing is a general architecture principle for language agents.

Required evidence:

- multiple task families
- external public benchmark
- transfer beyond local fixtures
- robust ablations
- strong baselines

Current status: conjecture only.

## Current Safe Abstract Shape

Safe:

> We study whether sparse module routing can improve modular language agents under cost constraints. On a 26-task executable code suite, direct-first cascade with lite AA escalation reaches 100% success at 1.50 mean calls, beating always-on AA tuned (84.6% @ 2.00) and approaching MoA accuracy at lower cost. Oracle route analysis confirms a meaningful opportunity gap. Terminal-Bench pilots remain too small for architecture claims; ACI patches stabilized shell parsing but hard tasks still fail for agent-capability reasons.

Unsafe:

> Always-on Agent-Attention improves over ReAct and MoA.

## Red Flags

Future reports must explicitly flag:

- AA loses to ReAct on cost-normalized success.
- MoA wins raw accuracy on the current code suite.
- Terminal-Bench pilot is too small and interface-limited.
- Route-proxy and toy results cannot support end-task claims.
- Any memory result must be checked for leakage.

## Positive Result Requirements

A positive result is credible only if it answers:

1. What baseline did it beat?
2. On which exact tasks?
3. With what budget?
4. By how much raw success?
5. At what cost?
6. With what confidence interval?
7. What failure modes remain?

## Negative Result Policy

Negative results are valuable if they identify:

- a suite where routing has no opportunity gap
- a component that only adds cost
- a memory policy causing negative transfer
- a terminal interface failure that invalidates architecture comparison
- a baseline that is too strong for AA to beat without a new mechanism

The project should preserve these results because they sharpen the eventual thesis.
