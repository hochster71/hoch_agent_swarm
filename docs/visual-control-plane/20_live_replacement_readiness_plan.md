# Visual Control Plane Live Replacement Readiness Plan

This document outlines the readiness criteria, gates, and error budget policy required before the Visual Control Plane is allowed to replace the baseline cockpit page locally.

---

## 1. Safety Status: FULL REPLACEMENT IS STILL BLOCKED

Replacement remains inactive:
*   `active_cockpit_replacement_enabled`: `false`
*   `replacement_ready`: `false`

---

## 2. Readiness Gates

The following 15 gates must be verified before local replacement activation:

1.  **Operator Final Approval Gate**: Direct signed consent recorded from Michael Hoch.
2.  **Baseline Cockpit Backup Gate**: A local backup of `control-plane.html` created at `/tmp/control-plane.html.backup`.
3.  **Rollback Verified Gate**: Step-by-step verification of restoration commands.
4.  **Visual Parity Gate**: Comparative confirmation of dark-theme layout, labels, and rendering fidelity.
5.  **Telemetry Truth Gate**: Verification that rendering maps strictly to verified datastore states.
6.  **State Fallback Gate**: Unresolved or missing endpoints default to `UNAVAILABLE` or `FAIL-CLOSED`.
7.  **Accessibility Gate**: Contrast checks, keyboard navigability, and focus validation.
8.  **Tablet/iPad Readability Gate**: Verification of column layouts on viewports down to 768px.
9.  **Error Budget Gate**: Fulfillment of zero-tolerance constraints.
10. **Security No-Regression Gate**: Strict assurance of zero backend mutating calls or execution APIs.
11. **Local-Only Scope Gate**: Verification that preview rendering occurs entirely client-side.
12. **Backend Mutation Blocked Gate**: Verification that no mutating HTTP commands are sent.
13. **Prompt Execution Blocked Gate**: Verification that prompt execution engines are isolated.
14. **Approval Decision Execution Blocked Gate**: Actions in the preview cockpit remain disabled mocks.
15. **CI/QA Full Pass Gate**: Complete verification of `npm run ci:validate` clean runs.

---

## 3. Error Budget Criteria

We enforce a zero-tolerance policy for UI safety and operational regressions:
*   **0** broken dashboard routes
*   **0** unsupported state labels
*   **0** fake LIVE states
*   **0** backend mutation paths
*   **0** prompt execution paths
*   **0** approval decision execution paths
*   **0** missing rollback steps
*   **0** high/critical unresolved UI safety findings
