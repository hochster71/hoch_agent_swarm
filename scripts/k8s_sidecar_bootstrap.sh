#!/usr/bin/env bash
# HAS/HASF k3d sidecar bootstrap script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
# Check if docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo "BLOCKER: Docker daemon is unavailable or not running on host."
    echo "All Kubernetes manifests and sidecar scripts have been prepared successfully."
    echo "To run the sidecar cluster, start Docker Desktop and rerun this script."
    echo "Verdict: CONDITIONAL GO (Docker Blocker)"
    echo "=================================================="
    exit 0
fi

echo "Docker daemon detected. Starting k3d cluster bootstrap..."

# 1. Create k3d cluster
if k3d cluster list has-sidecar-cluster >/dev/null 2>&1; then
    echo "k3d cluster 'has-sidecar-cluster' already exists. Reusing..."
else
    echo "Creating k3d cluster 'has-sidecar-cluster'..."
    k3d cluster create --config "$PROJECT_ROOT/runtime/k8s/k3d-cluster.yaml"
fi

# 2. Build and import sidecar worker image
echo "Building has-worker Docker image..."
docker build -t has-worker:latest -f "$PROJECT_ROOT/Dockerfile.worker" "$PROJECT_ROOT"

echo "Importing has-worker image into k3d..."
k3d image import has-worker:latest -c has-sidecar-cluster

# 3. Create namespace
echo "Applying Kubernetes namespace and quotas..."
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/namespace.yaml"
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/resource-quotas.yaml"
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/rbac.yaml"

# 4. Create secrets dynamically from host env
SECRETS_FILE="$HOME/.hoch-secrets/has-tracker.env"
if [ -f "$SECRETS_FILE" ]; then
    echo "Creating has-tracker-secrets from $SECRETS_FILE..."
    kubectl delete secret has-tracker-secrets -n has-workers --ignore-not-found=true
    kubectl create secret generic has-tracker-secrets --from-env-file="$SECRETS_FILE" -n has-workers
else
    echo "Warning: Secrets file not found at $SECRETS_FILE. Creating placeholder secret..."
    kubectl delete secret has-tracker-secrets -n has-workers --ignore-not-found=true
    kubectl create secret generic has-tracker-secrets \
      --from-literal=TRACKER_USER=admin \
      --from-literal=TRACKER_PASSWORD=change-this-password \
      -n has-workers
fi

# 5. Apply configmap and PVC
echo "Applying configmaps and volumes..."
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/configmap.yaml"
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/pvc.yaml"

# 6. Apply deployments and cronjobs
echo "Applying deployment and cronjobs workloads..."
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/deployments/"
kubectl apply -f "$PROJECT_ROOT/runtime/k8s/cronjobs/"

echo "=================================================="
echo "[SUCCESS] HAS/HASF Kubernetes sidecar runtime bootstrapped successfully."
echo "Use './scripts/k8s_sidecar_status.sh' to inspect workloads."
echo "=================================================="
