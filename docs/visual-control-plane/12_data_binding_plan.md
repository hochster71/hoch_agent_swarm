# HOCH Visual Control Plane Data Binding Plan

This document specifies the data-binding plan mapping our 14 reusable visual components to backend resources, API endpoints, and local artifact files.

---

## 1. Required Binding Sources Reference

This plan utilizes the following 10 data sources to feed state truth to the UI components:
1.  **`/api/v1/live-runtime/cockpit`** (REST): Central runtime health telemetry aggregation.
2.  **`/api/v1/prompts/registry`** (REST): Active prompt registry list.
3.  **`/api/v1/prompts/categories`** (REST): Registry category list.
4.  **`/api/v1/prompts/router/rules`** (REST): Active router chains configuration rules.
5.  **`/api/v1/prompts/router/plan`** (REST): Task routing plan planner endpoint.
6.  **`artifacts/qa/known_assets/known_asset_probe_report.json`** (Artifact): Network probe outputs.
7.  **`artifacts/qa/prompt_registry/prompt_registry_report.json`** (Artifact): Prompt registry statistics report.
8.  **`artifacts/pentest/evidence_manifest.json`** (Artifact): Security scan evidence outputs.
9.  **`config/prompt_control_plane.json`** (Static): Primary prompt control plane configurations.
10. **`config/visual_control_plane.json`** (Static): Global visual config routes.

---

## 2. General Data Binding Rules

To enforce Nielsen heuristics around state-truth and prevent false status representation, the following mapping rules are strictly applied:
*   **No Live Claims from Missing Data**: If the source path is missing or inaccessible, the component status MUST resolve to `UNAVAILABLE` (never default to `LIVE`).
*   **Stale Data Mapping**: If a REST endpoint or artifact timestamp is older than `freshness_seconds`, the status transitions to `STALE`.
*   **Security Ambiguity**: Any unresolved validation mismatch, missing operator signature, or bypass attempt maps to `FAIL-CLOSED`.
*   **Static Mocking**: Any static placeholder or design mockup defaults to `SIMULATED`.
*   **Partial Evidence**: If some controls pass but others are pending verification, status maps to `DEGRADED`.
*   **Human Approval**: Any material action (deletion, deployment, publishing, app-store) requires explicit human approval before being executed.

---

## 3. Communication Strategy

1.  **REST Polling**: Main telemetry cards use HTTP GET requests with custom intervals (5s to 30s) to poll endpoints such as `/api/v1/live-runtime/cockpit`.
2.  **Server-Sent Events (SSE)**: Recommended for streaming one-way live telemetry events from the runtime event bus directly to the console terminal window.
3.  **WebSockets**: Reserved strictly for future bidirectional operator actions (running tasks, manual override commands).
4.  **No Live Controls**: Real-time control execution remains disabled in this phase.

---

## 4. Component-by-Component Mapping Spec

| Component Name | Source Type | Source Path | Refresh Strategy | Fallback State | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ops-header** | REST | `/api/v1/live-runtime/cockpit` | Polling (10s) | `UNKNOWN` | System title and operating status |
| **status-pill** | REST | `/api/v1/live-runtime/cockpit` | Polling (5s) | `UNKNOWN` | Renders the normalized state badges |
| **telemetry-card** | REST | `/api/v1/live-runtime/cockpit` | Polling (10s) | `UNAVAILABLE` | Cockpit metrics cards |
| **agent-card** | FUTURE | `/api/v1/agents/status` | Polling (15s) | `SIMULATED` | Agent duty details |
| **approval-card** | FUTURE | `/api/v1/approvals/queue` | Polling (5s) | `PENDING` | Displays Michael Hoch approval gates |
| **evidence-card** | ARTIFACT | `artifacts/pentest/evidence_manifest.json` | Manual | `UNAVAILABLE` | Attestations & SBOM checksum verification |
| **pipeline-stage** | FUTURE | `artifacts/qa/factory/pipeline_status.json` | Polling (30s) | `PENDING` | Software Factory conveyor stages |
| **node-map-card** | ARTIFACT | `artifacts/qa/known_assets/known_asset_probe_report.json` | Polling (30s) | `UNAVAILABLE` | Cluster topography node mapping |
| **prompt-card** | REST | `/api/v1/prompts/registry` | Polling (60s) | `UNAVAILABLE` | Prompt registry preview |
| **risk-badge** | REST | `/api/v1/prompts/router/plan` | Polling (10s) | `UNKNOWN` | Plan risk levels |
| **state-registry** | STATIC | `config/visual_control_plane.json` | Static | `UNKNOWN` | Permitted system state pills registry |
| **terminal-panel** | ARTIFACT | `artifacts/qa/prompt_registry/prompt_registry_report.json` | Polling (10s) | `UNAVAILABLE` | Execution log output console terminal |
| **metric-strip** | REST | `/api/v1/live-runtime/cockpit` | Polling (10s) | `UNAVAILABLE` | Dynamic counter values ribbon |
| **section-rail** | STATIC | `config/visual_control_plane.json` | Static | `UNKNOWN` | Vertical sidebar navigation rails |
