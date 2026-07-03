# Model Capacity Evaluation Comparison

This document details the comparative performance of model backend options evaluated on the HASF L3 golden test sets.

---

## 1. Capacity & Performance Comparison

| Model | Size | Hardware Host | Average Latency | G-EVAL Mean Score | Key Capacity Classification |
|---|---|---|---|---|---|
| **qwen2.5:1.5b-instruct** | 1.5B | VPS (Local CPU) | 12s | 3.2 / 5.0 | Planning, light coding roadmaps |
| **qwen2.5:14b-instruct** (Planned) | 14B | VPS (Local CPU) | 45s (Est) | 4.1 / 5.0 (Est) | Heavy reasoning, structured QA |
| **google/gemma-4-12b-qat** | 12B | Mac Studio (via Tunnel) | 18s | 4.5 / 5.0 | High-quality judging, contract verification |

---

## 2. Evaluation Findings

1. **qwen2.5:1.5b-instruct**: Good for lightweight roadmaps, but fails complex validation structures or nested logic criteria. Retries are common.
2. **google/gemma-4-12b-qat (LM Studio)**: Delivers stable structured json formatting and reliable judging rubrics. Highly suited for contract gating.
