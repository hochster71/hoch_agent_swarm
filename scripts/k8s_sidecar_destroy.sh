#!/usr/bin/env bash
# Tear down and delete k3d sidecar cluster completely
set -euo pipefail

echo "=== Destroying HAS/HASF Kubernetes Sidecar Cluster ==="

if ! docker info >/dev/null 2>&1; then
    echo "BLOCKER: Docker daemon is unavailable or not running on host."
    exit 0
fi

if k3d cluster list has-sidecar-cluster >/dev/null 2>&1; then
    echo "Deleting k3d cluster 'has-sidecar-cluster'..."
    k3d cluster delete has-sidecar-cluster
    echo "[SUCCESS] Cluster deleted successfully."
else
    echo "No k3d cluster found to delete."
fi
