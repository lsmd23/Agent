# Experiment Plan

## Phase 0: Toy Runtime Validation

Goal: verify that the runtime logs every routing, module activation, memory retrieval, verifier decision, halt decision, and reflection.

Tasks:

- code task with expected modules: memory, code, verifier
- search task with expected modules: memory, search, critic, verifier
- research task with expected modules: memory, search, critic, aggregator

Success criteria:

- trajectory JSON contains all steps
- no step exceeds configured budget
- halt reason is explicit
- memory read/write events are auditable

## Phase 1: Static Router Baselines

Compare:

- single ReAct-style loop
- fixed planner -> executor -> critic
- proposed lexical top-k router
- proposed lexical top-k router with memory

Metrics:

- success rate
- average steps
- tool/module calls
- repeated module ratio
- verifier catch rate
- premature halt rate

Expected outcome:

The proposed router should mainly improve cost and observability at this stage. It may not improve task success until routing has learned from trajectories.

## Phase 2: Memory KV-Cache

Memory entry:

```json
{
  "key": "task family + route + failure/success signature",
  "value": {
    "workflow": "...",
    "reflection": "...",
    "avoid": "...",
    "verifier": "..."
  }
}
```

Ablations:

- no memory
- success-only memory
- success plus failure memory
- memory with expiration
- memory with usefulness feedback

Measure:

- retrieval precision
- useful memory reuse rate
- negative transfer rate
- transfer gain on repeated task families

## Phase 3: Textual Backpropagation

Failure attribution schema:

```json
{
  "failure": "...",
  "blamed_component": "router|memory|module|verifier|halt",
  "local_gradient": "...",
  "proposed_update": {
    "target": "...",
    "change": "..."
  },
  "evidence": ["trajectory event ids"]
}
```

Only accept updates when:

- a verifier or external test confirms the failure
- the target component is local
- the update can be rolled back
- repeated failures support the change, or severity is high

## Phase 4: Learned Routing

Train from logged trajectories:

- input: task/state/module features
- label: successful module choice or oracle route
- auxiliary target: cost-adjusted reward

Compare:

- lexical router
- embedding router
- contextual bandit router
- imitation-learned router
- agentic router with memory and verifier feedback

## Suggested Initial Dataset

Code tasks:

- small Python bug fix
- failing unit test repair
- dependency/config issue
- documentation mismatch

Search tasks:

- answer requiring two independent sources
- conflicting source reconciliation
- recency-sensitive technical question

Mini research tasks:

- paper cluster summary
- method taxonomy
- benchmark/metric design
- ablation proposal
