# GitHub Linux Runner QA Evidence

* **Created At**: 2026-07-02T16:40:10-05:00
* **Status**: `Dual-Runner Strategy Active`

---

## Existing Workflows Discovered
* `.github/workflows/has-qa-runner.yml` (macOS self-hosted)
* `.github/workflows/has-local-runtime-runner.yml` (macOS self-hosted)

---

## Changes Made
* Created `.github/workflows/qa-linux.yml` to target `ubuntu-latest`.
* Created `.github/workflows/qa-macos.yml` to mirror self-hosted macOS tests.
* Created `docs/ci/GITHUB_RUNNER_MATRIX.md` to define scope and exclusions.

---

## Mapped Runner Scopes

### Linux Runner Scope
* Backend Python unit tests (Michael AI, HELM, Apple telemetry logic).
* Static safety gates (`scan_host_paths.sh`, `scan_hardcoded_status.sh`, `anti_fake_gate.sh`).
* Frontend compilation (`npm run build`).

### macOS Runner Scope
* E2E Playwright specs.
* macOS visual hygiene scripts.
* Live local telemetry tests using `pmset` / `system_profiler`.

### Local / Manual Scope
* Tailscale endpoint checks.
* `scripts/hoch200_gate.sh` (live SSH to VPS).
* `scripts/moonshot_remote_ui_gate.sh` (verifying active reverse port-forwarding).

---

## Local Verification Commands Run
All static checks and unit tests pass locally:
* `bash scripts/scan_host_paths.sh`: PASS
* `bash scripts/scan_hardcoded_status.sh`: PASS
* `uv run pytest tests/unit/helm`: PASS
* `uv run pytest tests/unit/michael_ai`: PASS
* `npm run build`: PASS
