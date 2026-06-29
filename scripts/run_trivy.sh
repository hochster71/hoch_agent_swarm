#!/usr/bin/env bash
set -euo pipefail

# Verify trivy command exists
if ! command -v trivy &> /dev/null; then
    echo "[ERROR] Trivy is not installed."
    echo "To install Trivy, run: brew install aquasecurity/trivy/trivy"
    echo "Or refer to: https://aquasecurity.github.io/trivy/v0.18.3/getting-started/installation/"
    exit 1
fi

echo "[INFO] Running Trivy filesystem scans..."
trivy fs --severity HIGH,CRITICAL --scanners vuln,config,secret .

echo "[INFO] Running Trivy image scans..."
trivy image --severity HIGH,CRITICAL --scanners vuln,config,secret hoch_agent_swarm-hoch-app:latest
