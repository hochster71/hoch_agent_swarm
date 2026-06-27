# Visual Control Plane Controlled Local Substitution

This document records the design, active backup validation, staged substitution results, and rollback paths for Phase V15.

---

## 1. Safety Status: LOCAL CONTROLLED SUBSTITUTION

Replacement is active in a local-only sandboxed scope:
*   `controlled_substitution_allowed`: `true`
*   `active_cockpit_replacement_enabled`: `true` (restricted to V15 controlled local substitution scope)
*   `substitution_performed`: `true` (updated after execution)

---

## 2. Backup & Staging Paths

*   **Active Backup Root**: [`artifacts/qa/visual_review/active_substitution_backups/`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/active_substitution_backups/)
*   **Active Rollback Path**: [`artifacts/qa/visual_review/active_substitution/ROLLBACK.md`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/active_substitution/ROLLBACK.md)

---

## 3. Rollback Instructions

To roll back immediately to the baseline cockpit configuration:
```bash
# Execute recovery from ROLLBACK.md:
cp artifacts/qa/visual_review/active_substitution_backups/control-plane.html.backup.<timestamp> mockups/visual-control-plane/control-plane.html
```
Checklist status: `CONTROLLED_LOCAL_SUBSTITUTION_COMPLETE`.
Next decision required: `V16_LOCAL_SUBSTITUTION_VALIDATION_AND_ROLLBACK_PROOF`.
