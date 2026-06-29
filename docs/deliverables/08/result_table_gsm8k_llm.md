# Real LLM GSM8K Results

> Updated 2026-06-26. Baseline: `llm_direct_agent` (single-call exact-match).

## Provider Comparison (20-task sample)

| Provider | Model | Accuracy | Mean Latency |
|----------|-------|----------|--------------|
| Ollama (local CPU) | `llama3.1:8b` | 60% (3/5 smoke) | ~4.1s |
| **Paratera API** | **`Qwen3-30B-A3B-Instruct-2507`** | **100% (20/20)** | **~1.8s** |

## Selected API Model

**`Qwen3-30B-A3B-Instruct-2507`** — chosen after probing:

| Model (probe) | Latency (1 task) | Probe result |
|---------------|------------------|--------------|
| Qwen3-30B-A3B-Instruct-2507 | **1.1s** | pass |
| DeepSeek-V3.2-Instruct | 3.6s | pass |
| GLM-4-Flash | 7.2s | pass |

MoE instruct model: fast, strong on grade-school math, good cost/performance tradeoff vs 235B+ models.

## Configure Remote API (do not commit secrets)

```bash
export OPENAI_API_KEY='your-key-here'
export OPENAI_BASE_URL='https://llmapi.paratera.com/v1'
export LLM_PROVIDER=openai
export LLM_MODEL='Qwen3-30B-A3B-Instruct-2507'

python3 experiments/real_benchmarks/run_gsm8k_llm.py \
  --provider openai --model 'Qwen3-30B-A3B-Instruct-2507'
```

## Artifacts

- Full run: `experiments/metrics/gsm8k_llm_paratera_full_summary.json`
- Trajectories: `experiments/llm_runs/gsm8k/paratera_full/`

## Reproduce

```bash
python3 experiments/real_benchmarks/check_llm_environment.py
python3 experiments/real_benchmarks/run_real_llm_bench.py --profile full \
  --provider openai --model 'Qwen3-30B-A3B-Instruct-2507' --skip-env-check
```
