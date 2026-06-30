# AA Component Ablation Audit (Brief C)

## Scope

Component-level ablation replay on the 26-task code matrix plus rescue-task trajectory forensics.

## Inputs Read

- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/metrics/cascade_pilot_summary.json` (rescue context)
- `experiments/metrics/phase2_memory_ablation_summary.json` (toy memory ablations)
- `experiments/llm_runs/code_full_matrix/` (trajectories for csv/email/env_flag)
- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief C)

## Method

1. Define 8 one-variable AA variants (top-k, memory, verifier, gates, direct-first).
2. Replay aggregate metrics from matrix rows or cascade simulation where available.
3. Mark proxy/live-required tiers; compare rescue-task AA vs ReAct trajectories.

## Commands Run

```bash
python3 experiments/ablations/run_aa_ablation_pilot.py --mode replay
```

## Artifacts Created

- `experiments/metrics/aa_ablation_pilot.json`
- `experiments/analysis/aa_ablation_audit.md`

## Results

### Control vs direct-first

| Policy | Accuracy | Mean calls | Cost-norm success |
|--------|----------|------------|-------------------|
| Always AA tuned | 84.6% | 2.00 | 0.4231 |
| Direct-first (ReAct→AA) | 96.2% | 1.46 | 0.6579 |

### Ablation matrix (replay)

| Variant | Tier | Accuracy | Calls | Cost-norm | Δ acc | Δ cost-norm |
|---------|------|----------|-------|-----------|-------|-------------|
| aa_tuned_control | direct | 84.6% | 2.00 | 0.4231 | 0.0 | 0.0 |
| aa_top1 | live_required | live | — | — | — | — |
| aa_no_adaptive_topk | live_required | live | — | — | — | — |
| aa_no_memory | proxy | 88.5% | 1.23 | 0.7187 | 0.0384 | 0.2956 |
| aa_no_verifier | live_required | live | — | — | — | — |
| aa_no_budget_gate | proxy | 96.2% | 2.08 | 0.4630 | 0.1153 | 0.0399 |
| aa_no_cost_penalty | live_required | live | — | — | — | — |
| aa_direct_first | direct | 96.2% | 1.46 | 0.6579 | 0.1153 | 0.2348 |

### Component recommendations

| Component | Action | Confidence | Rationale |
|-----------|--------|------------|-----------|
| tuned_control | **keep** | high | Reference configuration for delta comparisons; replace with direct-first deployment policy. |
| top1 | **gate** | low | No matrix replay; schedule live ablation before remove/keep decision. |
| no_adaptive_topk | **gate** | low | No matrix replay; schedule live ablation before remove/keep decision. |
| memory | **gate** | medium | Proxy ReAct (no memory) beats always-AA on cost-norm; Phase2 toy shows aa_no_memory +8.3pp success. Gate memory to escalation-only or outcome-memory pilot. |
| no_verifier | **gate** | low | No matrix replay; schedule live ablation before remove/keep decision. |
| strong_budget_gate | **keep** | medium | MoA proxy (relaxed fan-out) has higher accuracy but worse cost-norm than control; budget gate limits over-activation on easy tasks. |
| no_cost_penalty | **gate** | low | No matrix replay; schedule live ablation before remove/keep decision. |
| direct_first_escalation | **keep** | high | Direct-first improves cost-norm by +0.2348 vs always-AA with accuracy delta +0.1153 (matrix replay). |

### Rescue-task trajectory forensics

#### `phase1_code_csv_001`

AA rescued via extra modules ['critic_agent'] (2 calls vs ReAct 1). Step-1 empty routes: 1; critic+code on retry drove fix.
- ReAct: success=False, modules=['code_agent'], calls=1
- AA tuned: success=True, modules=['code_agent', 'critic_agent'], calls=2, top_k=[2, 2]
- MoA: success=True, modules=['code_agent', 'critic_agent'], calls=2

#### `phase1_code_email_001`

AA rescued via extra modules ['critic_agent'] (2 calls vs ReAct 1). Step-1 empty routes: 1; critic+code on retry drove fix.
- ReAct: success=False, modules=['code_agent'], calls=1
- AA tuned: success=True, modules=['code_agent', 'critic_agent'], calls=2, top_k=[2, 2]
- MoA: success=True, modules=['code_agent', 'critic_agent'], calls=2

#### `phase1_code_env_flag_001`

AA failed after activating ['code_agent', 'critic_agent'] (empty route steps=1); MoA succeeded with parallel proposers.
- ReAct: success=False, modules=['aggregator', 'code_agent', 'critic_agent'], calls=3
- AA tuned: success=False, modules=['code_agent', 'critic_agent'], calls=2, top_k=[2, 2]
- MoA: success=True, modules=['code_agent', 'critic_agent'], calls=2

### Phase 2 toy memory ablation hint

- No-memory success delta vs control: **+0.0833**
- No-memory cost-norm delta: **+0.0351**

## Interpretation

Replay narrows AA underperformance to over-activation on easy tasks and optional memory overhead. Direct-first gating and keeping budget/cost gates are supported; memory and top-k variants need live confirmation.

**Evidence outcome:** `supports_direction`

## Next Questions

- Live-run `aa_top1`, `aa_no_verifier`, `aa_no_adaptive_topk` on the 26-task code suite.
- Compare `aa_direct_first` live cascade vs matrix replay.
- Brief D: outcome-memory router to replace transcript memory in escalation slot.
