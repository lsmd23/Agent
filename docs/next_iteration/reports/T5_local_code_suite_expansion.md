# T5: Local Executable Code-Suite Expansion

Date: 2026-06-29  
Agent: Turing

## scope

Expand the local executable code-task suite to 20+ tasks with diverse bug types, update manifests, validate broken/golden repos, and smoke-test real LLM scoring on a subset.

## environment_observed

Same as T0/T1: WSL2, Python 3.10.12, no network required for scoring, remote LLM API available for optional eval smoke.

## work_completed

1. Added `experiments/fixtures/code/generate_expanded_fixtures.py` — reproducible generator for 20 new fixtures.
2. Generated **20 new fixtures** (25 total including original 5) covering:
   - import/path (`pkg_helper_001`, `url_join_001`)
   - parsing (`parse_int_001`, `parse_csv_row_001`, `json_get_001`, `email_valid_001`, `read_env_flag_001`)
   - edge-case math/string (`clamp_001`, `mean_001`, `palindrome_001`, `flatten_list_001`, `binary_search_001`)
   - config/doc mismatch (`trim_lines_001`, `config_get_001`)
   - security/sanitization (`sanitize_html_001`, `strip_tags_001`, `hash_password_001`)
   - refactor (`refactor_rename_001`, `merge_dict_001`, `slugify_001`)
3. Created task manifests:
   - `experiments/tasks/phase1_code_expanded.jsonl` (20 tasks)
   - `experiments/tasks/phase1_code_all.jsonl` (26 tasks = 6 original + 20 new)
4. Updated `tests/test_code_verifier.py` to auto-discover all fixtures via `list_fixture_dirs()`.
5. Ran validation: **25/25** fixtures broken-fail + golden-pass.
6. Real LLM smoke: 3 expanded tasks × `single_react_llm_agent` → **3/3 end-task pass**.

## commands_run

```bash
python3 experiments/fixtures/code/generate_expanded_fixtures.py
python3 experiments/real_benchmarks/validate_code_fixtures.py > experiments/metrics/t5_fixture_validation.json
python3 -m unittest discover -s tests
python3 experiments/real_benchmarks/run_real_llm_eval.py \
  --tasks experiments/tasks/phase1_code_expanded.jsonl \
  --family faithful --baselines single_react_llm_agent --limit 3 \
  --output-dir experiments/llm_runs/t5_smoke \
  --summary-output experiments/metrics/t5_code_expanded_smoke.json
```

## artifacts_created

| Path | Count |
|------|-------|
| `experiments/fixtures/code/*/` | **25 fixtures** |
| `experiments/tasks/phase1_code_expanded.jsonl` | 20 tasks |
| `experiments/tasks/phase1_code_all.jsonl` | 26 tasks |
| `experiments/metrics/t5_fixture_validation.json` | validation report |
| `experiments/metrics/t5_code_expanded_smoke.json` | LLM smoke summary |

## results

| Metric | Value |
|--------|-------|
| Total fixtures | **25** |
| Total executable code tasks | **26** (one fixture shared by 2 seed tasks) |
| Fixture validation | **25/25** broken fails + golden passes |
| Unit tests | **66 pass** (auto-discovery over 25 fixtures) |
| LLM smoke (3 tasks) | **100%** end-task pass (`single_react_llm_agent`) |

Task variety exceeds route keyword matching: security, parsing, refactor, config, import, edge algorithms — prompts describe bugs, not module names.

## risks_or_blockers

1. Expanded tasks may be **too easy** under fixture-aware prompting (3/3 smoke pass); harder variants needed for publication scale.
2. Full 26×7 baseline matrix not run yet (API cost/time); smoke only.
3. Some tasks share structural patterns (single-file `lib/*.py` fixes) — acceptable for development benchmark, not for main-track claims alone.

## next_recommended_action

Run matched-budget local matrix on `phase1_code_all.jsonl`:

```bash
python3 experiments/real_benchmarks/run_real_llm_eval.py \
  --tasks experiments/tasks/phase1_code_all.jsonl \
  --family faithful \
  --baselines single_react_llm_agent fixed_workflow_llm_agent agent_attention_llm_tuned \
  --output-dir experiments/llm_runs/t5_full \
  --summary-output experiments/metrics/t5_code_expanded_full.json
```

Parallel: fix Docker WSL socket (T1) and proceed to T2 Terminal-Bench smoke matrix.
