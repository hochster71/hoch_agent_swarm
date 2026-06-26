# CrewAI Version Assessment
> Generated: 2026-06-26 · Batch 4 · Hoch Agent Swarm

---

## Version Status

| | Version | Date |
|---|---|---|
| **Installed (pinned)** | `1.14.7` | — |
| **Latest on PyPI** | `1.15.0` | 2026-06-25 |
| **Delta** | 1 minor version | Released ~7 hours before this assessment |

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

**Defer.** Reassess after:
1. The Batch 4 intermediate artifact live run is validated (`uv run run_crew`).
2. At least one week of community stabilization time has elapsed for `1.15.0`.
3. The `filterwarnings` suppression in `pyproject.toml` is verified not to mask new real warnings in `1.15.0`.

**Estimated window**: Batch 5 or later.
