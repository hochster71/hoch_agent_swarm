# Execution Plan — HOCH Agent Swarm RC15 Forward Execution

This document details target execution steps, parallel tasks, rollback mechanisms, and go/no-go release gates.

## Immediate next commands

1. **Verify host environment**:
   ```bash
   PYTHONPATH=src:. uv run pytest
   ```
2. **Launch Docker UI and verify endpoints**:
   ```bash
   ./scripts/docker_down.sh || true
   ./scripts/docker_up.sh
   curl -s http://127.0.0.1:8086/api/v1/operator/health
   curl -s http://127.0.0.1:8086/api/tv/health
   ```
3. **Trigger screenshot evidence captures**:
   ```bash
   ./scripts/docker_capture_screenshots.sh
   REQUIRE_LIVE_SCREENSHOTS=1 PYTHONPATH=src:. uv run pytest tests/test_live_screenshot_manifest.py
   ```
4. **Seal next release candidate**:
   ```bash
   uv run python scripts/release_seal.py v0.1.0-rc16
   ```

## Parallelizable tasks
- Host test suites (`PERT-002`) can execute concurrently with reviewer package inspections (`PERT-009`, `PERT-010`, `PERT-011`).
- Playwright screenshot extraction (`PERT-008`) runs independently of local SQLite database export checks (`PERT-005`).

## Stop Conditions
- **Test Failures**: Any failed test in pytest halts the execution path.
- **Docker Socket Timeout**: If the Docker daemon fails to respond or throws 500 version negotiation errors, execution halts.
- **SSRF Violation**: Any failed check on loopback/private network constraints in HOCH TV proxy halts deployment.

## Go/No-Go Release Gates
1. **Gate 1**: 100% of host tests pass (554 tests).
2. **Gate 2**: Screenshot manifest hashes match captured screens.
3. **Gate 3**: Operator health state contains no unresolved ConMon drift alerts.

## Release Sealing Command
```bash
uv run python scripts/release_seal.py v0.1.0-rc16
```

## Rollback Command
In case of critical failures:
```bash
git reset --hard HEAD
git clean -fd
docker compose down --remove-orphans
```

## Evidence Refresh Command
```bash
./scripts/docker_capture_screenshots.sh
```
