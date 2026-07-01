# Operator Runbook — CLAWDE Control Tower Production Deployment

This runbook defines the operational procedures for deploying, monitoring, verifying, and rolling back the CLAWDE Control Tower and HOCH Agent Swarm.

## 1. Prerequisites & Staging Verification
1. Verify that the current branch and tags are pushed to the remote repository.
2. Run the staging dry-run checks in the cockpit dashboard. Ensure all checks are green:
   * Health endpoints respond.
   * Preflight score is valid.
   * Ledger integrity verification passes.
3. Verify that the handoff ZIP and ATO evidence package are intact.

## 2. Configuration & Secrets Mapping
1. Copy the environment configuration template `environment.env.template` to `environment.env`.
2. Configure all relevant cluster and security tokens inside `environment.env`.
3. Create the corresponding Kubernetes secrets:
   ```bash
   kubectl create secret generic swarm-secrets \
     --from-env-file=dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/environment.env
   ```

## 3. Production Deployment Execution
1. Apply the service and deployment manifests to the Kubernetes cluster:
   ```bash
   kubectl apply -f dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/deployment-service.yaml
   ```
2. Verify the rollout status:
   ```bash
   kubectl rollout status deployment/swarm-deployment --timeout=90s
   ```

## 4. Post-Deployment Verification
1. Run the healthcheck script to verify live container states:
   ```bash
   ./dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/healthcheck.sh <cluster-ip>
   ```
2. Ensure that both Uvicorn and Nginx/Caddy processes are running without errors.

## 5. Rollback Procedure
If any health check or readiness probe fails:
1. Trigger the rollback capsule script immediately:
   ```bash
   ./dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/rollback_capsule.sh
   ```
2. Inspect logs to troubleshoot the failure:
   ```bash
   kubectl logs deployment/swarm-deployment --all-containers --tail=100
   ```

---

### 🛡️ Compliance & Safety Disclaimer
*   **Authorization Status**: `ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW`
*   **Safety Notice**:
    *   The system has ATO-supporting evidence prepared for review.
    *   Actual ATO has not been granted.
    *   No authorization claim is being made.
