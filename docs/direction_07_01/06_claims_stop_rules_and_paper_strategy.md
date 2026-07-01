# D06: Claims, Stop Rules, And Paper Strategy Brief

## Objective

Keep the project honest while deciding whether to aim for workshop, demo, or main-track submission.

## Current Paper Position

The project is workshop/demo ready if framed as:

> A reproducible study of cost-aware cascade routing for modular language agents, with a positive local executable result and clear negative findings about always-on AA, redundant experts, and immature Terminal-Bench performance.

It is not main-track ready because:

- public benchmark scale is too small;
- Terminal-Bench pass rate is too low;
- expert v2 is not implemented;
- learned routing/memory/backprop are not yet strong;
- current positive result is single-model local code suite.

## Safe Claims

Allowed:

- A route opportunity gap exists on the local 26-task code suite.
- Always-on AA tuned is not an effective default.
- Direct-first cascade with AA lite reaches the local Pareto frontier.
- Terminal-Bench adapter and failure taxonomy are operational.
- Current expert modules are too redundant for strong routing claims.

Not allowed:

- Agent-Attention generally outperforms ReAct or MoA.
- Terminal-Bench validates the architecture.
- Learned routing is solved.
- Memory/backprop improves real tasks.

## Stop Rules

Stop or pivot a direction if:

- a new route policy cannot beat ReAct or MoA under matched budget on any meaningful subset;
- expert v2 remains >80% redundant after redesign;
- Terminal-Bench environment failures remain high enough to obscure agent failures;
- learned routing does not beat static cascade on held-out route regret;
- public benchmark setup consumes large compute without producing reproducible runs.

## Escalation Rules

Escalate a direction if:

- cascade positive result survives task expansion or a second model;
- expert v2 shows unique rescues;
- TB stable subset reaches non-trivial pass rate;
- learned router improves held-out regret with leakage controls;
- public benchmark subset reaches at least 20 tasks with 4 baselines.

## Paper Strategy Options

### Option A: Workshop Now

Frame around:

- cascade routing positive result;
- oracle route gap;
- negative results;
- artifact/reproducibility.

Risk:

- reviewers may see local tasks as too small.

### Option B: Main-Track Later

Required additions:

- 50+ tasks or public benchmark subset;
- expert v2 implemented and audited;
- TB or SWE-bench evidence;
- multi-model or at least stronger single-model robustness;
- confidence intervals and failure analysis.

Risk:

- longer path, more infrastructure burden.

### Option C: Systems/Artifact Paper

Frame around:

- runtime/envelope;
- benchmark adapters;
- failure taxonomy;
- reproducible routing experiments.

Risk:

- weaker algorithmic novelty.

## Deliverables

- `docs/direction_07_01/reports/D06_claims_stop_rules_and_paper_strategy.md`
- updated claim-evidence matrix if needed
- recommendation: workshop now / defer for main-track / systems artifact

## Final Guidance

Negative results should stay visible. They are part of the contribution: the project is learning which forms of "agent attention" are not sufficient.
