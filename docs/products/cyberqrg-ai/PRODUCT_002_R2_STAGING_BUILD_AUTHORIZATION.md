# PRODUCT 002 — CyberQRG-AI R2 Staging Build Authorization

This document establishes the R2 staging build boundary and governance policy for CyberQRG-AI.

---

## 1. Objectives & Target Users
* **Product Objective**: Provide an offline-first, local QR code scanner and security validator utility using local models.
* **Target Users**: Security compliance officers and developers running offline systems.
* **Problem Statement**: Standard scanner utilities rely on external APIs, creating data leakage and privacy vulnerabilities.

---

## 2. Allowed R2 Tasks (Atomic Staging Boundary)
1. **R2-001**: CyberQRG-AI architecture blueprint.
2. **R2-002**: Product requirements and user flows spec.
3. **R2-003**: Security/control mapping document.
4. **R2-004**: Local prototype scaffold layout.
5. **R2-005**: UI wireframe package.
6. **R2-006**: Data model proposal.
7. **R2-007**: Staging deployment plan.
8. **R2-008**: QA/eval plan.
9. **R2-009**: Evidence collection plan.
10. **R2-010**: Founder review checkpoint.

---

## 3. Blocked Tasks (Forbidden Actions)
* Production releases or Vercel production promotions.
* Stripe/payment integration.
* Public DNS or domain changes.
* Customer data handling.

---

## 4. Rollback & Stopping Criteria
* **Reversal**: All tasks are document-only proposals; rollback is achieved by deleting target files.
* **Stopping Condition**: If G-EVAL mean score drops below 4.0 or GPU budget exceeds $5.0/day, execution automatically halts.
