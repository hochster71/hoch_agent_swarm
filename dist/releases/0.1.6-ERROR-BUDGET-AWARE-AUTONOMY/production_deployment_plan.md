# Production Deployment Planning and Target Selection (DEPLOY1)

This document establishes the official deployment planning baseline for the CLAWDE Control Tower and HOCH Agent Swarm runtime systems.

## 1. Selected Production Runtime Target
*   **Hosting Target**: Private secure Kubernetes cluster (`deployment/swarm-deployment`).
*   **Process Architecture**:
    *   **Backend Node**: Uvicorn running FastAPI server (Python 3.14).
    *   **Frontend Node**: Compiled static Single-Page Application (SPA) served via Nginx/Caddy.
    *   **Database Node**: Persistent Volume Claim (PVC) holding the local SQLite `swarm_ledger.db`.

## 2. Network Exposure & Protective Boundary
*   **Exposure Scope**: Internal-only intranet routing, terminated by TLS Ingress Controller.
*   **Access Port**: Port 443 (HTTPS) with certificate mapping.
*   **Isolation Bounds**: Local API endpoints (like `/api/v1/hochster/*`) are kept strictly isolated from external networks to prevent data/state leakage.

## 3. Secrets Management Strategy
*   **Key Storage**: Vault integration or Kubernetes Secrets injected as environment variables.
*   **Variables Configured**:
    *   `OPENAI_API_KEY`: Kept in secure secret store.
    *   `OLLAMA_API_BASE`: Injected cluster-internal service endpoint URL.
*   **Verification Gate**: No plaintext keys in repository or manifests.

## 4. Process Manager & Supervisor
*   **Supervisor Daemon**: Kubernetes Kubelet manager handles automated container health lifecycle, restarting nodes on crash event detection.

## 5. Rollback Strategy & Migration Handling
*   **Rollback Procedure**:
    ```bash
    kubectl rollout undo deployment/swarm-deployment
    ```
*   **Schema Safety**: SQLite database schemas use backward-compatible migrations only; no column dropping or table renames without dual-version support.

## 6. Health Probe Configuration
*   **Liveness Probe**:
    *   Endpoint: `GET /api/v1/hochster/health`
    *   Interval: 30s
    *   Timeout: 5s
*   **Readiness Probe**:
    *   Endpoint: `GET /api/v1/readiness/status`
    *   Criteria: Score >= 80%

## 7. Backup & Recovery Posture
*   **Snapshot Frequency**: Daily automated backups of `swarm_ledger.db`.
*   **Retention Period**: 30-day retention lock on backup objects.
*   **Storage Target**: Encrypted offsite Google Cloud Storage / Amazon S3 bucket.

## 8. Deployment Acceptance Gates
1.  **CI Validation**: 100% of automated QA contract tests must pass.
2.  **Signature Seal**: Binary validation checks pass.
3.  **Ledger Integrity**: Cryptographic verification of action ledger passes.
4.  **Operator Approval**: Explicit manual approval registered in the decisions queue.

---

### 🛡️ Compliance & Safety Boundary Notice
*   **Authorization Status**: `ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW`
*   **Safety Notice**:
    *   The system has ATO-supporting evidence prepared for review.
    *   Actual ATO has not been granted.
    *   No authorization claim is being made.
