# Research Memo: From Fixed Agent Workflows To Agent-Attention Architectures

## 1. Positioning

The core research question is:

Can an agent system move from a hand-written `plan -> act -> observe -> update` loop to a routable, sparsely activated architecture where agents, tools, memories, skills, and verifiers are treated as composable computation units?

This belongs primarily to:

- agent-level attention
- agent/tool/memory routing
- gating and halting
- cross-task memory reuse
- textual backpropagation and continual improvement
- evaluation of efficiency and stability, not only task success

The proposed architecture should be judged as an engineering and learning system, not just as a metaphor. The analogy to Transformers/MoE/Memory Networks is useful only if it yields concrete state representations, scoring functions, activation rules, feedback updates, and benchmarks.

## 2. Related Work Map

### ReAct

ReAct interleaves reasoning traces with external actions, making it the closest baseline for explicit recurrent agent loops. It is a strong baseline because it already reduces hallucination through environment interaction and produces interpretable trajectories.

Source: https://arxiv.org/abs/2210.03629

### Toolformer

Toolformer is relevant to tool-use gating: it trains language models to decide when to call APIs, what arguments to pass, and how to fold results back into prediction. For this project, the key abstraction is tool-call supervision and self-supervised tool-use data generation.

Source: https://arxiv.org/abs/2302.04761

### HuggingGPT

HuggingGPT uses an LLM controller to plan tasks, select models, execute subtasks, and summarize results. It is a representative fixed controller plus model pool system, useful as a baseline for tool/model routing by textual capability descriptions.

Source: https://arxiv.org/abs/2303.17580

### Reflexion

Reflexion updates behavior through verbal feedback and episodic memory instead of weight updates. It directly supports the textual-backprop idea: failures produce natural-language reflections that affect future trials.

Source: https://arxiv.org/abs/2303.11366

### Voyager

Voyager combines automatic curriculum, executable skill library, and iterative prompting with environment feedback. It is highly relevant to cross-task skill KV-cache and lifelong agent learning.

Source: https://arxiv.org/abs/2305.16291

### Memory Networks

Memory Networks formalize long-term memory as a read/write component used jointly with inference. They are a conceptual anchor for external agent memory, especially when separating memory write, retrieval, and response aggregation.

Source: https://arxiv.org/abs/1410.3916

### Mixture-of-Agents

Mixture-of-Agents uses multiple LLM agents in layers where later agents consume earlier outputs. It is a useful comparison point for multi-agent aggregation, but it is not the same as budget-aware sparse routing because its layer structure can be more fixed and expensive.

Source: https://arxiv.org/abs/2406.04692

### MasRouter

MasRouter frames multi-agent system routing as a learned routing problem across collaboration mode, role allocation, and LLM routing. It is close to the proposed direction because it treats multi-agent construction itself as a routeable decision.

Source: https://arxiv.org/abs/2502.11133

### Agent-as-a-Router

Agent-as-a-Router, published as a 2026 arXiv preprint, is especially aligned with coding-task routing. It models routing as a context-action-feedback loop with verifier and memory components, and introduces a benchmark for regret-based router comparison.

Source: https://arxiv.org/abs/2606.22902

## 3. Unified Abstraction

### State

`state_t` should include:

- original goal as a residual anchor
- current task decomposition
- observations so far
- active hypotheses
- selected modules and their outputs
- budget usage
- confidence and risk signals
- failure signals
- compressed trajectory summary
- memory reads and writes

To prevent state drift, every update should keep the original goal visible and ask whether the latest state still supports that goal.

### Module Pool

Each module has:

- `id`
- `kind`: agent, tool, memory, verifier, skill, aggregator
- capability description
- input/output schema
- cost estimate
- latency estimate
- risk estimate
- reliability estimate
- historical performance features

### Query

The router query should encode:

- task intent
- current state
- missing information
- failure signals
- budget condition
- required evidence type
- required action type

### Routing Score

A first concrete score can be:

```text
score_i =
  semantic_match(query, module_i.key)
  + alpha * reliability_i
  + beta * historical_success_i
  - gamma * cost_i
  - delta * latency_i
  - eta * risk_i
  + memory_bonus_i
```

This supports hard top-k routing, soft score logging, and later learning. In early experiments, start with interpretable lexical or embedding similarity before learning a policy.

### Activation

Activation should be sparse by default:

- cheap gates first
- retrieve top-n candidate modules
- activate top-k modules
- optionally require verifier activation when risk or uncertainty is high
- stop when halt confidence exceeds threshold and verifier has passed when required

### Aggregation

The aggregator should produce:

- concise state update
- accepted facts/actions
- rejected or conflicting outputs
- unresolved questions
- next-step recommendation
- confidence
- evidence pointers

### Memory

Represent agent KV-cache as:

```text
K = task representation + module route + tool schema + failure/success features
V = trajectory summary + successful workflow + useful reflection + reusable skill
```

Memory should record both positive transfer and negative transfer. Retrieval precision matters more than memory size.

### Textual Backpropagation

After failure:

```text
failure -> blame candidate -> local textual gradient -> update target
```

Potential update targets:

- router rule
- module prompt
- memory write policy
- verifier checklist
- tool schema
- halt threshold
- task decomposition heuristic

The update must be local and auditable. Avoid global prompt rewrites unless repeated evidence justifies them.

## 4. Minimal Prototype

The first prototype should implement:

- task encoder
- module registry
- deterministic top-k router
- memory retrieval and write
- module execution interface
- aggregator/state updater
- verifier gate
- halt gate
- trajectory JSON logging
- reflection generation

The current `src/agent_attention_runtime.py` implements this as a deterministic toy runtime. It is not meant to solve real code tasks yet; it is a measurement harness for routing and control decisions.

## 5. Baselines

Use these baselines before claiming improvement:

- Single ReAct Agent: one loop chooses all actions.
- Fixed Workflow Agent: planner -> executor -> critic.
- Full-History Agent: full trajectory always included.
- Retrieval-Memory Agent: same loop plus vector memory.
- MoA-style Agent: multiple agents produce outputs, then layered aggregation.
- Proposed Agent-Attention Agent: dynamic routing over modules, memory, gates, and verifier.

## 6. Ablations

Recommended ablations:

- no memory
- memory read only, no writes
- memory writes without reflection
- no verifier gate
- verifier always on
- no cost penalty
- no risk penalty
- fixed top-k versus adaptive top-k
- hard routing versus soft aggregation
- cheap lexical router versus embedding router versus learned router
- halt threshold low/medium/high

## 7. Metrics

Final metrics:

- task success rate
- pass rate for code tasks
- answer correctness for search tasks
- citation/evidence correctness for research tasks

Process metrics:

- average tool calls
- token cost estimate
- latency
- repeated action ratio
- invalid tool call ratio
- premature stopping rate
- loop-stuck rate
- verifier catch rate
- memory retrieval precision
- useful memory reuse rate
- cross-task transfer gain
- negative transfer cases
- router regret versus oracle route

## 8. First Research Hypotheses

1. Sparse routing will reduce cost and repeated action ratio compared with fixed multi-agent workflows on mixed code/search tasks.
2. Verifier-gated halting will reduce premature stopping but may increase latency; adaptive verifier use should dominate verifier-always-on.
3. Cross-task trajectory memory will improve routing on repeated task families, but only when memory write policies include failure attribution.
4. Learned or feedback-updated routing should outperform static capability matching after enough trajectories, but lexical routing is a necessary interpretable baseline.

## 9. Key Risks

- The neural analogy may hide rather than clarify engineering choices.
- Multi-agent activation may increase cost without improving success.
- Memory can cause negative transfer if stale, irrelevant, or over-retrieved.
- Tool calls are discrete and cannot be optimized like differentiable attention without surrogate learning.
- Verifiers can become expensive false-confidence generators.
- Strong single-agent baselines may already solve small tasks cheaply.

## 10. Near-Term Decision

Start with a code/search mixed benchmark because it naturally requires routing, tool use, verification, and multi-step state management. The minimum useful result is not a new SOTA agent; it is a clean comparison showing when dynamic sparse activation is better, worse, or merely more inspectable than fixed workflows.
