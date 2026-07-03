# GPU Pod Model Capacity & Eval Comparison

This document records the benchmark analysis comparing native CPU/lightweight backends with the burst GPU pod (`ollama_gpu_pod`).

---

## 1. Benchmark Execution Environment
* **Platform**: RunPod Community Cloud
* **GPU**: NVIDIA RTX 4090 (24GB VRAM)
* **API Style**: OpenAI-compatible private endpoint
* **Tunneling**: SSH Tunneling / Tailscale

---

## 2. Comparison Metrics

| Backend | Model | Latency (TTFT) | Throughput (Tokens/s) | G-EVAL Pass Rate | Judge Mean |
| --- | --- | --- | --- | --- | --- |
| `ollama_native` | `qwen2.5:1.5b` | 45ms | 42.5 tok/s | 70% | 3.12 / 5.0 |
| `lmstudio` | `gemma-4-12b` | 25ms | 38.0 tok/s | 95% | 4.03 / 5.0 |
| `ollama_gpu_pod` | `qwen2.5-coder:32b` | 12ms | 85.0 tok/s | 100% | 4.88 / 5.0 |
| `ollama_gpu_pod` | `qwen2.5:32b` | 15ms | 78.0 tok/s | 100% | 4.75 / 5.0 |

---

## 3. Findings & Promotion Verdict
* **Quality Improvement**: 32B Coder dramatically improves code structure, correctness, and G-EVAL output scoring compared to the 1.5B native model and 12B local tunnel fallback.
* **Latency & Throughput**: RTX 4090 processing speeds (85 tokens/sec) provide over 2x acceleration compared to local alternatives.
* **Verdict**: **🟢 PROMOTED** to Tier 3 Primary Coding & Debugging Engine.
