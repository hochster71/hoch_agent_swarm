# HELM Autonomous Model Runner Doctrine

This document defines the operation doctrine of the HELM AI execution engine.

---

## 1. Core Operating Principles
* **State Driven**: HELM does not accept manual input parameters. It reads `helm_task_queue.json`, identifies the first task marked `queued`, and processes it.
* **Model/Agent Mapping**: HELM resolves the task requirement, queries `helm_agent_registry.json` to assign the matching agent capability, and routes the inference request to the configured local or remote provider.
* **No Direct Command Line Building**: HELM executes tasks via dedicated python adapters and AG assistants. It does not run arbitrary bash command lines.
* **Evidence Ledger Enforcement**: Every execution step must log its input, output, system timestamp, and model metrics to `helm_execution_log.json` and generate an evidence markdown file.
* **Founder Release Lock**: The runner has no authorization to publish or promote production release candidates without explicit founder signature evidence.
