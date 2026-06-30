# Expert Redesign Proposal (Post Brief H)

Date: 2026-06-30  
Status: **Required before TB routing claims**

## Problem

Brief H (`experiments/analysis/expert_specialization_audit.md`) falsified current module heterogeneity:

- **96% redundant activation** — multiple proposers emit near-identical patches
- **code_agent vs critic_agent pass-rate spread: 0.1%**
- Only **1** cross-baseline sole-module rescue

Sparse routing cannot win when all modules are the same prompt with different labels.

## Design Principles

1. **Distinct tools, not distinct personas** — specialists must differ in *capabilities* (shell, edit, test, search), not adjectives.
2. **Activation must be expensive** — default path stays ReAct; specialists require explicit escalation signal.
3. **Verifier as gate, not module** — keep verifier outside proposer pool (matches AA lite cascade).
4. **Measurable disagreement** — require >20% patch fingerprint disagreement before claiming multi-expert routing.

## Proposed Specialist Set (v2)

| Module | Capability | When routed |
|--------|------------|-------------|
| `patch_author` | Single-file pytest fix from failing test | Default code escalation |
| `repo_navigator` | Multi-file import/graph fix | `ImportError`, >3 repo files touched |
| `test_runner` | Execute pytest, return structured failure | After patch, before halt |
| `shell_agent` | Terminal-Bench tmux commands only | TB tasks only |
| `aggregator` | MoA-style merge | Only on cascade final stage |

Retire: generic `code_agent` / `critic_agent` / `search_agent` as parallel proposers.

## Integration Path

1. **Phase 1 (doc-only):** Update `docs/deliverables/03/router_design.md` references when implementing.
2. **Phase 2:** Implement `patch_author` + `test_runner` as tool-bound modules in cascade AA lite slot.
3. **Phase 3:** Re-run Brief H audit; target redundant activation < 50%.
4. **Phase 4:** TB eval only after Brief H passes on code suite.

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Redundant activation rate | 96% | < 50% |
| Disagreement rate (multi-proposer) | 31% | > 40% |
| Unique sole-module rescues | 1 | ≥ 3 on 26 tasks |

## Evidence Outcome

`falsified_or_blocked` for current modules — redesign is **prerequisite**, not optional polish.
