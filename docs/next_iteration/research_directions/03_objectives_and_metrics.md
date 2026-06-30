# 03 Objectives And Metrics

## Scope

This document defines new optimization objectives for future Agent-Attention variants. The goal is to stop optimizing vague "agent architecture quality" and instead measure whether routing creates value.

## Objective 1: Route Opportunity

Question:

> Do different routes win on different tasks?

For each task, collect success and cost for each baseline/route.

Metrics:

```text
winner_entropy = entropy(distribution of best_route over tasks)
oracle_success = mean(max_success_per_task)
oracle_cost_at_success = mean(min_cost_among_successful_routes_per_task)
route_opportunity_gap = oracle_cost_normalized_success - best_single_policy_cost_normalized_success
```

Interpretation:

- Low winner entropy means the suite does not need routing.
- If ReAct or MoA dominates almost every task, AA should not be expected to win.
- A positive opportunity gap is the precondition for learned routing.

## Objective 2: Oracle Route Regret

Question:

> How far is the router from the best route that could have been chosen with hindsight?

Per task:

```text
regret = oracle_reward(task) - selected_route_reward(task)
reward = success_value - lambda_calls * model_calls - lambda_tokens * tokens - lambda_latency * latency
```

Aggregate:

```text
mean_regret
cumulative_regret_over_task_stream
regret_by_task_family
regret_by_failure_type
```

This objective connects local experiments to Agent-as-a-Router-style regret evaluation.

## Objective 3: Cascade Utility

Question:

> Does escalation improve results enough to pay for itself?

A cascade step has positive utility only if:

```text
P(success_after_escalation) * value_success
  - added_cost
  - added_latency_penalty
  > expected_value_of_halting_or_retrying_cheaply
```

Useful metrics:

- escalation_rate
- escalation_success_gain
- unnecessary_escalation_rate
- missed_escalation_rate
- cost_per_rescued_task

The current AA tuned variant likely has high unnecessary escalation on easy code tasks.

## Objective 4: Activation Value

Question:

> Did each activated module add useful marginal value?

Per activated module:

```text
activation_value = downstream_success_delta_or_verifier_delta - module_cost
```

Approximate using:

- no-module ablation
- route replay
- paired failure comparison
- verifier catch or patch correction signal

Report:

- useful activation rate
- redundant activation rate
- harmful activation rate
- activation value by module kind

## Objective 5: Expert Specialization

Question:

> Are modules actually different experts, or just the same model with different labels?

Metrics:

- per-expert success by task family
- per-expert failure modes
- disagreement rate between experts
- unique rescue count
- specialist precision: success when selected / selections
- specialist recall: tasks only that expert solves / tasks requiring expert

If specialization is low, sparse routing cannot outperform a strong generalist.

## Objective 6: Calibration And Abstention

Question:

> Does the system know when cheap routes are enough and when it needs escalation?

Metrics:

- confidence-success calibration
- verifier false pass rate
- verifier false alarm rate
- abstain/escalate precision
- abstain/escalate recall
- premature halt rate

Practical target:

> High confidence cheap routes should pass often; low confidence routes should be selectively escalated.

## Objective 7: Outcome Memory Gain

Question:

> Does memory improve future route choice instead of leaking answers?

Store only route outcome summaries unless a task explicitly needs semantic memory.

Metrics:

- route accuracy before/after memory
- regret reduction after memory
- negative transfer rate
- memory hit precision
- stale memory rate
- train/test leakage audit

## Objective 8: Terminal Interface Reliability

Question:

> Are benchmark failures caused by routing, by model reasoning, or by the shell interface?

Metrics:

- environment_failure rate
- invalid command rate
- no-op command rate
- repeated command ratio
- useful observation compression rate
- test execution rate
- patch application success rate

Do not use Terminal-Bench to judge routing until interface failures are separately accounted for.

## Recommended Composite Score

For internal comparison:

```text
route_reward =
  1.0 * task_success
  - 0.08 * model_calls
  - 0.00005 * total_tokens
  - 0.00002 * latency_ms
  - 0.25 * timeout
  - 0.20 * environment_failure
```

This is not a universal paper metric. It is a tunable internal scalar for router training and ablation triage. Paper tables should still report raw success, calls, tokens, latency, and confidence intervals separately.

## Minimum Table For Future Reports

Every future routing report should include:

| Metric | Required |
|--------|----------|
| raw success | yes |
| model calls | yes |
| total tokens | yes |
| latency | yes |
| cost-normalized success | yes |
| oracle route gap | yes if routes are comparable |
| confidence interval | yes for task N >= 20 |
| failure taxonomy | yes |
| environment failures separated | yes for Terminal-Bench |
