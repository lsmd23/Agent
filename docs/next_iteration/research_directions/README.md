# Research Directions Guidance Pack

Date: 2026-06-30

This pack converts the latest empirical state into reusable guidance for future exploration agents. It is not a strict next-step checklist. It is a direction library: each document frames one class of ideas that can be assigned to future agents for implementation, critique, or falsification.

## Why This Pack Exists

The latest results show that Agent-Attention is technically viable but not yet empirically winning:

- Local executable code suite: `agent_attention_llm_tuned` reaches 22/26, below `single_react_llm_agent` at 23/26 and below `moa_style_llm_agent` at 25/26.
- Cost-normalized success is weakest for the current AA tuned variant because it spends close to MoA-level calls/tokens without MoA-level raw accuracy.
- Terminal-Bench pilot shows the present shell/ACI layer is immature; AA is not yet competitive there.

Therefore, the project should stop treating "sparse routing" as already proven and instead ask:

> Under what task conditions, cost constraints, expert diversity, and feedback loops does sparse routing become useful?

## Document Index

1. `01_evidence_reframing.md`  
   Reframes what current evidence supports, refutes, and leaves open.

2. `02_literature_transfer_map.md`  
   Maps relevant paper ideas into concrete mechanisms for Agent-Attention.

3. `03_objectives_and_metrics.md`  
   Defines the next optimization targets: oracle route frontier, cascade regret, activation value, specialization, calibration, and memory feedback.

4. `04_exploration_tracks_ranked.md`  
   Ranks exploration tracks by implementation cost and expected information gain.

5. `05_dispatch_briefs.md`  
   Gives assignable research briefs for future agents.

6. `06_claim_governance.md`  
   Defines what future evidence is allowed to claim, and what must remain a conjecture.

## Recommended Use

When dispatching an agent, give it:

- this `README.md`
- the specific direction file
- the current empirical summary pasted on 2026-06-30
- relevant local code paths named in that direction file

Agents should return one of three outcomes:

- `supports_direction`: evidence suggests the direction deserves more work
- `weak_or_inconclusive`: implementation worked but evidence is weak
- `falsified_or_blocked`: direction failed, or benchmark/environment makes it invalid

## Core Reframed Thesis

The safest current thesis is:

> Agent-Attention should be evaluated as a learned or feedback-updated routing layer that decides when to stay cheap, when to verify, when to activate specialists, and when to escalate to expensive aggregation.

The unsafe thesis is:

> The current lexical top-k Agent-Attention runtime already outperforms ReAct or MoA.

Current evidence does not support the unsafe thesis.

## Source Policy

The literature links in this pack were checked on 2026-06-30. Future agents must re-check sources when using them for a paper draft, because router and benchmark work is moving quickly.
