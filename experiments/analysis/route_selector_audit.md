# Route Selector Diagnostic (Brief E)

## Scope

Lightweight route classifier diagnostic on the 26-task code suite using oracle `cheapest_successful_route` labels from Brief A. Replay-only; no new LLM calls.

## Inputs Read

- `experiments/metrics/oracle_route_matrix.json`
- `experiments/tasks/phase1_code_all.jsonl`
- Fixture manifests under `experiments/fixtures/code/`
- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief E)

## Method

- Label: `cheapest_successful_route` from oracle route matrix.
- Features: task prompt/tags/memory flags, fixture metadata, and matrix-row difficulty signals (`matrix_successful_route_count`, min successful calls, route entropy).
- Train: logistic one-vs-rest route ranker on 6 tasks.
- Held-out split: `split_field` (20 tasks).
- Baselines: static dominant cheapest route; lexical/tag rule router.
- Metrics: route accuracy, mean regret vs oracle reward, cost-normalized success, success rate.

## Commands Run

```bash
python3 experiments/analysis/route_selector_diagnostic.py
```

## Artifacts Created

- `experiments/metrics/route_selector_diagnostic.json`
- `experiments/analysis/route_selector_audit.md`

## Results

### Held-out comparison

| Policy | Route accuracy | Mean regret | Cost-norm success | Success rate |
|--------|----------------|-------------|-------------------|--------------|
| Learned logistic | 50.0% | 0.1771 | 0.7667 | 85.0% |
| Static dominant | 45.0% | 0.1813 | 0.7833 | 85.0% |
| Lexical rules | 30.0% | 0.3450 | 0.5250 | 70.0% |

- Training accuracy (in-split): 100.0% on 6 tasks.
- Dominant training cheapest route: `single_react_llm_agent`.

### Learned held-out confusion (gold -> pred)

- `fixed_workflow_llm_agent->fixed_workflow_llm_agent`: 5
- `fixed_workflow_llm_agent->single_react_llm_agent`: 3
- `moa_style_llm_agent->single_react_llm_agent`: 2
- `retrieval_memory_llm_agent->single_react_llm_agent`: 1
- `single_react_llm_agent->fixed_workflow_llm_agent`: 4
- `single_react_llm_agent->single_react_llm_agent`: 5

## Interpretation

At N=26 with a small train split, results are diagnostic only. Some signal may exist, but regret gains over static/lexical baselines are not strong enough for production routing.

**Evidence outcome:** `weak_or_inconclusive`

## Next Questions

- Brief B: cascade rescue on oracle-failure subsets without relying on a learned upfront router.
- Expand suite / harder splits before live learned routing.
- Brief H: check whether route winners correlate with proposer specialization rather than prompt tags.
