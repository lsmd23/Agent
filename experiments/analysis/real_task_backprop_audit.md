# Real-Task Textual Backprop Audit (Brief G / T7 Partial)

## Scope

Executable textual-backprop diagnostic on real LLM code-suite failures.

## Inputs Read

- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/llm_runs/code_full_matrix/code_all/agent_attention_llm_tuned/` (stored trajectories)
- `experiments/tasks/phase1_code_all.jsonl`
- `experiments/phase3/` (attribution, patches, validation)
- `docs/deliverables/05/textual_gradient_policy.md`

## Method

1. Select failed rows for `agent_attention_llm_tuned` from code matrix summary.
2. Load matching real-LLM trajectory envelopes (no new model calls).
3. Attribute failure component and compile bounded `RuntimePatch` proposals.
4. Replay before/after on source task via `aa_tuned_control` simulation harness.
5. Held-out regression guard on same-family tasks that passed on real LLM.
6. Apply Subtask 05 lifecycle gates (accept / quarantine / reject).

## Commands Run

```bash
python3 experiments/analysis/real_task_backprop_diagnostic.py
```

## Artifacts Created

- `experiments/metrics/real_task_backprop_summary.json`
- `experiments/analysis/real_task_backprop_audit.md`
- `experiments/phase3/real_task/attributions/`
- `experiments/phase3/real_task/envelopes/`
- `experiments/phase3/real_task/replay_trajectories/`

## Results

### Decision counts

| Decision | Count |
|----------|-------|
| Accept | 0 |
| Quarantine | 0 |
| Reject | 4 |

### Aggregate

- Failures processed: **4** / 26 suite tasks
- Replay improvement rate: **0%**
- Held-out regressions: **0**
- New LLM calls: **0**

### Per-failure

| Task | Real failure | Blamed | Update | Replay Δ | Held-out | Decision |
|------|--------------|--------|--------|----------|----------|----------|
| `phase1_code_config_001` | max_steps_reached | halt | halt_threshold | +0.0 | `phase0_seed_code_fix_001` (no) | **reject** |
| `phase1_code_strip_tags_001` | confidence_threshold_met | halt | halt_threshold | +0.0 | `phase0_seed_code_fix_001` (no) | **reject** |
| `phase1_code_slugify_001` | max_steps_reached | halt | halt_threshold | +0.0 | `phase0_seed_code_fix_001` (no) | **reject** |
| `phase1_code_env_flag_001` | confidence_threshold_met | halt | halt_threshold | +0.0 | `phase0_seed_code_fix_001` (no) | **reject** |

**Evidence outcome:** `falsified_or_blocked`

## Interpretation

Attribution from real LLM trajectories; replay/held-out via Phase 3 simulation (zero new LLM). Accept requires confidence>=0.70, replay improvement, and no held-out regression on matrix-passing tasks.

- Real LLM failures may reflect patch quality or step budget, not only routing.
- Simulation replay tests whether bounded router/memory/halt patches would fix the
  toy-runtime analogue; it does not re-run the LLM on the failed task.
- Zero accepted updates means no auto-apply; quarantined patches need live validation.

## Next Questions

- Inspect failures where replay did not improve (likely execution/patch, not router).
- Add halt/budget patches tuned to max_steps_reached real failures.
