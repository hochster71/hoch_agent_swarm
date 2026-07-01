#!/usr/bin/env bash
set -euo pipefail

echo "============================================="
echo "   HOCH Swarm Local Security Gate (rc21)     "
echo "============================================="

# 1. Required: Run pytest
echo -e "\n[INFO] Step 1: Running pytest unit tests..."
if uv run pytest -q; then
    echo "[SUCCESS] Pytest unit tests passed."
else
    echo "[FAIL] Pytest unit tests failed!"
    exit 1
fi

# 2. Required: Validate docker compose config
echo -e "\n[INFO] Step 2: Validating docker-compose.yml..."
if docker compose config >/dev/null; then
    echo "[SUCCESS] Docker compose configuration is valid."
else
    echo "[FAIL] Docker compose configuration validation failed!"
    exit 1
fi

# 3. Optional: Run Semgrep
echo -e "\n[INFO] Step 3: Running Semgrep static scan..."
if command -v semgrep &> /dev/null; then
    if bash scripts/run_semgrep.sh; then
        echo "[SUCCESS] Semgrep static scan completed with no errors."
    else
        echo "[FAIL] Semgrep static scan found violations!"
        exit 1
    fi
else
    echo "[WARNING] Semgrep binary not found locally."
    echo "To install Semgrep, run: pip install semgrep"
    echo "Or on macOS: brew install semgrep"
fi

# 4. Optional: Run Trivy
echo -e "\n[INFO] Step 4: Running Trivy vulnerability scan..."
if command -v trivy &> /dev/null; then
    if bash scripts/run_trivy.sh; then
        echo "[SUCCESS] Trivy filesystem/image scan completed with no errors."
    else
        echo "[FAIL] Trivy scan found violations!"
        exit 1
    fi
else
    echo "[WARNING] Trivy binary not found locally."
    echo "To install Trivy, run: brew install aquasecurity/trivy/trivy"
    echo "Or refer to: https://aquasecurity.github.io/trivy/v0.18.3/getting-started/installation/"
fi

echo -e "\n============================================="
echo "   Local security gate checks finished.      "
echo "============================================="
