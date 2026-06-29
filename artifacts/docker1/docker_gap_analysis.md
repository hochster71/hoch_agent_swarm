# DOCKER1 Gap Analysis — Containerized HOCH Agent Swarm Runtime

> [!WARNING]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated.*

This gap analysis reviews the local sandbox environment of the `hoch_agent_swarm` repository to map the requirements of containerizing the dashboard runtime, Linux screenshot worker, and docker-compose configurations.

## Baseline Audit & Findings

A comprehensive scan of the repository root and subdirectories shows the following current states:
- **Application Portability**: The Flask dashboard currently launches successfully on macOS via `operator_launch` or `ui_server.py`.
- **IPTV Proxy Cache**: The M3U and XMLTV proxy services rely on file paths under `data/` and `artifacts/` which need persistent Docker volume mappings.
- **Screenshot Automation**: Browser screenshots are currently mocked out due to macOS Chrome automation limitations; a Linux-based container with Playwright/Chromium will allow true live browser capture.

---

## Identified Gaps

| Category | Gap Description | Proposed Remediation |
|---|---|---|
| **Build Configurations** | No `Dockerfile` exists for the main python runtime. | Create a multi-stage or slim python-based Dockerfile using `python:3.13-slim` that installs `uv`, copies dependencies, and defaults to `operator_launch`. |
| **Compose Orchestration** | No `docker-compose.yml` or `.dockerignore` exists. | Define services `hoch-app` (Flask app), `screenshot-worker` (Playwright worker), and `test-runner` (CI tests). Configure healthchecks, profiles, and volumes. |
| **Worker Automation** | No screenshot worker Playwright script exists. | Create `scripts/capture_live_screenshots.py` using Chromium headless to navigate to the 6 dashboard tabs, take full-page captures, write to volume, and produce `manifest.json`. |
| **Orchestration Scripts** | Missing bash launch wrappers. | Create `scripts/docker_up.sh`, `docker_down.sh`, `docker_test.sh`, and `docker_capture_screenshots.sh`. Make them executable. |
| **Test Verification** | Missing Docker test assertions. | Create `tests/test_docker_files.py` to assert presence of all files and structures. Create `tests/test_live_screenshot_manifest.py` to validate manifest compliance. |
| **Documentation** | Missing container run instructions. | Create `docs/DOCKER1.md` documenting compose commands, profiles, networking, volumes, and compliance limitations. |
