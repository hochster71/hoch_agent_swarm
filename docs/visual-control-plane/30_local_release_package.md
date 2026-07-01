# Visual Control Plane Local Release Package

This document records the packaging metadata and verification boundaries for the local visual cockpit release package.

---

## 1. Safety Boundaries: NOT DEPLOYED

*   `package_created`: `true`
*   `deployment_performed`: `false`
*   `production_deployment_enabled`: `false`
*   `external_publication_enabled`: `false`
*   `backend_mutation_enabled`: `false`
*   `prompt_execution_enabled`: `false`
*   `approval_decision_execution_enabled`: `false`
*   `security_posture_change_enabled`: `false`

---

## 2. Release Coordinates

*   **Release Root**: [`artifacts/releases/visual-control-plane-local`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local)
*   **Manifest Path**: [`artifacts/releases/visual-control-plane-local/manifest.json`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local/manifest.json)
*   **Provenance Path**: [`artifacts/releases/visual-control-plane-local/provenance.json`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local/provenance.json)
*   **Rollback Path**: [`artifacts/releases/visual-control-plane-local/ROLLBACK.md`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local/ROLLBACK.md)

---

## 3. Included Evidence Files

1.  [`local_operator_acceptance.json`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local/evidence/local_operator_acceptance.json)
2.  [`local_visual_cockpit_stabilization_report.json`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local/evidence/local_visual_cockpit_stabilization_report.json)
3.  [`reapply_local_visual_cockpit_report.json`](file:///Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/artifacts/releases/visual-control-plane-local/evidence/reapply_local_visual_cockpit_report.json)

---

## 4. Next Phase

*   **Next Allowed Phase**: `V22_LOCAL_RELEASE_REVIEW`
