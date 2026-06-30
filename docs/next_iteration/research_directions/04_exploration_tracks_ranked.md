# 04 Exploration Tracks Ranked By Implementation Cost

## Scope

This document ranks exploration tracks by implementation cost and expected information gain. It is meant for manual dispatch: give one track to one agent.

## Ranking Summary

| Rank | Track | Cost | Expected Information Gain | Why It Matters |
|------|-------|------|---------------------------|----------------|
| 1 | Direct-first cascade | Low | High | Tests whether AA's cost problem is mostly over-activation. |
| 2 | AA ablation sweep | Low | High | Identifies which AA components hurt cost or accuracy. |
| 3 | Oracle route matrix | Low-Medium | Very High | Tests whether routing opportunity exists at all. |
| 4 | Uncertainty-triggered MoA fallback | Low-Medium | High | Tries to approach MoA accuracy with less cost. |
| 5 | Outcome-memory router | Medium | High | Moves memory from transcripts to verified route statistics. |
| 6 | Lightweight learned router | Medium | High | Replaces lexical routing with outcome-trained routing. |
| 7 | Executable textual-backprop | Medium | Medium-High | Tests whether failures can produce useful local updates. |
| 8 | Terminal-Bench ACI upgrade | Medium-High | High | Separates interface failure from architecture failure. |
| 9 | Terminal-Bench 20+ task matrix | High | High | Needed for external benchmark evidence, but only after ACI improves. |
| 10 | Workflow search / ADAS-style optimization | High | Medium for now | Powerful later, premature before evaluation stabilizes. |

## Track 1: Direct-First Cascade

### Idea

Make ReAct/direct the default cheap route. Enter AA only when cheap execution fails, verifier confidence is low, or task features indicate high difficulty.

### Borrowed From

FrugalGPT, RouteLLM, ReAct.

### Minimal Variant

```text
direct/ReAct attempt
  -> pytest/verifier pass: halt
  -> fail or low confidence: AA tuned
  -> fail again: MoA fallback
```

### Success Signal

- Raw success >= ReAct.
- Cost lower than always-MoA.
- Cost-normalized success better than current AA tuned.

### Main Risk

The verifier may be too weak to decide when to escalate.

## Track 2: AA Ablation Sweep

### Idea

Current AA is not competitive. Before adding complexity, isolate which component is harmful.

### Variants

- top-k = 1
- top-k = 2
- adaptive top-k off
- memory off
- verifier off
- aggregator off
- no budget gate
- no cost penalty
- direct path enabled

### Success Signal

One ablated AA variant improves either:

- accuracy with same cost, or
- cost with same accuracy, or
- calibration of escalation decisions.

### Main Risk

Small task count may make differences noisy.

## Track 3: Oracle Route Matrix

### Idea

For each task, compute the best route in hindsight using the existing baseline matrix.

### Minimal Output

```json
{
  "task_id": "...",
  "best_success_route": "...",
  "cheapest_success_route": "...",
  "oracle_reward_route": "...",
  "aa_selected_route": "...",
  "aa_regret": 0.0
}
```

### Success Signal

The oracle route differs across tasks and beats any single policy on cost-quality.

### Main Risk

If one baseline dominates almost all tasks, current suite cannot validate routing.

## Track 4: Uncertainty-Triggered MoA Fallback

### Idea

Use MoA as an expensive rescue route, not a default baseline.

### Trigger Examples

- direct patch fails pytest
- model output lacks required patch block
- verifier identifies contradiction
- task has multiple files, ambiguous API, or previous family failures

### Success Signal

Approaches MoA raw accuracy while reducing average calls/tokens.

### Main Risk

Escalation trigger may fire too often and collapse into MoA.

## Track 5: Outcome-Memory Router

### Idea

Replace transcript memory with route outcome memory.

### Memory Key

```text
task_family + error_type + repo_features + failing_test_signature + route_context
```

### Memory Value

```text
route -> success/cost/failure statistics
```

### Success Signal

Lower regret on later tasks or held-out same-family tasks.

### Main Risk

Leakage if memory stores answers or full fixes.

## Track 6: Lightweight Learned Router

### Idea

Train a small classifier or ranker to choose direct, AA, MoA, verifier, or specialist route.

### Features

- task family
- failing test length
- repo file count
- stack trace/error type
- prompt length
- previous route outcomes
- direct confidence/verifier score

### Labels

- cheapest successful route
- highest reward route
- oracle route class

### Success Signal

Held-out route regret below lexical/static router.

### Main Risk

With only 26 local tasks, train/test splits are fragile. Use this first as a diagnostic, not final evidence.

## Track 7: Executable Textual-Backprop

### Idea

Use real failed pytest/TB runs to generate local updates and test them on held-out tasks.

### Minimal Loop

```text
failure -> blame route/module/prompt/memory/verifier
  -> propose local textual update
  -> replay failed case
  -> test held-out case
  -> accept/quarantine/reject
```

### Success Signal

Fixes repeated failure classes without increasing held-out regression.

### Main Risk

Replay success can be overfit and should not be counted as general learning.

## Track 8: Terminal-Bench ACI Upgrade

### Idea

Improve the shell/edit/test interface before judging routing on TB.

### Borrowed From

SWE-agent and Terminal-Bench.

### Improvements

- explicit file navigation tool
- targeted edit/apply patch tool
- test command extraction
- observation compression
- recovery commands for shell failures
- distinction between environment failure and agent failure

### Success Signal

Environment failure rate decreases; test execution rate increases.

### Main Risk

ACI work can become a separate SWE-agent clone. Keep it minimal and measurable.

## Track 9: Terminal-Bench 20+ Task Matrix

### Idea

After ACI stabilizes, run a larger matched-budget public benchmark subset.

### Success Signal

At least one credible result on public executable tasks with confidence intervals.

### Main Risk

Expensive, noisy, and not useful before the interface is stable.

## Track 10: Workflow Search / ADAS-Style Optimization

### Idea

Search over workflow policies instead of hand-designing AA variants.

### Minimal Search Space

- direct only
- direct -> verifier
- direct -> AA
- direct -> MoA
- ReAct loop depth
- verifier threshold
- top-k
- memory on/off

### Success Signal

Search discovers a policy that beats hand-tuned AA on held-out tasks.

### Main Risk

Premature automation over a noisy benchmark can optimize artifacts.
