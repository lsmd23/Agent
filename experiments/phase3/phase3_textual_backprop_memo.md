# Phase 3 Textual Backprop Experiment Memo

Date: 2026-06-26  
Control: `aa_tuned_control` failures from Phase 2  
Evidence level: experiment-observed (toy runtime)

## Pipeline

1. Load failed `aa_tuned_control` trajectories from Phase 2 (`4` failures / `12` tasks).
2. Attribute failure → `attributionCase` + `updateRecord` patch proposal.
3. Compile bounded `RuntimePatch` (router / memory / halt targets).
4. **Failure replay** before/after on source task.
5. **Held-out** validation on same-family task.
6. Lifecycle decision per Subtask 05 gates (`accept` / `reject` / `quarantine`).

## Results Summary

| Metric | Value |
|--------|-------|
| Failures processed | 4 |
| Replay improvement rate | 75% (3/4) |
| Accept | 0 |
| Quarantine | 3 |
| Reject | 1 |

## Per-Failure Decisions

| Task | Blamed | Update Target | Replay Δ success | Decision | Reason |
|------|--------|---------------|------------------|----------|--------|
| phase0_seed_negative_memory_001 | router | router_rule | 0.0 | reject | replay_no_improvement |
| phase1_code_doc_001 | router | router_rule | +1.0 | quarantine | medium_confidence_replay_improved |
| phase1_code_import_001 | router | router_rule | +1.0 | quarantine | medium_confidence_replay_improved |
| phase1_search_conflict_001 | router | router_rule | +1.0 | quarantine | medium_confidence_replay_improved |

## Key Findings

1. **Attribution → patch → replay roundtrip works** — all four failures produced schema-valid attribution cases, update records, and textual update envelopes.
2. **Conservative acceptance gates hold** — no update reached `accept` because attribution confidence was `0.68` (< `0.70` threshold) even when replay fixed the source failure.
3. **Router early-priority patches fix code/search routing failures on replay** — three failures flipped from fail→pass on replay with bounded `early_priority_modules` patches.
4. **Negative-memory probe resists simple router patch** — control already quarantines harmful memory at load; failure mode is deeper (memory/aggregator loop), so proposed router patch did not improve replay.

## Claims We Can Make

- Subtask 05 lifecycle (attribution, replay, held-out, quarantine) is **executable** on toy trajectories.
- Replay can distinguish **improving vs non-improving** local patches before production apply.
- Medium-confidence updates with replay gain are **quarantined**, not auto-applied.

## Claims We Cannot Make

- Textual backprop improves aggregate success (no accepted updates).
- Attribution blame is always correct (no human/oracle validation).
- Quarantined patches would promote to accept on larger held-out sets.

## Reproduce

```bash
python3 experiments/phase3/phase3_backprop_runner.py
python3 -m unittest tests.test_textual_backprop -v
```

Artifacts:
- `experiments/metrics/phase3_backprop_summary.json`
- `experiments/phase3/attributions/`
- `experiments/phase3/envelopes/`
- `experiments/phase3/replay_trajectories/`
