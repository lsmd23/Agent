# Research Directions Guidance Pack

Date: 2026-06-30 (updated post-W1 synthesis)

This pack converts the latest empirical state into reusable guidance for future exploration agents. It is not a strict next-step checklist. It is a direction library: each document frames one class of ideas that can be assigned to future agents for implementation, critique, or falsification.

## Why This Pack Exists

Wave 3 exploration (see `docs/next_iteration/reports/W1_wave3_exploration_synthesis.md`) refined the picture:

- **Route opportunity exists** on the 26-task code suite (oracle gap +0.24 cost-normalized; Brief A supports).
- **Always-on AA tuned loses** to ReAct/MoA on cost-quality; **cascade with AA lite escalation wins** at 100% / 1.50 calls (Brief B + live eval).
- **AA components are surgically improvable** (Brief C); **current modules are not real experts** (Brief H falsified).
- **Terminal-Bench** needs ACI-stable eval before architecture claims; T3 ACI rerun fixed shell parsing (0% invalid-shell) but pass rate unchanged at 4/15 (Brief F).

Therefore, the project should stop treating "sparse routing" as already proven and instead ask:

> Under what task conditions, cost constraints, expert diversity, and feedback loops does sparse routing become useful?

## Wave 3 Status (2026-06-30)

| Track / Brief | Status | Outcome |
|---------------|--------|---------|
| A Oracle route matrix | Done | `supports_direction` |
| B Cascade controller | Done | `supports_direction` — use `cascade_react_aa_lite_llm` |
| C AA ablation | Done | `supports_direction` — gate verifier/memory |
| F TB ACI | Done + rerun | `supports_direction` — defer large TB matrix |
| H Expert specialization | Done | `falsified_or_blocked` — redesign experts |
| D Outcome memory | Done | `weak_or_inconclusive` |
| E Learned router | Done | `weak_or_inconclusive` |
| G Executable backprop | Done | `falsified_or_blocked` |
| T4 / T6 / T7 | Done | see `W2_complete_iteration_goals.md` |

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

7. `07_expert_redesign_proposal.md`  
   Post–Brief H specialist redesign (prerequisite for TB routing claims).

## Recommended Use

When dispatching an agent, give it:

- this `README.md`
- the specific direction file
- `docs/next_iteration/reports/W1_wave3_exploration_synthesis.md` (current empirical summary)
- relevant local code paths named in that direction file

Agents should return one of three outcomes:

- `supports_direction`: evidence suggests the direction deserves more work
- `weak_or_inconclusive`: implementation worked but evidence is weak
- `falsified_or_blocked`: direction failed, or benchmark/environment makes it invalid

## Core Reframed Thesis

The safest current thesis is:

> Agent-Attention should be evaluated as a **cascade routing layer** that defaults to cheap ReAct, escalates through a **lite AA slot** when needed, and reserves MoA for rescue — approaching the oracle route frontier under matched budget.

The unsafe thesis is:

> The current always-on lexical top-k Agent-Attention runtime already outperforms ReAct or MoA.

Current evidence does not support the unsafe thesis. Cascade `react_aa_lite` on the code suite is the first positive end-task routing result.

## Source Policy

The literature links in this pack were checked on 2026-06-30. Future agents must re-check sources when using them for a paper draft, because router and benchmark work is moving quickly.
