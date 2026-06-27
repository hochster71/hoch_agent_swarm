# Visual Control Plane Operator Dry Run Review

This document presents the staged candidate cockpit and rollback instructions to Michael Hoch for verification and approval.

---

## 1. Safety Status: FULL REPLACEMENT IS STILL BLOCKED

Replacement remains inactive:
*   `active_cockpit_replacement_enabled`: `false`
*   `replacement_performed`: `false`

---

## 2. Review Links

*   **Candidate Cockpit**: [`artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html)
*   **Rollback Evidence**: [`artifacts/qa/visual_review/dry_run_candidate/ROLLBACK.md`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/dry_run_candidate/ROLLBACK.md)

---

## 3. Operator Verification Tasks

1.  Inspect [control-plane.candidate.html](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html) visual style and layouts.
2.  Assert [ROLLBACK.md](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/qa/visual_review/dry_run_candidate/ROLLBACK.md) lists correct recovery paths.
3.  Check that the original baseline `control-plane.html` remains accessible.

---

## 4. Decision Required

Choose one decision in the review report:
*   `APPROVE_DRY_RUN_FOR_LOCAL_REPLACEMENT`
*   `APPROVE_WITH_MORE_CHANGES`
*   `REJECT_REPLACEMENT`
