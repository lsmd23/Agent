# Oracle Route Audit (Brief A)

## Scope

Route Opportunity Auditor on the 26-task code suite matrix (5 baselines, no new LLM calls).

## Inputs Read

- `experiments/metrics/code_full_matrix_summary.json`
- `docs/next_iteration/research_directions/03_objectives_and_metrics.md` (Objective 1–2)
- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief A)

## Method

- Per task: cheapest successful baseline = oracle cost route; max route_reward = oracle reward route.
- `route_reward = success - 0.08*calls - 5e-5*tokens - 2e-5*latency_ms`.
- Per-task cost-normalized success = `1/model_calls` if pass else `0`.

## Commands Run

```bash
python3 experiments/analysis/oracle_route_matrix.py
```

## Artifacts Created

- `experiments/metrics/oracle_route_matrix.json`
- `experiments/analysis/oracle_route_audit.md`

## Results

| Metric | Value |
|--------|-------|
| Oracle success | 100.0% (26/26) |
| Best single baseline (success) | moa_style_llm_agent @ 96.2% |
| Success gap (oracle − best single) | +3.8% |
| Oracle cost-normalized success | 0.9615 |
| Best single cost-normalized | single_react_llm_agent @ 0.7187 |
| Route opportunity gap | +0.2428 |
| Winner entropy (cheapest successful) | 1.505 / max 2.322 |
| Dominant cheapest baseline | single_react_llm_agent (46.2% of tasks) |

### Cheapest-successful winner counts

- `fixed_workflow_llm_agent`: 11/26
- `moa_style_llm_agent`: 2/26
- `retrieval_memory_llm_agent`: 1/26
- `single_react_llm_agent`: 12/26

### Unique solo success (only baseline to pass task)

- `moa_style_llm_agent`: 1 task(s)

### Mean regret vs oracle reward

- `single_react_llm_agent`: 0.1396
- `moa_style_llm_agent`: 0.1822
- `retrieval_memory_llm_agent`: 0.1945
- `agent_attention_llm_tuned`: 0.2839
- `fixed_workflow_llm_agent`: 0.3642

## Interpretation

The suite shows meaningful per-task route variation. Oracle routing beats the best fixed baseline on success and/or cost-normalized success enough to justify cascade and router pilots (Brief B/E).

**Evidence outcome:** `supports_direction`

## Next Questions

- Implement Brief B cascade (direct → AA → MoA) on failure sets from this matrix.
- Brief E: can cheap features predict `cheapest_successful_route`?
- Brief C: ablate AA components on tasks where AA is cheapest-successful.
