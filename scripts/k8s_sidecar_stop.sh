#!/usr/bin/env bash
# Pause/stop the k3d sidecar cluster to conserve resource usage
set -euo pipefail

echo "=== Stopping HAS/HASF Kubernetes Sidecar Cluster ==="

if ! docker info >/dev/null 2>&1; then
    echo "BLOCKER: Docker daemon is unavailable or not running on host."
    exit 0
fi

if k3d cluster list has-sidecar-cluster >/dev/null 2>&1; then
    echo "Stopping k3d cluster 'has-sidecar-cluster'..."
    k3d cluster stop has-sidecar-cluster
    echo "[SUCCESS] Cluster stopped successfully."
else
    echo "No running k3d cluster found."
fi
