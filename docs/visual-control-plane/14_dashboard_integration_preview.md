# HOCH Visual Control Plane Dashboard Integration Preview

This document details the design and deployment of the Visual Control Plane dashboard preview page.

---

## 1. Preview Strategy & Scope

To ensure the safety of active operations, **Phase V5 — Controlled Dashboard Integration Preview** is strictly bounded to a separate preview-only page:
*   **Preview Page**: [`mockups/visual-control-plane/dashboard-preview.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/mockups/visual-control-plane/dashboard-preview.html)
*   **Renderer**: [`frontend/visual_dashboard_preview.js`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/frontend/visual_dashboard_preview.js)

### Explicit Constraints
1.  Does not replace the active cockpit dashboard files (`control-plane.html`, etc.).
2.  Does not write to or mutate any backend database or file.
3.  Does not execute prompt chains or LLM calls.
4.  All button elements are marked "VISUAL ONLY" and disabled.
5.  WebSockets and EventSource connections are blocked.
6.  Operates using read-only declarative local test fixtures.

---

## 2. Renders Mocking All 8 States

The preview page verifies that `visual_adapters.js` handles data boundaries cleanly, rendering a dedicated card layout demonstrating:
*   `LIVE`: Active status with verified evidence.
*   `DEGRADED`: High latency or partial validation failures.
*   `PENDING`: Awaiting human review or release triggers.
*   `SIMULATED`: Non-production design mock elements.
*   `STALE`: Old or cached telemetry older than the freshness window.
*   `FAIL-CLOSED`: Active policy blocks and security bypass attempts.
*   `UNAVAILABLE`: Inaccessible backend or missing API payloads.
*   `UNKNOWN`: Unrecognized data formatting or mapping exceptions.
