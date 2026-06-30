# Claim Evidence Matrix

Date: 2026-06-30 (updated post Wave 3 / T4 / T7)

## scope

Classifies project claims by evidence level. Prevents overclaiming.

## claim table (2026-06-30)

| Claim | Evidence level | Evidence | Status |
| --- | --- | --- | --- |
| ReAct-style agents are required baselines. | literature-supported | Subtask 01; ReAct, SWE-agent | accepted |
| MoA-style aggregation is required comparator. | literature-supported | Subtask 01, 08 | accepted |
| Runtime logs route/cost/memory/verifier signals. | prototype-validated | Subtask 06–07; real LLM envelopes | accepted |
| Executable pytest oracles score code tasks. | experiment-observed | 26-task code suite, `code_verifier.py` | accepted |
| Always-on AA tuned beats ReAct/MoA on code suite. | experiment-observed | `code_full_matrix_summary.json`, T4 Pareto | **refuted** |
| Cascade AA lite improves cost-quality vs always-on AA. | experiment-observed | `code_cascade_wave3_with_ci.json`, T4 | **accepted (N=26 pilot)** |
| Oracle route opportunity gap exists. | experiment-observed | `oracle_route_matrix.json`, Brief A | accepted |
| Current AA modules are heterogeneous experts. | experiment-observed | Brief H audit | **refuted** |
| Learned route selector beats static routing held-out. | experiment-observed | Brief E, `route_selector_diagnostic.json` | **weak / inconclusive** |
| Outcome memory reduces route regret. | experiment-observed | Brief D, Δ regret +0.001 | **weak / inconclusive** |
| Textual backprop fixes real AA code failures. | experiment-observed | Brief G, 0/4 accept | **refuted** |
| TB shows AA architecture advantage. | experiment-observed | T3 pilot 4/15 pass | **not claimed** |
| Sparse routing is universal agent principle. | conjecture | — | not claimed |

## safe abstract wording

See `docs/paper_outline.md` abstract skeleton.

## negative results (preserve)

1. Always-on AA tuned: 84.6% @ 2.00 calls vs cascade lite 100% @ 1.50.
2. Expert redundant activation 96%.
3. Learned router +0.004 regret vs static at N=26 — not deployable.
4. TB agent failures 53% post-ACI — architecture comparison blocked.

## interfaces

Report claims using `docs/next_iteration/research_directions/06_claim_governance.md` levels 0–6.

## risks

- N=26 code suite still below main-track threshold.
- Single model/provider.
- TB pilot too small.

## open_questions

- Does 7-task TB steps=12 change pass rate enough to mention in abstract?
- When to promote cascade claim from pilot (N=26) to benchmark (N≥50)?
