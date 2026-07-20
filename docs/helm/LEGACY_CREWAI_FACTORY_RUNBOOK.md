# Legacy CrewAI Factory — activation runbook

**Status: OPTIONAL EXTRA (dormant).** Council-authorized dependency-surface reduction,
2026-07-19: `crewai[tools]` moved from the default dependency set to the
`legacy-crewai-factory` extra. Evidence trail: `coordination/evidence/sbom_cve_20260719/`.

## Why it was optionalized
The HELM runtime (`backend/`) has zero crewai imports; the SI environment reported crewai
not installed; and the crewai transitive graph carried both remaining A3 package risks —
`json-repair` (GHSA-xf7x-x43h-rpqh, unfixable while crewai pins `<0.26`) and `chromadb`
(PYSEC-2026-311, no fixed release). Optionalizing removed **106 packages** from the default
resolution (196 → 90) and took the default-runtime lock-level audit to **0 findings**.

## What still lives where
- Factory source (unchanged): `src/hoch_agent_swarm/` (crew.py, model_router.py,
  run_report.py, release_candidate.py, tools/custom_tool.py)
- Factory tests (unchanged, skip when crewai absent): `tests/test_crew_smoke.py`,
  `tests/test_model_router.py`, `tests/test_swarm_pipeline.py`, `tests/test_entry_points.py`
- Pre-optionalization lockfile: `coordination/evidence/sbom_cve_20260719/uv.lock.pre_optionalization`
- Entry points (`run_crew`, `train`, …) remain declared in `pyproject.toml`; they fail
  with ImportError unless the extra is installed — that is intended fail-closed behavior.

## Activating the lane (deliberate, non-default, ISOLATED)

**Never install the extra into the HELM production venv.** The lane runs in its own
virtual environment so its 2 open advisories can never reach the production runtime:

```bash
uv venv .venv-crewai
UV_PROJECT_ENVIRONMENT=.venv-crewai uv sync --frozen --extra legacy-crewai-factory
.venv-crewai/bin/python -m pytest tests/test_crew_smoke.py tests/test_model_router.py -q
```

### Activation gate — ALL required before any use
1. Explicit operator request (no automated activation path may exist)
2. Non-production environment only
3. Separate virtual environment (`.venv-crewai`, never `.venv`)
4. Advisory acknowledgement: json-repair GHSA-xf7x-x43h-rpqh + chromadb PYSEC-2026-311 are OPEN
5. No production credentials inherited into the lane environment
6. No automatic HELM startup registration (no launchd/systemd/supervisor entry)
7. No routing assignment without authorization (no model_routing registry entry may point at this lane)
8. Evidence produced by the lane is marked `evidence_class: LEGACY_OPTIONAL_LANE` — it can
   never satisfy a production requirement or gate

### Interpreter-identity check (run BEFORE any CrewAI code)
Declaring the isolated environment is not the same as using it — PATH drift or stale shell
activation can silently substitute the production interpreter:
```bash
.venv-crewai/bin/python -c '
import os, sys
expected = os.path.realpath(".venv-crewai")
actual = os.path.realpath(sys.prefix)
if actual != expected:
    raise SystemExit(f"Wrong environment: expected {expected}, got {actual}")
print("interpreter identity OK:", actual)
'
```

### Additional fail conditions (abort activation if ANY is true)
- `HELM_ENV=production` is set in the lane environment
- production secrets/API keys are present in the lane environment
- production database URLs are present
- production routing registration is enabled (any model_routing entry pointing at this lane)
- the default HELM venv (`.venv`) and the CrewAI venv resolve to the same real path

A default `uv sync` must never install the extra — `run_dependency_runtime_confirmation.sh`
fails closed if crewai/chromadb/json-repair appear in the default venv.

## Security posture of the lane (segmented — NOT part of default posture)
The extra retains **2 open advisories** until upstream resolution or lane retirement:
`json-repair` 0.25.3 (crewai pin blocks the 0.60.1 fix — override NOT authorized) and
`chromadb` 1.1.1 (no fixed release; risk record `coordination/goal/findings/CHROMADB_RISK.json`).
Do **not** report these as remediated, and do **not** let them contaminate the default
A3 posture. Re-assess on every crewai upgrade; retire the lane if the factory stays dormant.

## Deactivating / retiring
Default `uv sync --frozen` already excludes the lane. Full retirement = delete the extra,
archive `src/hoch_agent_swarm/` per the quarantine process, and close CHROMADB_RISK as
REMOVED.
