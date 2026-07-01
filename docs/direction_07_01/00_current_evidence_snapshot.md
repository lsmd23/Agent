# 00 Current Evidence Snapshot

Date: 2026-07-01

## Headline

The current project state supports a workshop-tier paper around cost-aware cascade routing. It does not yet support a main-track claim that Agent-Attention is a general superior agent architecture.

## Code Suite Evidence

Source files:

- `docs/deliverables/08/result_table_code_suite_matrix.md`
- `experiments/metrics/code_cascade_wave3_summary.json`
- `experiments/metrics/t4_pareto_summary.json`
- `experiments/metrics/oracle_route_matrix.json`

Key results:

| Policy | Accuracy | Mean calls | Interpretation |
|--------|----------|------------|----------------|
| `cascade_react_aa_lite_llm` | 100% | 1.50 | First positive Pareto result. |
| `moa_style_llm_agent` | 96.2% | 2.08 | Strong raw accuracy, expensive. |
| `single_react_llm_agent` | 88.5% | 1.23 | Strong cheap default. |
| `agent_attention_llm_tuned` | 84.6% | 2.00 | Always-on AA is refuted as default. |

Oracle route audit:

- Oracle success: 100%.
- Best single raw-success baseline: MoA at 96.2%.
- Best single cost-normalized baseline: ReAct.
- Route opportunity gap: about +0.24 cost-normalized.
- Winner entropy indicates more than one route matters, but ReAct remains dominant for many tasks.

Interpretation:

> The useful mechanism is not always-on top-k routing. The useful mechanism is conditional escalation from cheap ReAct into a lite specialist slot.

## Terminal-Bench Evidence

Source files:

- `docs/deliverables/08/result_table_terminal_bench_full_steps12.md`
- `experiments/metrics/t3_full_steps12_summary.json`

Key results:

- 7 tasks x 5 baselines = 35 runs.
- Total pass: 3/35.
- Only `fix-permissions` had any passes.
- Failure categories: 12 environment failures, 20 agent failures, 3 pass.

Interpretation:

> Terminal-Bench currently proves harness reachability and failure observability, not architecture superiority.

## Negative Results That Matter

- Always-on AA tuned is not on the Pareto frontier.
- Expert specialization is currently weak: previous audit reported 96% redundant activation.
- Learned route selector is weak at the current scale.
- Outcome memory has near-zero effect.
- Textual backprop produced 0 accepted updates in the latest diagnostic.

These negative results are valuable because they narrow the next design:

- route over modes/cascades rather than always-on module top-k;
- redesign experts before learning a router;
- stabilize external benchmark execution before scaling;
- treat memory/backprop as later-stage mechanisms.

## Current Best Thesis

Safe:

> Cost-aware cascade routing can improve local executable code-task cost-quality by defaulting to cheap ReAct and selectively escalating through a lite Agent-Attention slot.

Unsafe:

> Agent-Attention generally outperforms ReAct, MoA, or terminal agents.

## Main Gaps

1. Scale: 26 local tasks are not enough for main-track evidence.
2. Public benchmark: Terminal-Bench pass rate is still too low.
3. Expert heterogeneity: current modules are too redundant.
4. Learning: route learner and memory are not yet supported by enough data.
5. Multi-model robustness: current positive result is one model/provider.
