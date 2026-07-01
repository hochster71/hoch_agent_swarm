# HOCH Visual Control Plane Feature-Flagged Local Activation

This document defines the optional, local-only activation policy and rollback steps.

---

## 1. Operator Approval Sign-Off Record

*   **Review Decision**: `APPROVE_WITH_CHANGES`
*   **Operator**: Michael Hoch
*   **Approval Date**: 2026-06-27
*   **Requested Changes for Future Live Deployment**:
    *   Tighter card spacing and margin optimizations.
    *   Clearer source/freshness metadata labels.
    *   Stronger visual hierarchy and distinct colors for `FAIL-CLOSED` cards.
    *   Clearer separation between preview-only and operational cockpit controls.
    *   Tablet/iPad readability check.

---

## 2. Feature-Flag Activation Strategy

The cockpit replacement remains disabled by default under local safety parameters:
*   `active_cockpit_replacement_enabled`: `false` (forces fallback to baseline `control-plane.html`)
*   `visual_preview_route_enabled`: `true` (enables sandbox preview `dashboard-preview.html`)
*   `local_only`: `true`

---

## 3. Rollback Procedure

To roll back instantly to the baseline cockpit environment:
1.  Verify the original `control-plane.html` remains unmodified.
2.  Set `active_cockpit_replacement_enabled` to `false` in `config/visual_runtime_flags.json`.
3.  Revert any optional preview navigation routes in the UI context.
4.  Rerun `qa:ui-contract` and `ci:validate` to ensure zero regression.
