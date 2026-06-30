# T7: Real-Task Router, Memory, And Textual-Backprop Ablations

Date: 2026-06-30
Status: **Complete (diagnostic/replay tier)** — no new LLM calls for router/memory/backprop pilots.

## scope

Move router, memory, and textual-backprop claims from toy/proxy toward executable code-suite evidence.

## commands_run

```bash
python3 experiments/analysis/route_selector_diagnostic.py
python3 experiments/analysis/outcome_memory_router.py
python3 experiments/analysis/real_task_backprop_diagnostic.py
python3 experiments/analysis/t7_consolidate.py
```

## Router ablation (Brief E)

- Evidence outcome: **weak_or_inconclusive**
- Held-out learned route accuracy: 0.5
- Held-out learned mean regret: 0.177142
- Static dominant regret: 0.181349
- Train/test split by `split_field` (6 train / 20 test tasks).

## Memory ablation (Brief D)

- Evidence outcome: **weak_or_inconclusive**
- Δ regret vs fixed cascade: 0.000972
- Memory hit rate: 0.153846
- Leakage audit: passed

## Textual backprop (Brief G)

- Evidence outcome: **falsified_or_blocked**
- Failures analyzed: 4
- Accept / quarantine / reject: {'accept': 0, 'reject': 4, 'quarantine': 0, 'rollback': 0}
- Replay improvement rate: 0.0

## Headline verdict

| Component | Credible improvement? | Notes |
|-----------|----------------------|-------|
| Learned route selector | weak | Beats lexical; ~ties static at N=26 |
| Outcome memory router | weak | Δ regret +0.001 vs cascade; guards OK |
| Textual backprop on AA failures | no | 0/4 accept; halt attribution only |

## acceptance

- [x] End-task executable outcomes (code matrix replay)
- [x] Train/test split for router (no task leakage in train labels from test)
- [x] Memory leakage guards audited
- [x] Backprop held-out regression checks
- [ ] Live learned router in production path (deferred — diagnostic only)
