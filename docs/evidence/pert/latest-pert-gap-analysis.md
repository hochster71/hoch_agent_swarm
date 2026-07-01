# PERT Gap Analysis: Hoch Agent Swarm E2E Build

## 1. Executive Summary
This document identifies all P0, P1, and P2 gaps preventing full E2E build validation and automated dependency path visualization in the Hoch Agent Swarm. By resolving these gaps, we transition the Swarm to a validated **GO** state under the cost and security constraints.

---

## 2. Gap Classification & Risks

| Category | Gap Description | Priority | Mitigation / Plan |
| :--- | :--- | :--- | :--- |
| **PERT UI Panel** | The Cockpit UI lacks a dedicated tab for displaying the PERT network graph and critical path. | **P0** | Implement `#view-pert-e2e-build` container in `index.html` with rendering hooks in `app.js`. |
| **Build Validation Script** | No automated orchestrator script exists to test gates and verify local-first configs in order. | **P0** | Develop `scripts/pert_e2e_build.sh` enforcing strict PASS criteria for all 8 gates. |
| **E2E Integration Spec** | Playwright test coverage is missing for the PERT tab panels. | **P0** | Create `tests/e2e/pert-e2e-build.spec.ts` asserting graph, tables, and decisions. |
| **Heartbeat Logging** | Heartbeat checks run silently without writing timestamped run logs for ATO evidence. | **P1** | Set up periodic uvicorn API logs for runtime checkpoints. |
| **Browser Limit enforcement**| Playwright automation runs natively without container resource bounds. | **P1** | Add browser limit controls to container compose profiles. |

---

## 3. Integration Risks & Cost Guardrails
- **GPU Expense Mitigations**: Zero always-on GPU instances. VPS handles lightweight control plane routing, keeping monthly costs under **$100**.
- **Execution Limits**: Max active agents cap of **20** prevents thread starvation or browser memory leaks on budget VPS systems.
