# Architecture Lock — HELM Full-Time Orchestration Bridge

---

## 1. Problem Statement
Michael manually copies and pastes prompts between OpenAI, Claude, and local AG scripts. This is the primary blocker to autonomous execution.

---

## 2. Operating Model
* **HELM**: Primary orchestrator and mission parser.
* **OpenAI (Reasoning Adapter)**: Generates logical decomposition maps.
* **Claude (Critic Adapter)**: Code review and prompt validation checks.
* **AG (Execution Adapter)**: Modifies workspace files and executes local tests.
* **ollama_gpu_pod**: Local heavy model task running (e.g. Qwen 32B).
* **HAS/HASF**: Hosts validation gates, tracks logs, signs evidence.

---

## 3. OWASP LLM01 Defense-in-Depth Boundary
* **Intent Sanitizer**: Serves as a bypassable detection layer 1 (input validation).
* **Enforcement Boundary**: The primary enforcement boundary is composed of the Policy Engine, Data Egress Policy, and Founder Gates. This ensures that even if layer 1 is bypassed, unauthorized or destructive actions are strictly blocked.
