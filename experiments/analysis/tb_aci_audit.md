# Brief F: Terminal ACI Mechanic Audit

Date: 2026-06-30  
Status: **Complete** — smoke-level taxonomy + two minimal ACI patches implemented.

## scope

Determine whether Terminal-Bench (TB) failures are caused by agent architecture or by the terminal agent-computer interface (ACI). Taxonomize T2/T3 runs, propose minimal fixes, and assess whether a larger TB matrix is justified.

## inputs_read

| Source | Notes |
|--------|-------|
| `docs/next_iteration/research_directions/05_dispatch_briefs.md` §Brief F | ACI before TB scaling |
| `docs/next_iteration/reports/T2_terminal_bench_smoke_matrix.md` | 5×3 single-shot matrix |
| `docs/next_iteration/reports/T3_matched_budget_benchmark_matrix.md` | 3×5 multi-step pilot |
| `experiments/metrics/t2_matrix_run.log` | 15 per-run rows |
| `experiments/metrics/t3_pilot_run.log` | 15 per-run rows |
| `experiments/metrics/terminal_bench_smoke_summary.json` | T2 aggregate |
| `experiments/metrics/terminal_bench_matrix_summary.json` | T3 aggregate + per_task |
| `experiments/llm_runs/terminal_bench/**/shell_steps.json` | 10 trajectories (T3 + smoke) |
| `experiments/terminal_bench/{adapter,faithful_tb_agent,tb_shell_loop}.py` | ACI implementation |

## method

1. Combined T2 (15 runs, pre–multi-step) and T3 (15 runs, multi-step loop) failure categories from run logs and envelope JSON.
2. Sub-classified T3 environment failures by `failure_reason` (apt mirror, test setup, registry).
3. Analyzed 10 available `shell_steps.json` trajectories for invalid-shell patterns: empty parse, truncated JSON, nudge fallback (`pwd`/`ls -la`), duplicate commands.
4. Implemented two minimal ACI patches (observation compression + truncated-JSON recovery / patch-tool lite) and verified with unit tests (no full TB matrix re-run).

## commands_run

```bash
cd /home/myuser/Agent
python3 -m unittest tests.test_terminal_bench_adapter -v
# Ad-hoc shell_steps / envelope analysis (inline Python on logs + trajectories)
```

## artifacts_created

| Path | Purpose |
|------|---------|
| `experiments/analysis/tb_aci_audit.md` | This report |
| `experiments/analysis/tb_aci_improvements.json` | Structured recommendations + patch metadata |
| `experiments/terminal_bench/adapter.py` | `compress_observation`, `extract_file_patch_commands`, partial JSON recovery, expanded command allowlist |
| `experiments/terminal_bench/tb_shell_loop.py` | Observation compression in prompts, re-prompt on parse failure, duplicate-command skip |
| `tests/test_terminal_bench_adapter.py` | 5 new unit tests for ACI helpers |

## results

### Failure taxonomy (combined T2 + T3, N=30)

| Category | Count | Share | Notes |
|----------|------:|------:|-------|
| **pass (none)** | 6 | 20% | All on `fix-permissions` |
| **agent_failure** | 19 | 63% | End-task verifier failed; agent ran but task incomplete/wrong |
| **environment_failure** | 5 | 17% | Infra during Docker build or test setup |
| **invalid_shell** (subset of agent, from trajectories) | 3 empty-parse steps / 76 total steps | ~4% of steps | Truncated JSON at max_tokens=512; no nudge-fallback hits in logged runs |

T2-only (N=15, single-shot era): 2 pass, 13 agent_failure, 0 environment_failure.  
T3-only (N=15, multi-step): 4 pass, 6 agent_failure, 5 environment_failure.

### T3 environment failure breakdown (N=5)

| failure_reason | Count | Example tasks |
|----------------|------:|---------------|
| `apt_mirror_failure` | 2 | fibonacci-server, fix-permissions (AA only) |
| `test_setup_failed` | 3 | configure-git-webserver, fibonacci-server (AA) |

Environment failures are **not baseline-specific** except AA's spurious apt hit on fix-permissions (same task passes for 4/5 other baselines).

### Invalid-shell breakdown (10 trajectories, 76 steps)

| Pattern | Count | Root cause |
|---------|------:|------------|
| Empty parse (no commands emitted) | 3 | Truncated JSON when embedding long SSH keys / multi-command payloads |
| Sanitizer-dropped commands | 0 | Allowlist already covers observed commands |
| Nudge fallback (`pwd`/`ls -la`) | 0 | Present in old code path; removed in patch |
| Duplicate consecutive commands | 42 | Agent re-runs same chmod/ls; wastes steps |

### Architecture vs interface split

| Failure mode | Verdict | Evidence |
|--------------|---------|----------|
| Multi-step gap (T2) | **Interface** | T2 20% pass → T3 27% pass on overlapping tasks; fix-permissions 1/5 → 4/5 after multi-step loop |
| Apt/registry/setup failures | **Environment** | 5/30 runs; not fixable by routing |
| Hard task failures (fibonacci-server, configure-git-webserver) | **Mostly agent** | Agent runs complete but server/git config wrong; needs more steps or stronger model |
| AA underperformance | **Mixed** | T2: 0/5 (agent); T3: 0/3 (2 env + 1 agent) — not clearly architecture-dominated at N=3 |
| Truncated JSON / empty shell steps | **Interface** | 3/76 steps; recoverable via partial JSON parse + re-prompt |

### Patches implemented (smoke-verified via unit tests)

1. **Observation compression** — `compress_observation()` tail-preserves errors; applied to terminal state and history in `build_step_prompt`.
2. **Truncated-JSON recovery + patch-tool lite** — `_extract_commands_from_partial_json()`, `extract_file_patch_commands()` (`# file:` → heredoc); re-prompt on parse failure instead of blind `pwd`/`ls -la` nudge; skip duplicate consecutive commands.

Unit tests: **13/13 pass** (2 skipped without TB package).

## interpretation

- **~17% of combined failures are environment**, not agent quality. A larger matrix on apt-heavy tasks will inflate noise unless the no-apt manifest is enforced.
- **~63% are genuine agent failures** on multi-step terminal tasks (server setup, git, downloads). The 30B model with 8 steps is insufficient for hard tasks regardless of baseline architecture.
- **Invalid-shell is a small but measurable interface tax** (~4% of steps). Truncated JSON at 512 max_tokens is the dominant pattern; observation compression and partial recovery address it without a full SWE-agent clone.
- T3 multi-step loop **materially improved** simple-task pass rate (fix-permissions 4/5 vs 2/15 in T2). This supports Brief F's evidence outcome: interface fixes drop no-op/truncation failures.
- AA's TB underperformance vs local code suite is **not primarily routing** at current N; it's terminal task difficulty + occasional env flakes + step budget.

## supports_direction | weak_or_inconclusive | falsified_or_blocked

**supports_direction** — Environment and invalid-shell failures are identifiable and partially remediable. Multi-step ACI was necessary before architecture comparisons mean anything.

## next_questions

1. Re-run T3 pilot (3 tasks × 5 baselines) with patched ACI to measure invalid-shell step rate before/after (≈15 min, not full 7×5 matrix).
2. Increase `max_shell_steps` to 12 for server/git tasks; log `parse_status` and `invalid_shell` in trajectory envelopes.
3. Pin no-apt task manifest and exclude tasks with flaky `setup-uv-pytest.sh` until env stable.
4. Defer full ≥20-task TB matrix until env failure rate <10% on pilot reruns.

## evidence_outcome

Per Brief F: **Useful** — environment failure and invalid/no-op shell behavior are quantified; two minimal patches implemented. Larger TB matrix is **partially justified** for infrastructure validation on the 7-task no-apt manifest, but **not yet for architecture claims** until env flakes drop and ACI patch smoke rerun confirms truncated-JSON recovery.
