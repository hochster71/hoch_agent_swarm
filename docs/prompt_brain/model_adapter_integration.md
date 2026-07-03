# HOCH Prompt Brain — Model Adapter Integration (Hardened)

This document outlines the hardened Model Adapter Layer supporting local model health verification, health reason codes, and fail-closed configurations.

---

## 1. Adapter Status Properties

All model adapters return standard schema definitions containing:
* `health_reason_code`: `"ENDPOINT_REACHABLE" | "MISSING_API_KEY" | "ENDPOINT_UNREACHABLE" | "SIMULATION_FALLBACK_ALWAYS_AVAILABLE"`
* `local_remediation_hint`: Step-by-step guidance for operators to resolve offline adapters.
* `available_models`: Discovered local/cloud models (e.g. models returned by LM Studio's `/v1/models` endpoint).
* `last_successful_execution`: ISO timestamp of the last successful run.
* `execution_mode`: `"live_model" | "simulated"`.

---

## 2. Local Adapters
* **LM Studio**: Automatically polls `http://127.0.0.1:1234/v1/models` and discovers loaded models (e.g. `lmeta-3-8b`).
* **Ollama**: Automatically polls `http://127.0.0.1:11434/api/tags` and discovers installed tags.
