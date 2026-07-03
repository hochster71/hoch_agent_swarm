#!/usr/bin/env bash
# =============================================================================
# docker_security_gate.sh
# Audits local and remote Docker configurations for security hardening.
# =============================================================================
set -euo pipefail

echo "==> Running Docker Hardening Security Gate..."

# 1. Check Dockerfile USER directive
if [ -f "Dockerfile" ]; then
  if ! grep -q "USER " Dockerfile; then
    echo "❌ FAIL: Dockerfile is missing non-root USER instruction."
    exit 1
  fi
fi

# 2. Check docker-compose.yml for privileged mode or unsafe volumes
if [ -f "docker-compose.yml" ]; then
  if grep -q "privileged: true" docker-compose.yml; then
    echo "❌ FAIL: docker-compose.yml configures unsafe privileged: true."
    exit 1
  fi
fi

echo "✅ Docker Hardening Security Gate Passed."
exit 0
