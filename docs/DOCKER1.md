# DOCKER1 — Containerized HOCH Agent Swarm Runtime & Playwright Screenshot Worker

> [!WARNING]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated.*

This document describes the design, compose structure, and execution parameters of containerizing the HOCH Agent Swarm runtime, enabling true Playwright headless Chromium screenshots inside a standard Linux container context.

---

## Architecture Overview

The container playground consists of three coordinated Docker services orchestrated via Docker Compose:

1. **`hoch-app`** (Dashboard Service):
   - **Image**: Built from `Dockerfile` based on `python:3.13-slim`.
   - **Purpose**: Runs the Flask dashboard, operator cockpit, and background agent orchestrations.
   - **Ports**: Exposes port `8086:8086` locally.
   - **Healthcheck**: Tests responsiveness of `/api/v1/operator/health` using native Python `urllib` calls.
   - **Volumes**: Maps local `artifacts/`, `data/`, and `docs/` directories for persistent state storage.

2. **`screenshot-worker`** (Browser Automation Service):
   - **Image**: Built from `Dockerfile.screenshot` based on Playwright's `v1.49.1-noble` image.
   - **Purpose**: Connects to the dashboard at `http://hoch-app:8086` and runs `scripts/capture_live_screenshots.py` using Chromium headless to capture live evidence.
   - **Profile**: Activated on-demand using the `screenshots` Docker Compose profile.
   - **Volumes**: Maps the output screenshot path `./artifacts/live_screenshots:/app/artifacts/live_screenshots`.

3. **`test-runner`** (CI Test Service):
   - **Image**: Shares the `Dockerfile` main python image.
   - **Purpose**: Executes the complete pytest suite inside a clean Linux container environment.
   - **Profile**: Activated on-demand using the `test` Docker Compose profile.

---

## Local-Only Security Boundary

All services are configured for local sandbox interaction only. External live IPTV rebroadcasts are disabled, and all incoming requests utilize loopback bindings.
- **Port Exposure**: Exposes port `8086` bound strictly to local interfaces.
- **Network Mode**: Uses isolated container-to-container DNS mapping (e.g. the screenshot worker accesses the app at `http://hoch-app:8086`).

---

## Commands Reference

### 1. How to Launch the Swarm Dashboard
To build and start the Flask web cockpit locally in a container:
```bash
cd ~/hoch_agent_swarm
./scripts/docker_up.sh
```
Access the running application at:
[http://localhost:8086](http://localhost:8086)

### 2. How to Run Containerized Pytests
To execute the repository test suite inside the Linux environment:
```bash
cd ~/hoch_agent_swarm
./scripts/docker_test.sh
```

### 3. How to Capture Live Browser Screenshots
To spin up the dashboard in the background and trigger the Playwright screenshot capture:
```bash
cd ~/hoch_agent_swarm
./scripts/docker_capture_screenshots.sh
```

### 4. How to Shutdown Services
To stop and remove all container resources, volumes, and networks:
```bash
cd ~/hoch_agent_swarm
./scripts/docker_down.sh
```

---

## Evidence Artifact Paths & Schema

All captured screens and metadata manifests are written to:
- `artifacts/live_screenshots/overview.png`
- `artifacts/live_screenshots/promptbrain.png`
- `artifacts/live_screenshots/promptqa.png`
- `artifacts/live_screenshots/evidencebrain.png`
- `artifacts/live_screenshots/hochtv.png`
- `artifacts/live_screenshots/operator.png`
- `artifacts/live_screenshots/manifest.json`

The manifest adheres to the following format:
```json
{
  "mode": "live-browser-capture",
  "runtime": "docker-compose-linux",
  "tool": "playwright-chromium-linux",
  "dashboardUrl": "http://hoch-app:8086",
  "capturedAt": "2026-06-28T15:30:00Z",
  "pages": [
    {
      "id": "overview",
      "file": "overview.png",
      "status": "captured",
      "sha256": "4b1f6d...",
      "selectorUsed": "#nav-overview",
      "error": ""
    }
  ]
}
```

---

## Known Limitations

- **Host Docker Access**: Running Docker Compose and the browser worker requires an active local Docker daemon socket. If the Docker daemon is down or inaccessible on the host system, local pytests will run in fallback skip mode.
