# HOCH Visual Control Plane Local Cockpit Alias Activation

This document defines the local cockpit alias configuration, verification strategy, and rollback details for Phase V10.

---

## 1. Verification Decision Recorded

*   **Decision**: `FINAL_APPROVE_LOCAL_ACTIVATION`
*   **Operator**: Michael Hoch
*   **Approval Date**: 2026-06-27
*   **Approval Status**: Approved for local optional alias route serving.

---

## 2. Invariants & Configuration

The local alias cockpit is mapped under:
*   **Alias Route**: [`mockups/visual-control-plane/local-cockpit-alias.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/mockups/visual-control-plane/local-cockpit-alias.html)

### Flag Safety Posture
All backend modifications and prompt triggers remain fully blocked:
*   `active_cockpit_replacement_enabled`: `false` (baseline cockpit remains live)
*   `visual_preview_route_enabled`: `true`
*   `visual_cockpit_alias_enabled`: `true`
*   `backend_mutation_enabled`: `false`
*   `prompt_execution_enabled`: `false`
*   `approval_decision_execution_enabled`: `false`

---

## 3. Rollback Procedure

To disable the optional local alias immediately:
1.  Verify the baseline `control-plane.html` remains active.
2.  Set `visual_cockpit_alias_enabled` to `false` in `config/visual_runtime_flags.json`.
3.  Delete or rename the optional alias route `local-cockpit-alias.html`.
4.  Rerun `qa:ui-contract` and `ci:validate` to ensure zero regression.
