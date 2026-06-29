# Real LLM Benchmark Memo (GSM8K)

Date: 2026-06-26  
Backend: Ollama (`llama3.1:8b`, Q4_K_M) via `http://localhost:11434`  
Evidence level: experiment-observed (real model calls)

## Environment Check

| Resource | Value | Implication |
|----------|-------|-------------|
| RAM | 7.6 GB total (~5.6 GB available) | Tight for 8B; Q4 quant works but no headroom for parallel runs |
| GPU | None (`nvidia-smi` unavailable) | **CPU-only inference** |
| CPU | 32 cores | Adequate throughput, high latency per call |
| Ollama CLI | Not in WSL `PATH` | API reachable from WSL (likely Windows host Ollama) |
| Installed model | `llama3.1:8b` (~4.9 GB) | Only model available locally |

**Verdict:** Local Ollama **can run** real LLM benchmarks, but expect **~20–50 s/question** on CPU. Full 20-task run ≈ 7–15 min. For faster iteration or larger models, use a remote API.

## Smoke Results (5 tasks, llama3.1:8b)

| Metric | Value |
|--------|-------|
| Accuracy | 60% (3/5) |
| Mean latency | ~4 s/task (warm) to ~48 s/task (cold) |

Failures on `gsm8k_test_0002`, `gsm8k_test_0003` — reasoning errors, not infra failures.

## How To Run

```bash
# 1. Environment check
python3 experiments/real_benchmarks/check_llm_environment.py --probe-chat

# 2. Profiles
python3 experiments/real_benchmarks/run_real_llm_bench.py --profile probe   # 1 task
python3 experiments/real_benchmarks/run_real_llm_bench.py --profile smoke   # 5 tasks
python3 experiments/real_benchmarks/run_real_llm_bench.py --profile full    # 20 tasks

# Direct runner
python3 experiments/real_benchmarks/run_gsm8k_llm.py \
  --provider ollama --model llama3.1:8b --limit 5
```

### Remote API (when local is too slow)

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1   # or compatible endpoint
export LLM_MODEL=gpt-4o-mini
python3 experiments/real_benchmarks/run_real_llm_bench.py --profile smoke \
  --provider openai --model gpt-4o-mini
```

## Artifacts

- Tasks: `experiments/tasks/gsm8k_test_sample.jsonl` (20 GSM8K test items)
- Trajectories: `experiments/llm_runs/gsm8k/{probe,smoke,full}/`
- Summaries: `experiments/metrics/gsm8k_llm_*_summary.json`
- Env report: `experiments/metrics/llm_environment_report.json`

## Known Limitations

- ~~Baseline is `llm_direct_agent` (single-call, no Agent-Attention routing).~~ **Updated:** multi-baseline runner compares direct, ReAct, and Agent-Attention LLM runtime.
- Exact numeric match only; no chain-of-thought grading.
- No token cost normalization yet.

## Multi-Baseline Comparison (2026-06-26)

Three real-LLM baselines on GSM8K:

| Baseline | Description |
|----------|-------------|
| `llm_direct_agent` | Single-call exact-match (original) |
| `llm_react_agent` | Multi-turn ReAct scratchpad (up to 4 steps) |
| `agent_attention_llm_tuned` | P2 tuned runtime with real LLM module executors |

Smoke (3 tasks, Qwen3-30B via Paratera): all baselines **100%** accuracy; AA mean latency ~2.1s vs direct ~1.5s.

Full (20 tasks): direct **95%** (19/20), ReAct **100%**, Agent-Attention LLM **100%**. Only failure: `gsm8k_test_0012` (lemon-tree break-even; direct=12, gold=13). AA mean latency ~3.2s, mean 1.05 model calls.

```bash
python3 experiments/real_benchmarks/run_gsm8k_multi_baseline.py --limit 20 \
  --output-dir experiments/llm_runs/gsm8k/multi_baseline_full \
  --summary-output experiments/metrics/gsm8k_multi_baseline_full_summary.json
```

Artifacts: `experiments/metrics/gsm8k_multi_baseline_full_summary.json`, `experiments/llm_runs/gsm8k/multi_baseline_full/`.
