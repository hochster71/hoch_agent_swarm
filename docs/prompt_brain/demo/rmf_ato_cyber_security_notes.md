# HOCH RMF/ATO Cybersecurity Prompt Pack — Security & Zero-Leakage Architecture

This document details data protection controls and system boundaries of the Prompt Brain local execution engine.

---

## 1. Local-Only Execution Architecture
* **Adapter Isolation**: All remote pipelines (OpenAI, Gemini) are disabled unless explicitly configured by environment keys.
* **Local Loop**: Prompts are dispatched exclusively to localhost addresses (`http://localhost:1234/v1` for LM Studio and `http://localhost:11434/api` for Ollama).
* **Zero Telemetry Leakage**: No telemetry, model weights, or input artifacts are forwarded outside the host boundary.

---

## 2. Input Sanitization Guidelines
* **Do Not Upload Sensitive Information**: Users should review all files in `/demo_evidence_inputs` to ensure no controlled, proprietary, or classified data is included before running workflows.
* **Hash Checksums**: All output reviews are hashed locally to ensure document integrity is traceable.
