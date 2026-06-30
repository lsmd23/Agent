# 02 Literature Transfer Map

## Scope

This document maps relevant literature into mechanisms that future agents can borrow. It is not a general survey; it is an engineering transfer map for Agent-Attention.

## Transfer Table

| Source | Useful Principle | What To Borrow | What Not To Copy Blindly |
|--------|------------------|----------------|---------------------------|
| Sparsely-Gated MoE / Switch Transformer | Conditional computation only helps when experts are specialized and routing is stable. | top-k/top-1 activation, load/usage accounting, router stability diagnostics, expert specialization metrics. | Do not assume neural MoE gains transfer automatically to prompt-level agents. |
| FrugalGPT | A cascade can match strong-model quality while reducing cost by escalating only when needed. | direct-first cascade: cheap route first, verifier/confidence decides escalation. | Do not make every task enter the expensive routing layer. |
| RouteLLM | Cost-quality routing can be learned from preference/outcome data and can transfer across model pairs. | outcome-trained lightweight router; route threshold controlling cost/quality tradeoff. | Do not rely only on lexical task labels. |
| Agent-as-a-Router / CodeRouterBench | Routing bottleneck is information deficit; verified feedback should update routing context. | Context-Action-Feedback loop, outcome memory, cumulative regret, task-dimension statistics. | Do not treat static router accuracy as the final objective. |
| ReAct | A single interleaved reason-act loop is strong and cheap. | Keep ReAct as default cheap path and hard baseline. | Do not compare AA against a weak or artificially constrained ReAct. |
| SWE-agent | Agent-computer interface can dominate architecture quality on software tasks. | terminal/editor/test ACI design before large Terminal-Bench claims. | Do not assume router changes will fix poor shell interaction. |
| Terminal-Bench | Public executable terminal tasks expose long-horizon agent failures. | use as primary external stress benchmark once ACI is stable. | Do not overinterpret tiny pilot subsets. |
| MasRouter | MAS routing includes collaboration mode and role allocation, not only model choice. | route over modes: direct, verify, specialist, MoA, search, memory. | Do not force a flat top-k module selection for every task. |
| DyLAN | Dynamic agent team selection can reduce unnecessary collaboration. | trial-based agent importance and early stopping. | Avoid expensive team optimization unless task difficulty justifies it. |
| Reflexion / Self-Refine | Verbal feedback can improve future trials without weight updates. | executable failure -> reflection -> local update -> held-out regression check. | Do not count replay fixes as general learning without held-out tests. |
| Toolformer | Tool use should be learned or triggered only when beneficial. | tool-call admission labels and "when to call" supervision from logs. | Do not add tools as always-on modules. |
| LATS | Search helps when single-step acting is too myopic. | optional search/planning fallback for hard terminal tasks. | Too expensive for default path. |
| AFlow / ADAS | Hand-designed workflows can be replaced by searched/generated workflows. | later-stage workflow search over AA policies. | Too high-cost before strong evaluation harness exists. |

## Mechanism Imports

### 1. Direct-First Cascade

Imported from FrugalGPT and RouteLLM.

Policy shape:

```text
run cheap direct/ReAct route
  -> if verifier passes and confidence high: halt
  -> if uncertain or failed: route to specialist/AA
  -> if still failed or high-risk: escalate to MoA/search/tree
```

This reframes AA as an escalation controller, not as the default execution engine.

### 2. Outcome Memory

Imported from Agent-as-a-Router and Reflexion.

Store:

```text
task_signature
features
route_taken
success
cost
failure_type
verifier_signal
```

Avoid storing full patch answers as reusable memory. The first valuable memory is performance statistics by task dimension.

### 3. Oracle Route Frontier

Imported from routing literature and MoE diagnostics.

For each task, calculate which baseline or route would have achieved the best success/cost tradeoff. If the oracle frontier does not beat ReAct or MoA, sparse routing has no room to win on that suite.

### 4. Mode Routing

Imported from MasRouter and DyLAN.

Route among collaboration modes:

- direct one-shot
- ReAct loop
- verifier-only retry
- specialist module
- retrieval-memory
- MoA aggregation
- search/tree planning

This is likely more useful than selecting flat top-k modules on every step.

### 5. ACI Before Terminal-Bench Scaling

Imported from SWE-agent.

Before running larger TB matrices, improve:

- file inspection
- targeted edit command
- test execution
- observation compression
- recovery from shell/environment errors

Terminal-Bench failure should be split into architecture failure vs interface failure.

## Source Links

- Sparsely-Gated MoE: https://arxiv.org/abs/1701.06538
- Switch Transformer: https://arxiv.org/abs/2101.03961
- FrugalGPT: https://arxiv.org/abs/2305.05176
- RouteLLM: https://arxiv.org/abs/2406.18665
- Agent-as-a-Router: https://arxiv.org/abs/2606.22902
- ReAct: https://arxiv.org/abs/2210.03629
- SWE-agent: https://arxiv.org/abs/2405.15793
- Terminal-Bench: https://www.tbench.ai/
- MasRouter: https://arxiv.org/abs/2502.11133
- DyLAN: https://arxiv.org/abs/2310.02170
- Reflexion: https://arxiv.org/abs/2303.11366
- Self-Refine: https://arxiv.org/abs/2303.17651
- Toolformer: https://arxiv.org/abs/2302.04761
- LATS: https://arxiv.org/abs/2310.04406
- AFlow: https://arxiv.org/abs/2410.10762
- ADAS: https://arxiv.org/abs/2408.08435
