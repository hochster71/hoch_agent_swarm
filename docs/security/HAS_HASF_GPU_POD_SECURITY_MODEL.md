# HAS/HASF GPU Pod Security Model

This document outlines the security controls, communication requirements, and lifecycle constraints applied to ephemeral GPU execution nodes (`ollama_gpu_pod`).

---

## 1. Network Security & Tunneling
* **Private API Exposure**: The GPU pod must never expose port `11434` publicly.
* **Encrypted Path**: All traffic from `HOCH-200` to the GPU pod must run through:
  - Tailscale private mesh subnet.
  - SSH Local/Remote Port Forwarding tunnel:
    `ssh -N -L 11434:localhost:11434 root@<GPU_POD_IP>`

---

## 2. Data Gating & Zero-Trust
* **No Secrets**: No API keys, VCS tokens, or application credentials may be written to or configured on the GPU pod.
* **No Source of Truth**: The GPU pod serves only as an instruction-in / text-out inference engine. It holds no persistent workspace data or database files.
* **No Deployment/Release Authority**: The policy engine blocks any execution request requesting deployment or release keys from running on or using outputs from the GPU pod without a separate verification step.

---

## 3. Teardown & Lifecycle
* **Ephemeral Mandate**: At the end of every active factory run, run the teardown script:
  `python3 scripts/teardown_gpu_pod_adapter_state.py`
  to scrub registry access.
