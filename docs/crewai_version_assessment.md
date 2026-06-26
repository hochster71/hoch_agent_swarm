# CrewAI Version Assessment
> Generated: 2026-06-26 · Batch 4 · Updated: 2026-06-26 Batch 7 · Hoch Agent Swarm

---

## Version Status

| | Version | Date |
|---|---|---|
| **Installed (pinned)** | `1.15.0` | Promoted Batch 7 |
| **Latest on PyPI** | `1.15.0` | 2026-06-25 |
| **Delta** | — (current) | — |

---

## What Changed in 1.15.0

Source: [GitHub releases — crewAIInc/crewAI v1.15.0](https://github.com/crewAIInc/crewAI/releases/tag/1.15.0)
Published: `2026-06-25T23:17:52Z`

### Features (all Flow/CLI-focused)
- Track conversational flow turn usage in telemetry
- Support conversational flows in the CLI TUI
- Add unified declarative flow loading
- Add declarative Flow CLI support
- Add optional `if` expression to `each.do` steps
- Add single agent action to Flow definitions
- Add crew actions to `FlowDefinition`
- Add inline crew definition loading
- Add `each` composite action to `FlowDefinition`
- Implement DMN mode support in crew creation and execution

### Bug Fixes
- Fix owner-only permissions enforcement on credential files
- Fix JSON schema flow state kickoff inputs
- **Fix symlink path traversal in skill archive extraction** ← security fix
- Aggregate token usage across all LLM calls
- Remove duplicated Exa tool
- Resolve JSON crew issues
- Fix JSON crew handling and enhance memory

---

## Risk Assessment for Hoch Agent Swarm

| Area | Risk | Rationale |
|---|---|---|
| Flow/Declarative APIs | **None** | The swarm uses `@CrewBase` + sequential `Process` only. No flows, no declarative loading. |
| DMN mode | **None** | Not used. |
| CLI TUI changes | **None** | Not relied upon in production runs. |
| Token usage aggregation | **Low positive** | Could improve telemetry accuracy; no breaking change expected. |
| Symlink security fix | **Low positive** | Fixes a traversal vulnerability in skill archive extraction. Not directly triggered by this project, but beneficial. |
| JSON crew handling | **Unknown** | The swarm does not use JSON crew format, but underlying serialization changes could affect task output handling. Worth verifying. |
| Credential file permissions | **Low positive** | Tightens enforcement; no expected regression for Ollama-only workflows. |
| `function_calling_llm` deprecation | **Pending** | The 176 deprecation warnings from `1.14.7` are from internal CrewAI code. This batch confirms `1.15.0` was published after several alphas — the warnings may be resolved in `1.15.0`. |

> [!IMPORTANT]
> **The symlink security fix is the only item with operational security relevance.**
> It affects skill archive extraction, not the core agent execution path used by this project.
> Upgrading for this fix alone is reasonable once the workflow is re-validated.

---

## Why the Upgrade is Deferred

1. **Timing**: `1.15.0` was released 7 hours before this assessment. No community validation period has elapsed.
2. **Workflow sealed**: Batches 1–3 sealed the execution contract against `1.14.7`. Introducing a runtime change before the sealed workflow is validated against the new artifact paths (added in Batch 4) would create compound variables.
3. **No blocking feature requirement**: None of the `1.15.0` features are required for the Hoch Agent Swarm workflow (`@CrewBase`, sequential process, Ollama LLM, file `output_file` tasks).
4. **Deprecation unknown state**: The 176 deprecation warnings may be addressed in `1.15.0`, or they may have moved. Re-running the test suite against `1.15.0` is the only way to know.

---

## Recommended Upgrade Test Sequence

When ready to evaluate, execute in this exact order:

```bash
# 1. Verify baseline is clean
uv run pytest -q

# 2. Upgrade in an isolated environment
uv sync --upgrade-package crewai

# 3. Confirm installed version
uv run python -c "import crewai; print(crewai.__version__)"

# 4. Run full test suite — expect any new deprecation warnings to surface
uv run pytest -q

# 5. Run live crew to confirm artifact output quality is unchanged
uv run run_crew

# 6. Run tests again with live artifacts
uv run pytest -q

# 7. If all pass, commit updated uv.lock
git add uv.lock pyproject.toml
git commit -m "chore: upgrade crewai to 1.15.0"
```

### Rollback

If the upgrade causes test failures or artifact validation errors:

```bash
# Restore pinned version
git checkout -- pyproject.toml uv.lock
uv sync
uv run python -c "import crewai; print(crewai.__version__)"  # should be 1.14.7
```

---

## Recommendation

**PROMOTED** (as of 2026-06-26, Batch 7 shim assessment).

`crewai 1.15.0` is **compatible** with this Ollama/local LLM runtime and has been
promoted to `main`. Pytest: 123 passed. Live crew: PASS. All 5 artifacts VALID.

**Batch 6 BLOCKED decision — corrected root cause**: The Batch 6 trial run failed
with `ValueError: OPENAI_API_KEY is required` because the `.env` file was not
present in the trial worktree (git worktrees do not copy gitignored files). Without
`MODEL=ollama/llama3.1:8b` set, `crewai 1.15.0` fell back to `gpt-4o` and routed
through the OpenAI native provider. This was a trial environment setup defect, not
a 1.15.0 regression.

**Operational prerequisite**: The `.env` file must be present in the working
directory before running the crew. This requirement exists on both 1.14.7 and 1.15.0;
1.15.0 makes it fail faster and more explicitly (at client construction vs. inference).

**Full trial memo**: `docs/crewai_1_15_0_trial_memo.md` (in `trial/crewai-1.15.0` branch).

**Installed**: `crewai[tools]>=1.15.0,<2` — resolves to `1.15.0`.


---

## Isolated Trial Procedure (Batch 8+)

Use a git worktree so the main branch is never touched during the upgrade trial.
`run_report.json` provides the measurable before/after baseline.
`trial_preflight` blocks a trial run if required local runtime inputs are absent.

> **Batch 7 lesson**: git worktrees do not copy gitignored files. A missing `.env`
> causes `crewai` to fall back to `gpt-4o` and fail with `OPENAI_API_KEY is required`.
> The preflight script (Step 0 and Step 2b) makes this impossible to miss.

### Step 0 — Preflight on main (before creating the worktree)

```bash
# Verify the local runtime is healthy on main before starting anything
uv run trial_preflight
# Must exit 0. If blocked, fix the issue before proceeding.
```

Expected output:
```
  ✅ env_file_present: .env found at ...
  ✅ model_env_var_set: MODEL='ollama/llama3.1:8b'
  ✅ api_base_env_var_set: API_BASE='http://localhost:11434'
  ✅ ollama_endpoint_reachable: HTTP 200 from http://localhost:11434
  ✅ baseline_run_report_exists [warn-only]: latest baseline: ...

preflight: PASS — all blocking checks passed
```

### Step 1 — Collect a baseline run report on main

```bash
uv run run_crew
# Note the run_report.json path printed:
# [report] Run report written: artifacts/crew_runs/<timestamp>/run_report.json
BASELINE_REPORT="artifacts/crew_runs/<timestamp>/run_report.json"
```

### Step 2 — Create an isolated worktree

```bash
TRIALS_DIR=~/hoch_agent_swarm_trials
mkdir -p "$TRIALS_DIR"
WORKTREE="$TRIALS_DIR/crewai-<new-version>-trial"
git worktree add "$WORKTREE" -b trial/crewai-<new-version>
cd "$WORKTREE"
```

### Step 2b — Symlink .env into the trial worktree  ← MANDATORY

```bash
# Git worktrees do NOT copy gitignored files. Without this step,
# crewai will fall back to gpt-4o and fail with OPENAI_API_KEY is required.
ln -sf /Users/michaelhoch/hoch_agent_swarm/.env ./.env
ls -la .env  # verify symlink resolves
```

### Step 3 — Upgrade CrewAI in the trial worktree only

```bash
# Relax the pin in pyproject.toml (trial branch only):
#   "crewai[tools]==<current>" → "crewai[tools]>=<new>,<2"
uv sync
uv run python -c "import crewai; print(crewai.__version__)"  # expect <new-version>
```

### Step 4 — Run preflight in the trial worktree

```bash
# Verify the symlinked .env is loaded and Ollama is still reachable
uv run trial_preflight
# Must exit 0. If blocked, fix before proceeding.
```

### Step 5 — Run tests

```bash
uv run pytest -q
# Stop here if any test fails. Do not continue to live run.
```

### Step 6 — Live crew run with run report

```bash
uv run run_crew
TRIAL_REPORT="artifacts/crew_runs/<timestamp>/run_report.json"
```

### Step 7 — Compare run reports

```bash
# Automated comparison — replaces the manual inline python3 script
uv run compare_reports "$BASELINE_REPORT" "$TRIAL_REPORT"
# exit 0 = PROMOTE, exit 1 = INVESTIGATE or BLOCK
```

Machine-readable output:
```bash
uv run compare_reports --json "$BASELINE_REPORT" "$TRIAL_REPORT"
```

The tool diffs `status`, `crewai_version`, `mcp_stub_version`, `errors`,
per-artifact `validation_status`, and size deltas.
SHA-256 changes are noted as informational — artifact content varying run-to-run
is expected for LLM output. The verdict is based on validation status, not hashes.

| Verdict | Meaning |
|---|---|
| `PROMOTE` | Trial passed all gates — proceed to Step 8 |
| `INVESTIGATE` | Trial passed but has non-fatal anomalies — review findings |
| `BLOCK` | Trial failed or regressed — do not promote; see findings |


### Step 8 — Decision

| Outcome | Action |
|---|---|
| Tests pass, artifacts valid | Promote: commit `uv.lock` + `pyproject.toml` to main |
| Tests fail or artifacts invalid | Revert trial branch; main is never touched |

### Step 9 — Promote or revert

**Promote (on main):**
```bash
cd /Users/michaelhoch/hoch_agent_swarm
# Update pyproject.toml on main to match trial constraint
# uv sync → verify version
# uv run pytest -q → must pass
# uv run run_crew → must PASS
git add pyproject.toml uv.lock docs/crewai_version_assessment.md
git commit -m "chore: promote crewai to <new-version>"
# Clean up trial worktree
git worktree remove "$WORKTREE" --force
git branch -D trial/crewai-<new-version>
```

**Revert (trial only — main is never touched):**
```bash
cd /Users/michaelhoch/hoch_agent_swarm
git worktree remove "$WORKTREE" --force
git branch -D trial/crewai-<new-version>
# Main remains at prior version with uv.lock unchanged
```
