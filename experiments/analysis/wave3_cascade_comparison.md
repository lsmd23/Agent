# Wave 3 Cascade Comparison

Unified eval via `run_real_llm_eval.py --family cascade` (2026-06-30).

## Cascade policies (live 26-task code suite)

| Baseline | Accuracy | Mean calls | Cost-norm | CI (bootstrap) |
|----------|----------|------------|-----------|----------------|
| `cascade_react_aa_lite_llm` | 100.0% | 1.50 | 0.6667 | 100.0%–100.0% |
| `cascade_react_moa_llm` | 92.3% | 1.65 | 0.5581 | 80.8%–100.0% |
| `cascade_react_aa_moa_llm` | 100.0% | 1.69 | 0.5909 | 100.0%–100.0% |

## Reference fixed baselines (original matrix)

| Baseline | Accuracy | Mean calls | Cost-norm |
|----------|----------|------------|-----------|
| `single_react_llm_agent` | 88.5% | 1.23 | 0.7187 |
| `agent_attention_llm_tuned` | 84.6% | 2.00 | 0.4231 |
| `moa_style_llm_agent` | 96.2% | 2.08 | 0.4630 |

## Interpretation

- **`cascade_react_aa_lite_llm` reaches 100% accuracy** at 1.50 mean calls — best wave-3 policy on this run.
- AA lite (no verifier/memory, fixed top-k=2) as escalation slot outperforms always-on AA tuned (84.6% @ 2.00 calls).
- `cascade_react_moa_llm` underperformed lite on this run (92.3%); check per-task variance on `csv_001` and `slugify_001`.
- Default deployment recommendation: **`cascade_react_aa_lite_llm`** over `react_aa_moa` unless MoA rescue is required on held-out hard tasks.

## Artifacts

- `experiments/metrics/code_cascade_wave3_summary.json`
- `experiments/metrics/code_cascade_wave3_with_ci.json`
- Trajectories: `experiments/llm_runs/code_cascade_wave3/`
