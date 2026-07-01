# T3 ACI Rerun Comparison

Compare original T3 pilot vs post-ACI-patch rerun (3 tasks × 5 baselines).

## Before (original T3)

- Total runs: 15
- Total pass: 4/15
- Failure categories: {'none': 4, 'environment_failure': 5, 'agent_failure': 6}

| Baseline | Pass | Rate |
|----------|------|------|
| `agent_attention_llm_tuned` | 0/3 | 0.0% |
| `fixed_workflow_llm_agent` | 1/3 | 33.3% |
| `moa_style_llm_agent` | 1/3 | 33.3% |
| `retrieval_memory_llm_agent` | 1/3 | 33.3% |
| `single_react_llm_agent` | 1/3 | 33.3% |

## After (ACI rerun)

- Total runs: 15
- Total pass: 4/15
- Failure categories: {'none': 4, 'environment_failure': 3, 'agent_failure': 8}
- Invalid-shell step rate: 0.0
- Empty/truncated parse steps: 0/63

| Baseline | Pass | Rate |
|----------|------|------|
| `agent_attention_llm_tuned` | 1/3 | 33.3% |
| `fixed_workflow_llm_agent` | 0/3 | 0.0% |
| `moa_style_llm_agent` | 1/3 | 33.3% |
| `retrieval_memory_llm_agent` | 1/3 | 33.3% |
| `single_react_llm_agent` | 1/3 | 33.3% |

### Step metrics (after)

| Baseline | Mean steps | Invalid-shell | Empty-parse |
|----------|------------|---------------|-------------|
| `agent_attention_llm_tuned` | 5.3 | 0 | 0 |
| `fixed_workflow_llm_agent` | 2.7 | 0 | 0 |
| `moa_style_llm_agent` | 5.3 | 0 | 0 |
| `retrieval_memory_llm_agent` | 5.3 | 0 | 0 |
| `single_react_llm_agent` | 2.3 | 0 | 0 |

## Interpretation

- Pass count: before **4** → after **4**.
- Environment failure rate: before **33.3%** → after **20.0%** (Brief F target < 10%).
- Invalid-shell step rate after patch: **0.0** (Brief F target < 2%).
- ACI patches reduced environment failures but did not raise total pass count; remaining failures are mostly agent-side on hard tasks (`fibonacci-server`, `configure-git-webserver`).
- `agent_attention_llm_tuned` improved from 0/3 to 1/3 (pass on `fix-permissions`).
- Defer ≥20-task TB matrix until agent failure drivers are understood; current bottleneck is task difficulty + step budget, not shell parsing.
