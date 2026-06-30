# T6: Paper Artifact Packaging

Date: 2026-06-30  
Status: **Complete (workshop-tier draft pack)**

## scope

Prepare claim-evidence mapping, paper outline, and reproducibility instructions after T3/T4/T7 results.

## artifacts_created

| Path | Purpose |
|------|---------|
| `docs/paper_outline.md` | Title, abstract skeleton, sections, limitations |
| `docs/artifact_reproducibility.md` | Environment, commands, expected outputs |
| `docs/deliverables/09/claim_evidence_matrix.md` | Updated 2026-06-30 |
| `docs/deliverables/08/result_table_cost_quality_pareto.md` | T4 Pareto table |
| `docs/deliverables/08/result_table_real_task_ablations.md` | T7 ablation table |
| `docs/next_iteration/reports/T4_statistics_and_pareto.md` | Statistics report |
| `docs/next_iteration/reports/T7_real_task_ablations.md` | Ablation report |
| `docs/next_iteration/reports/W1_wave3_exploration_synthesis.md` | Exploration synthesis |

## claim summary

### Accepted (experiment-observed, code suite N=26)

- Cascade `react_aa_lite` improves cost-quality vs always-on AA tuned.
- Oracle route opportunity gap exists (+0.24 cost-normalized).
- Always-on AA tuned does **not** beat ReAct/MoA on cost-quality Pareto.

### Accepted (diagnostic / negative)

- Expert modules 96% redundant (Brief H).
- Textual backprop 0/4 accept on AA code failures (Brief G).
- Learned route selector weak vs static at N=26 (Brief E).
- Outcome memory Δ regret ≈ 0 vs cascade (Brief D).

### Not claimed

- TB architecture advantage.
- Main-track general superiority.
- Production learned router.

## acceptance

- [x] Every claim names evidence source
- [x] Proxy/toy separated from end-task in outline
- [x] Compute/benchmark limitations stated
- [ ] Camera-ready LaTeX (deferred)
- [ ] Zenodo/archival upload (deferred)

## next

1. LaTeX skeleton if targeting workshop submission.
2. Expand TB to stable 7-task results before adding TB rows to abstract.
3. Re-run claim audit after `t3_full_steps12` completes.
