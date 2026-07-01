#!/usr/bin/env bash
# k8s_exposure_check.sh - Checks k3d/Kubernetes container public interface exposure
set -euo pipefail

export DOCKER_API_VERSION=1.41


# Pin Docker context to desktop-linux
if docker context ls | grep -F "desktop-linux" >/dev/null; then
  docker context use desktop-linux >/dev/null
fi

echo "==> Running Kubernetes/k3d Exposure Hygiene Check..."

# Check all running containers for non-loopback 6443 (k8s API) exposure
public_bind_found=false
k8s_active=false

# Get all running containers
running_containers=$(docker ps --format "{{.Names}}")

if [ -n "$running_containers" ]; then
  for container in $running_containers; do
    # Check if container name has k3d or if it is desktop-control-plane
    if echo "$container" | grep -Ei "k3d|k8s|control-plane|kind" >/dev/null; then
      k8s_active=true
    fi

    # Inspect port bindings for port 6443
    ports_json=$(docker inspect --format='{{json .NetworkSettings.Ports}}' "$container")
    
    # If container binds 6443/tcp
    if echo "$ports_json" | grep -F '"6443/tcp"' >/dev/null; then
      echo "Auditing k8s API container: $container..."
      # If HostIp contains 0.0.0.0, ::, or empty wildcard HostIp
      if echo "$ports_json" | grep -E '"HostIp":"(0\.0\.0\.0|::)"' >/dev/null || echo "$ports_json" | grep -F '"HostIp":""' >/dev/null; then
        echo "❌ ERROR: Public bind detected on $container! Ports details: $ports_json"
        public_bind_found=true
      fi
    fi
  done
fi

if [ "$public_bind_found" = "true" ]; then
  echo "Result: K8S_PUBLIC_BIND_BLOCKER"
  exit 1
fi

echo "Result: COMPOSE_BASELINE_PASS"
# If the running k3d container is active and has no public bind, it's loopback-only
# Wait, currently no running k3d containers are detected, but desktop-control-plane is active
k3d_active_running=$(docker ps --filter "label=app=k3d" --format "{{.Names}}")
if [ -n "$k3d_active_running" ]; then
  echo "Result: K8S_LANE_PROMOTED_BUT_SAFE (Loopback-only)"
else
  echo "Result: K8S_LANE_NOT_PROMOTED"
fi

exit 0
