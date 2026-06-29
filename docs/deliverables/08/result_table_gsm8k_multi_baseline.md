# Real LLM GSM8K Multi-Baseline Results

> Updated 2026-06-26. Compares direct single-call, ReAct multi-turn, and Agent-Attention with real LLM module executors.

Model: `Qwen3-30B-A3B-Instruct-2507` via Paratera OpenAI-compatible API.

## Full Sample (20 tasks)

| Baseline | Accuracy | Mean Latency | Mean Model Calls |
|----------|----------|--------------|------------------|
| `llm_direct_agent` | **95% (19/20)** | ~1.8s | 1.0 |
| `llm_react_agent` | **100% (20/20)** | ~2.3s | 1.0 |
| `agent_attention_llm_tuned` | **100% (20/20)** | ~3.2s | 1.05 |

**Discriminative failure:** `gsm8k_test_0012` (lemon-tree break-even year). Direct answered **12** (off-by-one); ReAct and Agent-Attention both answered **13**. Same single model call on ReAct/AA for that item — prompt/format difference, not multi-step recovery.

**Cost note:** Agent-Attention uses ~1.8× direct mean latency on this sample; one task (`gsm8k_test_0002`) required **2** module calls after verifier/routing.

## Smoke (3 tasks)

| Baseline | Accuracy | Mean Latency | Mean Model Calls |
|----------|----------|--------------|------------------|
| `llm_direct_agent` | 100% (3/3) | ~1.5s | 1.0 |
| `llm_react_agent` | 100% (3/3) | ~1.8s | 1.0 |
| `agent_attention_llm_tuned` | 100% (3/3) | ~2.1s | 1.0 |

## Reproduce

```bash
python3 experiments/real_benchmarks/run_gsm8k_multi_baseline.py --limit 20 \
  --output-dir experiments/llm_runs/gsm8k/multi_baseline_full \
  --summary-output experiments/metrics/gsm8k_multi_baseline_full_summary.json
```

Select baselines:

```bash
python3 experiments/real_benchmarks/run_gsm8k_multi_baseline.py \
  --baselines llm_direct_agent agent_attention_llm_tuned --limit 5
```

## Artifacts

- Full summary: `experiments/metrics/gsm8k_multi_baseline_full_summary.json`
- Smoke summary: `experiments/metrics/gsm8k_multi_baseline_summary.json`
- Trajectories: `experiments/llm_runs/gsm8k/multi_baseline_full/{baseline_id}/`
- AA scored metrics: `experiments/metrics/gsm8k_multi_baseline_aa_scored.json`

## Known Deviations

- Agent-Attention uses P2 tuned config with memory disabled for math track.
- GSM8K exact-match verifier only; no chain-of-thought grading.
- Learned router not yet wired to real LLM track (lexical only).
- Lexical router often selects `critic_agent` before `code_agent` on math tasks.
