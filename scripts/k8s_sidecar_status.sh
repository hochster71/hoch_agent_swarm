#!/usr/bin/env bash
# HAS/HASF k3d sidecar status script
set -euo pipefail

echo "=== HAS/HASF Kubernetes Sidecar Status Report ==="

if ! docker info >/dev/null 2>&1; then
    echo "STATUS: Cluster Offline (Docker daemon not running)"
    echo "Verdict: CONDITIONAL GO (Docker Blocker)"
    exit 0
fi

if ! k3d cluster list has-sidecar-cluster >/dev/null 2>&1; then
    echo "STATUS: Cluster Offline (k3d cluster 'has-sidecar-cluster' does not exist)"
    exit 0
fi

echo "Kubernetes Context:"
kubectl config current-context

echo -e "\nNodes in Cluster:"
kubectl get nodes

echo -e "\nResource Quotas:"
kubectl get resourcequotas -n has-workers

echo -e "\nWorker Pods (has-workers Namespace):"
kubectl get pods -n has-workers -o wide

echo -e "\nJobs & CronJobs:"
kubectl get cronjobs -n has-workers
kubectl get jobs -n has-workers
