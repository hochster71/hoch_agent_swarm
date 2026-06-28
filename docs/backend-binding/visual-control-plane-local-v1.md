# Visual Control Plane Backend Runtime Binding Readiness

This document outlines the data contracts, mappings, and safety bounds to bind the visual preview cockpit to the backend.

---

## 1. Mapped Endpoints

### `/api/v1/runtime/process/animation-state`
*   **Method**: `GET`
*   **Description**: Returns local runtime processes and their UI animation tokens (`koi` sprite actions, color schemas, and movement types).
*   **Mutations**: None (Read-only query of `RuntimeProcessBus`).

### `/api/v1/runtime/process/health`
*   **Method**: `GET`
*   **Description**: Exposes current health metrics of local processes.
*   **Mutations**: None (Read-only summary).

---

## 2. Safety Posture

To ensure strict compliance with preview-only boundaries, the following mutation endpoints are completely blocked and disconnected from the cockpit interface:
*   `POST /api/v1/prompt/execute`
*   `POST /api/v1/approval/decision`
*   `POST /api/v1/remediation/execute`

---

## 3. QA Readiness Validation

The readiness parameters are verified through static schema contract validations to guarantee that:
1.  All data properties returned from backend endpoints match the visual adapter properties precisely.
2.  No mutating routes are exposed or linked from the frontend.
