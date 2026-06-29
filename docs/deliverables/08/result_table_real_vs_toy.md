# Real LLM vs Toy Runtime Comparison

Generated from real-LLM full runs. Model: `Qwen3-30B-A3B-Instruct-2507`.

## Phase1 Faithful (12 tasks, route-proxy for real LLM)

| Toy Baseline | Real LLM | Toy Success | Real Pass | Real Partial | Δ Pass | Real Calls |
|--------------|----------|-------------|-----------|--------------|--------|------------|
| single_react_agent | single_react_llm_agent | 91.7% | 8.3% | 83.3% | -83.3pp | 2.83 |
| fixed_workflow_agent | fixed_workflow_llm_agent | 91.7% | 0.0% | 83.3% | -91.7pp | 2.83 |
| full_history_agent | full_history_llm_agent | 91.7% | 8.3% | 83.3% | -83.3pp | 2.83 |
| retrieval_memory_agent | retrieval_memory_llm_agent | 83.3% | 8.3% | 83.3% | -75.0pp | 2.83 |
| moa_style_agent | moa_style_llm_agent | 8.3% | 50.0% | 41.7% | +41.7pp | 3.17 |
| agent_attention_agent | agent_attention_llm_agent | 25.0% | 16.7% | 83.3% | -8.3pp | 3.17 |
| agent_attention_agent_tuned | agent_attention_llm_tuned | 66.7% | 75.0% | 16.7% | +8.3pp | 2.17 |

## Phase1 Memory Ablations

| Toy Ablation | Real LLM | Toy Success | Real Pass | Real Partial | Δ Pass |
|--------------|----------|-------------|-----------|--------------|--------|
| aa_tuned_control | aa_tuned_control_llm | 66.7% | 75.0% | 16.7% | +8.3pp |
| aa_no_memory | aa_no_memory_llm | 75.0% | 83.3% | 8.3% | +8.3pp |
| aa_memory_read_only | aa_memory_read_only_llm | 66.7% | 75.0% | 16.7% | +8.3pp |
| aa_success_only_memory_write | aa_success_only_memory_write_llm | 66.7% | 75.0% | 16.7% | +8.3pp |
| aa_unfiltered_memory | aa_unfiltered_memory_llm | 66.7% | 75.0% | 16.7% | +8.3pp |
| aa_quarantine_aware | aa_quarantine_aware_llm | 66.7% | 75.0% | 16.7% | +8.3pp |

## Phase1 Router Variants

| Toy Router | Real LLM | Toy Success | Real Pass | Real Partial | Δ Pass |
|------------|----------|-------------|-----------|--------------|--------|
| aa_lexical_router | aa_lexical_router_llm | 66.7% | 75.0% | 25.0% | +8.3pp |
| aa_rule_router | aa_rule_router_llm | 41.7% | 75.0% | 16.7% | +33.3pp |
| aa_learned_router_replay | aa_learned_router_replay_llm | 75.0% | 75.0% | 8.3% | +0.0pp |
| aa_oracle_router | aa_oracle_router_llm | 91.7% | 66.7% | 8.3% | -25.0pp |

## GSM8K Faithful (20 tasks, exact-match)

| Baseline | Pass Rate | Mean Calls | Mean Latency |
|----------|-----------|------------|--------------|
| llm_direct_agent (reference) | 95.0% | 1.0 | 1838.1 |
| single_react_llm_agent | 100.0% | 3.0 | 7152.75 |
| fixed_workflow_llm_agent | 100.0% | 3.0 | 8192.25 |
| full_history_llm_agent | 95.0% | 3.0 | 6781.8 |
| retrieval_memory_llm_agent | 100.0% | 3.0 | 7002.4 |
| moa_style_llm_agent | 100.0% | 5.0 | 12917.9 |
| agent_attention_llm_agent | 70.0% | 5.0 | 10608.1 |
| agent_attention_llm_tuned | 90.0% | 2.2 | 6028.5 |

## Interpretation

- **Toy** success = route-oracle on deterministic executors.
- **Real LLM Phase1** pass/partial = same route-oracle on real module outputs.
- **Real LLM GSM8K** = exact numeric match (end-task).
- Large positive Δ on MoA/AA-default may reflect real LLM helping routing complete; large negative Δ on ReAct may reflect verifier/gate differences under latency.

