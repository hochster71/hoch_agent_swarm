# Model Adapter & Reverse SSH Tunnel Dependency Documentation

This document logs the runtime dependency details of the HELM AI Model Runner execution pipeline.

---

## 1. Dependency Details
* **Model Endpoint Path**: `http://localhost:1234/v1` (LM Studio OpenAI compatible endpoint)
* **Reverse SSH Tunnel Dependency**: The remote VPS `HOCH-200` has no local GPU resources to serve `google/gemma-4-12b-qat`. Instead, it relies on a reverse SSH port forwarding tunnel:
  ```bash
  ssh -N -f -R 1234:localhost:1234 root@50.116.41.183
  ```
  This routes traffic targeting `localhost:1234` on `HOCH-200` back to the local development Mac where LM Studio is hosted.

---

## 2. Failure Modes & Mitigations
* **Tunnel Loss (Status: DEGRADED)**: If the local development machine goes offline or the SSH process terminates, HELM requests fail with connection errors.
  * *Mitigation*: The `has-runtime-watchdog.service` continuously probes `/v1/models` every 10 seconds. If unreachable, it updates `helm_adapter_registry.json` and `helm_runtime_state.json` to `DEGRADED`, disabling queue scheduling until connection is restored.
* **Stale State Recovery**: If the tunnel drops and returns, the watchdog automatically recovers state back to `ONLINE`.

---

## 3. Tunnel Persistence Plan
* **Option A (Target Architecture)**: Move model serving directly to a dedicated local container on `HOCH-200` via Ollama when resources allow.
* **Option B (Immediate Mitigation)**: Establish a local Mac plist daemon/launchd configuration to automatically keep the reverse SSH tunnel alive:
  `/Users/michaelhoch/Library/LaunchAgents/com.hoch.ssh-tunnel-1234.plist`
