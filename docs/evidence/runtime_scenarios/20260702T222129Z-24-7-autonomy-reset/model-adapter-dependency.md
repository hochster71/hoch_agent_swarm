# Model Adapter & Reverse SSH Tunnel Dependency Documentation

This document logs the runtime dependency details of the HELM AI Model Runner execution pipeline.

---

## 1. Dependency Details
* **Preferred Model Endpoint**: `http://localhost:11434/v1` (Native Ollama container on HOCH-200 executing qwen2.5:1.5b-instruct on CPU)
* **Fallback Model Endpoint**: `http://localhost:1234/v1` (LM Studio over reverse SSH tunnel executing google/gemma-4-12b-qat)
* **Reverse SSH Tunnel Dependency**: The fallback model uses a reverse SSH port forwarding tunnel:
  ```bash
  ssh -N -f -R 1234:localhost:1234 root@50.116.41.183
  ```
  This routes traffic back to Michael's local Mac machine.

---

## 2. Failure Modes & Mitigations
* **Native Model Offline**: If the local Ollama docker container crashes, the system automatically falls back to `lmstudio` over the reverse tunnel.
* **Tunnel Loss (Status: DEGRADED)**: If the local development machine goes offline or the SSH process terminates, the watchdog marks `lmstudio` as `DEGRADED`.
  * *Mitigation*: The `has-runtime-watchdog.service` probes both `/api/tags` on `11434` and `/v1/models` on `1234` every 10 seconds to maintain dynamic truth in `helm_adapter_registry.json` and `helm_runtime_state.json`.

---

## 3. Deployment Status
* **Native Ollama serving**: **🟢 ONLINE & ACTIVE** (Ollama Docker container `ollama` deployed on HOCH-200 running `qwen2.5:1.5b-instruct`).
* **Reverse SSH Tunnel**: **🟢 ONLINE & ACTIVE** (supervised fallback).
