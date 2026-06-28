# CURRENT_STATE.md — Swarm State Handoff

## Release Metadata
- **Current Release Tag**: `v0.1.0-rc15`
- **Latest Commit**: `ce6d3c8`
- **Release Candidate Configuration**: [release_candidate.json](file:///Users/michaelhoch/hoch_agent_swarm/artifacts/release_candidates/20260628T164855/release_candidate.json)

## Test Status
- **Host Unit/Integration Tests**: 554 / 554 automated tests passing (`PYTHONPATH=src:. uv run pytest`).
- **Containerized Tests**: 554 / 554 passing (`docker compose --profile test run --rm test-runner`).
- **Screenshot Manifest Verification**: Passed (`REQUIRE_LIVE_SCREENSHOTS=1 PYTHONPATH=src:. uv run pytest tests/test_live_screenshot_manifest.py`).

## Runtime & Docker Status
- **Docker Daemon**: Active
- **Running Container**: `hoch-agent-swarm-app` (healthy, running dashboard application)
- **UI URL**: http://localhost:8086
- **Operator Health Status**: Subsystems healthy. PromptQA average score is `73.1` (reporting degraded status as expected by design for simulation parameters).

## Playback Mode & Security Controls (HOCH TV)
- **Playback Path**: http://localhost:8086/api/tv/stream/<channel_id>/master.m3u8
- **Asset Segment Path**: http://localhost:8086/api/tv/stream/<channel_id>/asset?url=<hex>
- **SSRF Validation**: Active. Decoded segment hosts must match the corresponding channel host (or be a whitelisted stream provider). Loopback and private network targets are strictly blocked.
- **Direct Remote Playback**: Prohibited in the browser (CORS-free playback handled exclusively by the local loopback proxy).

## Active Tasks & Open Blockers
- **Active Tasks**: None. Recovery and verification successfully completed.
- **Open Blockers**: None.

## Run Commands Quick Reference
```bash
# Clean start containerized cockpit
./scripts/docker_down.sh || true
./scripts/docker_up.sh

# Perform live screenshots capture
./scripts/docker_capture_screenshots.sh

# Run full test suite on host
PYTHONPATH=src:. uv run pytest

# Run tests in docker container
./scripts/docker_test.sh

# Seal next release candidate
uv run python scripts/release_seal.py v0.1.0-rc16
```

## Security & Compliance Boundary Declarations
- **ATO-supporting evidence package ready for review.**
- **Actual ATO has not been granted.**
- **No authorization claim is being made.**
- **Risks are not fully eliminated.**
- **System is local-only unless explicitly configured otherwise.**

---
*Created dynamically at the end of PERT1 (2026-06-28).*
