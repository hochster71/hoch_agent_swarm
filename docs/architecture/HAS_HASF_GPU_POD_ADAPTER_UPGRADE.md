# HAS/HASF GPU Pod Adapter Upgrade Architecture

This document maps out the architecture for integrating an accelerated burst GPU pod (RTX 4090) into the HAS/HASF/HELM runtime environment.

---

## 1. Topography & Division of Labor
* **HOCH-200 (Governance Plane)**: Retains the source of truth, watchdog checks, task queue, evidence manifest, and policy engine.
* **GPU Pod (Execution Plane)**: Acts purely as an ephemeral model execution backend (`ollama_gpu_pod` adapter).
* **Mac Studio**: Tertiary fallback only.

---

## 2. Target Models & Providers
* **Primary hardware**: RunPod Community or Secure Cloud RTX 4090 (24GB VRAM).
* **Fallback hardware**: Vast.ai (cheaper live market).
* **Models**:
  - `qwen2.5-coder:32b` (Primary coding and evaluation candidate).
  - `qwen2.5:32b` (General reasoning and structured outputs).
  - `qwen2.5-coder:14b` (Optional fallback).

---

## 3. Promotion Gates
An ephemeral pod adapter is only promoted to the active routing table if it passes:
1. `verify_model_adapter_health.py`
2. `verify_agent_output_quality.py` (G-EVAL battery check)
3. `verify_runtime_truth_freshness.py`
4. `verify_no_secret_leakage.py`
5. `verify_gpu_pod_adapter.py`
