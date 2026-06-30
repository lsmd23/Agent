# T5: Local Executable Code-Suite Expansion

Suggested agent: Turing

## Objective

Expand the local executable code-task suite so the project has a reliable fallback and a fast development benchmark even when Terminal-Bench/SWE-bench is blocked.

## Dependencies

- Can run after T0.
- Does not require Terminal-Bench.

## Required Reads

- `experiments/tasks/phase1_tasks.jsonl`
- `experiments/tasks/phase1_code_tasks.jsonl`
- `experiments/fixtures/code/`
- `experiments/real_benchmarks/code_verifier.py`
- `experiments/real_benchmarks/task_oracles.py`
- `tests/test_code_verifier.py`

## Required Work

1. Add 20-50 small executable code tasks.
2. Each task must include:

- fixture repo
- failing test
- expected verifier command
- success oracle
- task manifest entry
- no hidden manual judgment

3. Cover multiple task types:

- import/path bug
- parsing bug
- edge-case math/string bug
- config/documentation mismatch
- security/sanitization bug
- small refactor with tests

4. Run real LLM baselines on a small subset first, then full local suite if budget allows.

## Deliverables

- Expanded fixtures under `experiments/fixtures/code/`
- Updated task manifests under `experiments/tasks/`
- Tests for verifier/task loading
- `docs/next_iteration/reports/T5_local_code_suite_expansion.md`

## Acceptance Criteria

- All gold or intended fixes pass verifier.
- All broken starting repos fail at least one relevant test.
- No task depends on external network during scoring.
- The suite has enough variety that route keyword matching is not sufficient.

## Failure Modes

- Making tasks too easy after fixture-aware prompting.
- Creating tests that pass before the model changes anything.
- Letting benchmark answers leak through memory across train/test split.
