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

Current status: not yet established.

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

> We study whether sparse module routing can improve modular language agents under cost constraints. We build an instrumented runtime and evaluate it on local executable code tasks and Terminal-Bench pilots. Initial results show that naive lexical top-k routing is not sufficient: it underperforms strong ReAct and MoA baselines on the current suite. This motivates a reframing toward feedback-updated cascade routing and oracle-regret evaluation.

Unsafe:

> Agent-Attention improves over ReAct and MoA.

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
