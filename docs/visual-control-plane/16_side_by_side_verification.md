# HOCH Visual Control Plane Side-by-Side Verification

This document details the live side-by-side comparison page.

---

## 1. Scope & Verification Strategy

We have established a dedicated local verification page:
*   **Verification Page**: [`mockups/visual-control-plane/side-by-side-review.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/mockups/visual-control-plane/side-by-side-review.html)

This interface renders the current baseline cockpit side-by-side with the new layout preview, allowing operators to verify visual consistency and fallback states directly:
*   **Left Panel**: Current baseline cockpit ([`control-plane.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/mockups/visual-control-plane/control-plane.html)).
*   **Right Panel**: Sandbox preview ([`dashboard-preview.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/mockups/visual-control-plane/dashboard-preview.html)) driven by pure adapters.

---

## 2. Invariants & Security

1.  **Warning Banner**: Explicitly displays `REVIEW ONLY — NO LIVE REPLACEMENT` to prevent operational ambiguity.
2.  **No Mutation**: Review buttons trigger alerts instead of calling live endpoints. No `POST`, `PUT`, `PATCH`, `DELETE`, `WebSocket`, or `EventSource` connections are initialized.
3.  **Checklist Status**: Registered under [`artifacts/qa/visual_review/side_by_side_review_checklist.json`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/side_by_side_review_checklist.json) in `PENDING_OPERATOR_REVIEW` state.
