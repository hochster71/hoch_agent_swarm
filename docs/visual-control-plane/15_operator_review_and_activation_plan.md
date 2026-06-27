# HOCH Visual Control Plane Operator Review and Activation Plan

This document establishes the review criteria, rollback steps, and feature-flag activation strategy for the Visual Control Plane.

---

## 1. Explicit Michael Hoch Approval Gate

The new visual dashboard preview is strictly sandboxed. Full activation and cockpit replacement (`control-plane.html`) require manual verification and sign-off by **Michael Hoch**. No automated script or agent may toggle activation settings.

---

## 2. Blocked Actions

The following actions are strictly prohibited in this phase:
1.  **Production Deployment**: No remote or container cluster deployments.
2.  **External Publication**: Local-only activation scope.
3.  **Backend Mutation**: No POST, PUT, PATCH, or DELETE operations.
4.  **Prompt Execution**: Swarm prompt triggers remain fully blocked.
5.  **Approval Decision Execution**: Gate decisions remain simulation-only.
6.  **Security Posture Change**: System hardening defaults must not be altered.

---

## 3. Operator Review Checklist
*   [ ] Preview page loads locally.
*   [ ] Dark theme typography is consistent.
*   [ ] No false `LIVE` state is displayed when source data is missing.
*   [ ] All 8 fallback states are rendered correctly.
*   [ ] Stale telemetry payloads transition to `STALE` status.
*   [ ] Missing API endpoints render as `UNAVAILABLE`.
*   [ ] Security policy violations correctly resolve to `FAIL-CLOSED`.
*   [ ] Approval buttons are visual-only (disabled).
*   [ ] Zero backend state mutation occurs.
*   [ ] No WebSocket or EventSource connections are established.
*   [ ] Active production cockpit file (`control-plane.html`) remains completely unchanged.
*   [ ] Rollback path is documented and verified.

---

## 4. Rollback Procedure

If any visual anomaly, data-binding issue, or safety regression is detected:
1.  **Preserve active cockpit**: Maintain the current active `control-plane.html` page without edits.
2.  **Isolate preview**: Do not link `dashboard-preview.html` to any production routing index.
3.  **Disable feature flag**: Ensure `active_cockpit_replacement_enabled` remains `false` in `config/visual_activation_plan.json`.
4.  **Restore prior assets**: Revert any changes to `frontend/app.js` using git checkout if necessary.
5.  **Rerun QA suites**: Run `npm run qa:ui-contract` to verify prior test validations remain fully green.
6.  **Rerun CI validation**: Execute `npm run ci:validate` to ensure clean builds.
7.  **Confirm REST endpoints**: Run `curl -s http://127.0.0.1:8000/api/v1/live-runtime/cockpit` to confirm backend API compatibility.

---

## 5. Go / Conditional Go / No-Go Decision Table

| Condition | Release Decision | Action |
| :--- | :--- | :--- |
| All review checklist items pass and signed off | **GO** | Authorized for staged cockpit activation planning |
| Minor styling issue observed but safety invariants intact | **CONDITIONAL_GO** | Authorized for local testing; activation blocked until resolved |
| Any safety invariant, evidence check, or rollback step fails | **NO_GO** | Immediately disable flags, trigger rollback, and isolate preview |
