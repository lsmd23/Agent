# 05 Dispatch Briefs

## Scope

These briefs are assignable direction cards for future agents. They are intentionally exploratory. Each agent should be allowed to return a negative result.

## Brief A: Route Opportunity Auditor

### Question

Does the current 26-task code suite contain enough task-level variation for routing to matter?

### Inputs

- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/metrics/code_full_matrix_with_ci.json`
- raw per-task rows if available

### Deliverables

- oracle route table
- winner entropy
- oracle frontier vs best single baseline
- conclusion: suite supports routing / suite too easy / suite dominated by one policy

### Evidence Outcome

If oracle routing barely improves over ReAct or MoA, do not train a router on this suite.

## Brief B: Cascade Controller Designer

### Question

Can direct-first escalation recover AA's cost problem?

### Inputs

- current faithful LLM baselines
- pytest verifier
- failure sets from code suite

### Deliverables

- direct -> AA -> MoA cascade spec
- escalation trigger table
- pilot metrics on code suite
- cost per rescued task

### Evidence Outcome

Useful if success approaches MoA while cost approaches ReAct.

## Brief C: AA Component Surgeon

### Question

Which AA components are causing current underperformance?

### Inputs

- `agent_attention_llm_tuned`
- route logs
- code suite

### Deliverables

- ablation matrix
- component-level cost and success deltas
- recommendation: remove, keep, or gate each component

### Evidence Outcome

Useful even if all variants fail, because it narrows the design.

## Brief D: Outcome Memory Engineer

### Question

Can memory store verified route outcomes rather than task answers?

### Inputs

- code suite per-task baseline outcomes
- memory policy docs

### Deliverables

- outcome memory schema
- retrieval policy
- leakage guard
- before/after regret comparison

### Evidence Outcome

Useful if it reduces route regret without leaking answers.

## Brief E: Lightweight Router Learner

### Question

Can cheap task features predict the oracle route?

### Inputs

- oracle route table from Brief A
- task manifests
- failing test text
- repo metadata

### Deliverables

- feature extractor
- small classifier/ranker
- held-out evaluation
- confusion matrix
- calibration report

### Evidence Outcome

Useful if held-out regret beats lexical/static routing. If N is too small, report it as diagnostic only.

## Brief F: Terminal ACI Mechanic

### Question

Are Terminal-Bench failures caused by architecture or by the terminal interface?

### Inputs

- Terminal-Bench T2/T3 reports
- `experiments/terminal_bench/`
- SWE-agent paper/design notes

### Deliverables

- environment vs agent failure taxonomy
- minimal ACI improvements
- before/after smoke metrics
- recommendation on whether to run larger TB matrix

### Evidence Outcome

Useful if environment failure and invalid/no-op shell behavior drop materially.

## Brief G: Executable Backprop Evaluator

### Question

Can textual backprop improve repeated executable failures without regression?

### Inputs

- failed code tasks
- failed TB tasks
- textual backprop policy docs

### Deliverables

- failure attribution records
- proposed local updates
- replay results
- held-out regression checks
- accept/quarantine/reject decisions

### Evidence Outcome

Useful only if held-out checks pass. Replay-only fixes are not enough.

## Brief H: Expert Specialization Auditor

### Question

Are current modules real experts or mostly redundant prompts?

### Inputs

- module outputs from baselines
- success/failure by task family
- disagreement cases

### Deliverables

- module specialization table
- unique rescue cases
- redundant activation rate
- proposal for stronger specialist definitions

### Evidence Outcome

If specialization is weak, routing cannot win until experts are redesigned.

## Common Report Format

Every brief should return:

```text
scope
inputs_read
method
commands_run
artifacts_created
results
interpretation
supports_direction | weak_or_inconclusive | falsified_or_blocked
next_questions
```
