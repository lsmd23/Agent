# Cascade Pilot Audit (Brief B)

## Scope

Direct-first cascade replay on the 26-task code matrix (no new LLM calls).

## Inputs Read

- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/metrics/oracle_route_matrix.json` (failure context from Brief A)
- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief B)

## Method

Replay per-task stage outcomes from the full matrix:

```text
single_react → fail → agent_attention_llm_tuned → fail → moa_style
```

Aggregate escalation rate, rescue count, cost per rescued task, and cost-normalized success.

## Commands Run

```bash
python3 experiments/cascade/run_cascade_pilot.py --mode replay
```

## Artifacts Created

- `experiments/metrics/cascade_pilot_summary.json`
- `experiments/analysis/cascade_pilot_audit.md`

## Results

### Primary policy: react → AA → MoA

| Metric | Cascade | ReAct | AA tuned | MoA |
|--------|---------|-------|----------|-----|
| Accuracy | 100.0% | 88.5% | 84.6% | 96.2% |
| Mean model calls | 1.54 | 1.23 | 2.00 | 2.08 |
| Cost-norm success | 0.6500 | 0.7187 | 0.4231 | 0.4630 |

- Escalation rate: **11.5%** (3 rescued)
- Cost per rescued task (extra calls): **2.6667**

### Escalation trigger table

| Stage | Trigger |
|-------|---------|
| ReAct → AA | pytest fail after direct attempt |
| AA → MoA | pytest fail after AA attempt |

### Rescued tasks

- `phase1_code_csv_001`: rescued by **agent_attention_llm_tuned** (single_react → agent_attention_llm_tuned, 3 calls)
- `phase1_code_email_001`: rescued by **agent_attention_llm_tuned** (single_react → agent_attention_llm_tuned, 3 calls)
- `phase1_code_env_flag_001`: rescued by **moa_style_llm_agent** (single_react → agent_attention_llm_tuned → moa_style, 7 calls)

### Alternate policy: react → MoA (skip AA)

- Accuracy: 100.0%
- Mean calls: 1.46
- Cost-norm: 0.6842
- Escalation rate: 11.5%

## Interpretation

Cascade replay matches MoA-level success with materially lower mean calls than always-MoA and better cost-normalized success than always-AA. Direct-first escalation is viable; live validation should confirm replay assumptions.

**Evidence outcome:** `supports_direction`

## Next Questions

- Run live cascade pilot (`--mode live`) to confirm replay on fresh trajectories.
- Compare react→MoA vs react→AA→MoA: is AA middle stage worth its cost on failures?
- Brief C: ablate AA components used only in escalation slot.
