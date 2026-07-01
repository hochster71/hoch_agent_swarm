# HOCH Visual Control Plane Controlled Dashboard Adapters

This document details the visual adapter functions designed to normalize and validate telemetry data before rendering it in the UI.

---

## 1. Adapter Architecture & Guarantees

All adapters implemented in `frontend/visual_adapters.js` are pure Javascript functions. They do not execute fetch calls, DOM mutations, WebSockets, or side-effects. This prevents unauthorized execution, excessive agency, and incorrect data representations.

### Enforced State Truth Rules
*   **Missing Source** $\rightarrow$ `UNAVAILABLE`
*   **Stale Data** $\rightarrow$ `STALE`
*   **Security Ambiguity** $\rightarrow$ `FAIL-CLOSED`
*   **Static Mock Data** $\rightarrow$ `SIMULATED`
*   **Pending Implementation** $\rightarrow$ `PENDING`
*   **Partial Usable Evidence** $\rightarrow$ `DEGRADED`
*   **Valid Current Evidence** $\rightarrow$ `LIVE`

---

## 2. Adapter Function Directory

1.  **`normalizeState(input)`**: Validates and normalizes state string labels against the 8 allowed states.
2.  **`isFresh(timestamp, freshnessSeconds)`**: Calculates if the payload timestamp is within the freshness window.
3.  **`adaptCockpitTelemetry(payload)`**: Normalizes `/api/v1/live-runtime/cockpit` data.
4.  **`adaptPromptRegistry(payload)`**: Adapts the prompt registry.
5.  **`adaptKnownAssets(payload)`**: Normalizes Ubiquiti network assets topology map.
6.  **`adaptApprovalQueue(payload)`**: Evaluates enqueued operator requests.
7.  **`adaptEvidenceManifest(payload)`**: Asserts SBOM/attestation checksum presence.
8.  **`adaptPromptRouterPlan(payload)`**: Maps risk badges and routes planner rules.
9.  **`adaptModelRuntime(payload)`**: Aggregates LLM orchestration hosts.
10. **`adaptMetricStrip(payload)`**: Renders horizontal KPI strip figures.
11. **`adaptAgentCard(payload)`**: Normalizes active agent workloads.
12. **`adaptPipelineStage(payload)`**: Adapts Software Factory conveyer progress.
