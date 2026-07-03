# PRODUCT 002 — CyberQRG-AI R2 Staging Build Authorization

This document establishes the R2 staging build boundary and governance policy for CyberQRG-AI.

---

## 1. Objectives & Target Users
* **Product Objective**: Provide an offline-first, local QR code scanner and security validator utility using local models.
* **Target Users**: Security compliance officers and developers running offline systems.
* **Problem Statement**: Standard scanner utilities rely on external APIs, creating data leakage and privacy vulnerabilities.

---

## 2. Allowed R2 Tasks (Staging Boundary)
* `task-002-r2-001`: Generate architecture blueprint.
* `task-002-r2-002`: Repo scaffold proposal.
* `task-002-r2-003`: Local prototype plan.
* `task-002-r2-004`: Offline-first UI wireframe layout.

---

## 3. Blocked Tasks (Forbidden Actions)
* Production releases or Vercel production promotions.
* Stripe/payment integration.
* Public DNS or domain changes.
* Customer data handling.

---

## 4. Run Parameters & Promotion Gates
* **Allowed Adapters**: `ollama_gpu_pod`, `lmstudio`.
* **Blocked Adapters**: `ollama_native` (Blocked from Tier 3 tasks).
* **Promotion Gates**:
  - `verify_product_002_r2_authorization.py`
  - `verify_gpu_budget_guard.py`
  - `verify_tier3_routing_policy.py`
