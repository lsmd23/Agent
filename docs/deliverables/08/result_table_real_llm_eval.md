# Real LLM Evaluation — All Baselines

> Updated 2026-06-26. Unified runner wires real LLM into all evaluation agent families.

## Baseline Registry (19 total)

| Family | Baseline IDs |
|--------|--------------|
| Standalone | `llm_direct_agent`, `llm_react_agent` |
| Faithful control policies | `single_react_llm_agent`, `fixed_workflow_llm_agent`, `full_history_llm_agent`, `retrieval_memory_llm_agent`, `moa_style_llm_agent`, `agent_attention_llm_agent`, `agent_attention_llm_tuned` |
| Memory ablations | `aa_tuned_control_llm`, `aa_no_memory_llm`, `aa_memory_read_only_llm`, `aa_success_only_memory_write_llm`, `aa_unfiltered_memory_llm`, `aa_quarantine_aware_llm` |
| Router variants | `aa_lexical_router_llm`, `aa_rule_router_llm`, `aa_learned_router_replay_llm`, `aa_oracle_router_llm` |

## Smoke Results

### GSM8K (2 tasks, faithful family)

| Baseline | Accuracy | Mean Calls |
|----------|----------|------------|
| single/fixed/full/retrieval/moa ReAct-style | 100% | 3–5 |
| `agent_attention_llm_agent` | 50% (1/2) | 5.0 |
| **`agent_attention_llm_tuned`** | **100%** | **2.0** |

### Phase1 (1 code task, faithful family)

Route-proxy scoring (no executable verifier yet): MoA and AA tuned **pass**; ReAct-style baselines **partial** (verifier/routing mismatch under real LLM latency).

## Run

```bash
# All faithful LLM agents on GSM8K
python3 experiments/real_benchmarks/run_real_llm_eval.py --suite gsm8k --family faithful --limit 20

# Phase1 mixed tasks
python3 experiments/real_benchmarks/run_real_llm_eval.py --suite phase1 --family faithful --limit 12

# Memory ablations with real LLM
python3 experiments/real_benchmarks/run_real_llm_eval.py --suite phase1 --family memory --limit 12

# Router variants with real LLM
python3 experiments/real_benchmarks/run_real_llm_eval.py --suite phase1 --family router --limit 12

# Everything (expensive)
python3 experiments/real_benchmarks/run_real_llm_eval.py --family all --suite gsm8k --limit 5
```

## Key Files

- Unified runner: `experiments/real_benchmarks/run_real_llm_eval.py`
- Shared executors: `experiments/real_benchmarks/llm_executors.py`
- Faithful LLM runtimes: `experiments/real_benchmarks/faithful_llm_runners.py`
- Task oracles: `experiments/real_benchmarks/task_oracles.py`

## Known Limitations

- Phase1 code/search tasks still use **route-proxy** success when no executable oracle exists.
- GSM8K uses exact numeric match.
- Token cost not normalized; `module.cost=1.0` per LLM call in routing budget.
