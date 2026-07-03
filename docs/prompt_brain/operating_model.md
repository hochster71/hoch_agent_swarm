# HOCH Prompt Brain Factory — Operating Model

This document outlines the operational model, execution loops, convergence rules, and runtime synchronization protocols for the **HOCH Prompt Brain Factory**.

---

## 1. Operational Rhythm

The Prompt Brain Factory runs under three operational triggers:
1. **Autonomic Expansion Cycles**: Recurring schedules designed to expand coverage across the NAICS/SOC graphs.
2. **On-Demand Domain Ingestion**: Triggered by the Mission Commander when a new business or technical requirement is introduced.
3. **Continuous Drift Compliance**: Scans and evaluates existing prompts when security baselines (such as NIST or CISA) are updated.

---

## 2. The Convergence Threshold

The loop runs recursively until the system achieves **Coverage Convergence**, defined as:
* **No Uncovered Tasks**: Every atomic task identified in the active scope contains an approved 12-prompt family.
* **Marginal Utility limit**: The number of new unique prompts generated per loop iteration falls below the target threshold.
* **Cryptographic Sync**: All approved prompts are registered in the evidence ledger with matching SHA256 hashes.
* **Zero Critical Findings**: No outstanding critical red-team findings exist.

---

## 3. Integration with the Active Swarm Runtime

Once a prompt passes the release gates (QA score >= 90, Red-Team findings = 0), the factory synchronizes it:
1. The **Evidence Ledger Agent** appends the prompt to `/data/prompt_brain/approved_runtime_prompts.jsonl`.
2. The **HASF Builder Agent** compiles these approved prompts and syncs them into the runtime JSON catalogs (`data/prompt_registry/hoch_agent_swarm_prompt_library_v3_enhanced.json` and others).
3. The active swarm agents (e.g. `SH-04` Security Agent) load these prompts dynamically via `PromptRegistry`.
