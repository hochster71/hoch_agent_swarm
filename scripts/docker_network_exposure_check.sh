#!/usr/bin/env bash
# docker_network_exposure_check.sh - Enforces loopback-only local runtime exposure policies

set -euo pipefail

# Verify and pin Docker context based on responsiveness
if docker --context default ps >/dev/null 2>&1; then
  docker context use default >/dev/null
elif docker --context desktop-linux ps >/dev/null 2>&1; then
  docker context use desktop-linux >/dev/null
else
  docker context use default >/dev/null || true
fi

echo "==> Running Docker Network Exposure Compliance Check..."

# Check docker compose ps output
compose_ps=$(docker compose ps)
echo "Current Compose PS state:"
echo "$compose_ps"

# 1. Reject public interface bindings (0.0.0.0) or IPv6 wildcard (::: or [::])
if echo "$compose_ps" | grep -E "0\.0\.0\.0|:::" >/dev/null; then
  echo "❌ FAIL: docker compose ps shows public interface exposure (0.0.0.0 or :::)!"
  exit 1
fi

# 2. Inspect containers using docker inspect for absolute validation of HostIp
for container in has-api has-ui; do
  echo "Inspecting host port bindings for $container..."
  host_ips=$(docker inspect --format='{{range $p, $conf := .NetworkSettings.Ports}}{{range $conf}}{{.HostIp}} {{end}}{{end}}' "$container")
  
  if [ -z "$host_ips" ]; then
    echo "❌ FAIL: Container $container has no published ports found!"
    exit 1
  fi
  
  for ip in $host_ips; do
    if [ "$ip" != "127.0.0.1" ]; then
      echo "❌ FAIL: Container $container has forbidden port binding to IP: '$ip' (must be strictly 127.0.0.1)!"
      exit 1
    fi
  done
done

# 3. Verify canonical ports and URLs are reachable locally
echo "Verifying local loopback reachability..."
if ! curl -sSf http://127.0.0.1:8000/api/v1/runtime-truth/state > /dev/null; then
  echo "❌ FAIL: Canonical API endpoint http://127.0.0.1:8000/api/v1/runtime-truth/state is unreachable!"
  exit 1
fi

if ! curl -sSf http://127.0.0.1:8080/ > /dev/null; then
  echo "❌ FAIL: Canonical UI endpoint http://127.0.0.1:8080/ is unreachable!"
  exit 1
fi

echo "[PASS] Docker network exposure checks passed. Loopback-only bound and verified."
exit 0
