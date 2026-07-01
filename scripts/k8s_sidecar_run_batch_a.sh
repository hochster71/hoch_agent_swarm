#!/usr/bin/env bash
# Trigger run-once Batch A inventory scans inside the sidecar cluster
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Triggering Batch A Inventory Scan Worker ==="

if ! docker info >/dev/null 2>&1; then
    echo "BLOCKER: Docker daemon is unavailable or not running on host. Cannot run Job."
    exit 0
fi

# Delete previous job if exists to allow rerun
kubectl delete job batch-a-inventory -n has-workers --ignore-not-found=true

# Apply job manifest
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/jobs/batch-a-inventory-job.yaml"

echo "Job 'batch-a-inventory' applied. Monitoring pod logs..."
sleep 2
POD_NAME=$(kubectl get pods -n has-workers -l job-name=batch-a-inventory -o jsonpath='{.items[0].metadata.name}' || true)
if [ -n "$POD_NAME" ]; then
    kubectl logs -n has-workers "$POD_NAME" -f || true
else
    echo "Waiting for pod to start..."
fi
