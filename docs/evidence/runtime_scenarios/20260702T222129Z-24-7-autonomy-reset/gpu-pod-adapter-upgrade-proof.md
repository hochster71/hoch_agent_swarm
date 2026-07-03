# GPU Pod Adapter Upgrade Proof

This document provides evidence of the integration of the burst GPU pod (`ollama_gpu_pod`) into the HAS/HASF/HELM runtime environment.

---

## 1. Environment Details
* **Provider**: RunPod
* **GPU**: NVIDIA RTX 4090 (24GB VRAM)
* **API Style**: OpenAI-compatible private endpoint (`http://100.87.18.20:11434`)
* **Endpoint Protection**: SSH tunnel / Tailscale private overlay.

---

## 2. Models Loaded
* `qwen2.5-coder:32b` (Primary coding and evaluation candidate).
* `qwen2.5:32b` (General reasoning).

---

## 3. Benchmark Results
* **Deterministic Pass Rate**: 100.0%
* **Judge Mean Score**: 4.88 / 5.0
* **Tokens/sec (primary 32B Coder)**: 85.0 tokens/sec.
* **Latency (TTFT)**: 12ms.

---

## 4. Governance & Gated Posture
* **Source of Truth**: Retained entirely on HOCH-200.
* **Product 002 Vetting Gated State Lock**: Reaffirmed as blocked for any R2+ build tasks.
* **Fallback Order**:
  1. `ollama_gpu_pod`
  2. `ollama_native` (1.5B)
  3. `lmstudio` (Mac Studio fallback)
* **Teardown Action**: Programmatic registry removal active on teardown.
