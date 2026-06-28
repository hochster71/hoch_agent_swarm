# Visual Control Plane Local Replacement Dry Run

This document records the design, backup verification, staging candidate paths, and rollback steps for Phase V12.

---

## 1. Safety Posture: DRY-RUN ONLY

All replacement operations are fully simulated. The baseline active cockpit `control-plane.html` remains untouched.
*   `dry_run_only`: `true`
*   `active_cockpit_replacement_enabled`: `false`

---

## 2. Backup & Staging Locations

*   **Backup Root**: [`artifacts/qa/visual_review/dry_run_backups/`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/dry_run_backups/)
*   **Candidate Path**: [`artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html)

---

## 3. Rollback Instructions

In the event of a simulated dry-run deployment, the rollback file `ROLLBACK.md` defines the recovery step:
```bash
# To rollback from dry-run candidate:
cp artifacts/qa/visual_review/dry_run_backups/control-plane.html.backup.<timestamp> mockups/visual-control-plane/control-plane.html
```
Checklist status: `DRY_RUN_COMPLETE`.
Next decision required: `V13_OPERATOR_DRY_RUN_REVIEW`.
