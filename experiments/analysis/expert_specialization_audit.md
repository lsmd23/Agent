# Expert Specialization Audit (Brief H)

## Scope

Expert Specialization Auditor on 26-task code matrix trajectories for `agent_attention_llm_tuned` and `moa_style_llm_agent` (52 runs, no new LLM calls).

## Inputs Read

- `experiments/metrics/code_full_matrix_summary.json`
- `experiments/llm_runs/code_full_matrix/` (AA + MoA trajectories)
- `docs/next_iteration/research_directions/03_objectives_and_metrics.md` (Objective 5)
- `docs/next_iteration/research_directions/05_dispatch_briefs.md` (Brief H)

## Method

- Parse trajectory events: `route.selected_modules`, `module_execution.outputs`, `model_call` payloads.
- Normalize proposer patch bodies; fingerprint for disagreement detection.
- Independently pytest-verify each proposer module output via `verify_code_task`.
- Compute specialist precision (run success | module selected), pytest pass rate given output, disagreement rate (multi-proposer steps with distinct fingerprints), redundant activation signals.

## Commands Run

```bash
PYTHONPATH=. python3 experiments/analysis/expert_specialization_audit.py
```

## Artifacts Created

- `experiments/analysis/expert_specialization_audit.json`
- `experiments/analysis/expert_specialization_audit.md`

## Results

### Aggregate (Objective 5)

| Metric | Value |
|--------|-------|
| Runs analyzed | 52 |
| Disagreement rate (multi-proposer steps) | 30.8% (16/52) |
| Redundant activation rate | 96.2% (50/52) |
| Unique rescue cases (sole passing proposer) | 4 |
| Cross-baseline sole-module rescues | 1 |
| search_agent activations | 1 |
| code_agent vs critic_agent pass-rate spread | 0.1% |

### Module specialization table

| Baseline | Module | Activations | Pytest pass (given output) | Specialist precision |
|----------|--------|-------------|------------------------------|----------------------|
| agent_attention_llm_tuned | code_agent | 26 | 23/26 (88.5%) | 84.6% |
| agent_attention_llm_tuned | critic_agent | 26 | 23/26 (88.5%) | 84.6% |
| agent_attention_llm_tuned | verifier | 50 | 0/0 (n/a) | 88.0% |
| moa_style_llm_agent | code_agent | 27 | 26/27 (96.3%) | 96.3% |
| moa_style_llm_agent | critic_agent | 26 | 25/26 (96.2%) | 96.2% |
| moa_style_llm_agent | search_agent | 1 | 1/1 (100.0%) | 100.0% |
| moa_style_llm_agent | verifier | 24 | 0/0 (n/a) | 95.8% |

### Unique rescue cases (sole passing proposer within run)

- `phase1_code_email_001` (agent_attention_llm_tuned): only `code_agent` patch passes pytest; run_success=True
- `phase1_code_env_flag_001` (agent_attention_llm_tuned): only `critic_agent` patch passes pytest; run_success=False
- `phase1_code_sanitize_001` (moa_style_llm_agent): only `critic_agent` patch passes pytest; run_success=False
- `phase1_code_slugify_001` (moa_style_llm_agent): only `code_agent` patch passes pytest; run_success=True

### Redundant activation signals (sample)

- `phase0_seed_code_fix_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, duplicate_passing_proposer_patches
- `phase0_seed_negative_memory_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, duplicate_passing_proposer_patches
- `phase1_code_binary_search_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, multiple_distinct_passing_proposers
- `phase1_code_clamp_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, duplicate_passing_proposer_patches
- `phase1_code_config_001` (agent_attention_llm_tuned): empty_module_execution_steps=3, no_module_activated_failure_signal
- `phase1_code_config_get_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, duplicate_passing_proposer_patches
- `phase1_code_csv_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, duplicate_passing_proposer_patches
- `phase1_code_doc_001` (agent_attention_llm_tuned): empty_module_execution_steps=1, no_module_activated_failure_signal, duplicate_passing_proposer_patches

### Stronger specialist definitions (proposal)

- Scope code_agent to repo edit + pytest loop with file-write tool; forbid free-form rewrites without test feedback.
- Scope critic_agent to diff review against failing assertion only; must output structured issue list before optional patch.
- Activate search_agent only when task manifest marks external_evidence=true; bind to retrieval tool I/O.
- Treat aggregator as fusion layer, not a fourth proposer—run only when proposer fingerprints disagree.
- AA router: block verifier-first routes on code tasks; require code_agent before verifier/critic.

## Interpretation

Modules behave as redundant prompts: high redundant activation, minimal pass-rate spread, search_agent unused. Redesign specialists before investing in learned routing.

**Evidence outcome:** `falsified_or_blocked`

## Next Questions

- Brief C: fix AA `no_module_activated` / empty module_execution before re-auditing.
- Replace label-only prompts with tool-scoped roles (critic gets failing patch only; search gets retrieval tool).
- Re-run Brief H after search_agent is routable on evidence-heavy tasks.
