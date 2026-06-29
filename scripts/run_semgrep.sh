#!/usr/bin/env bash
set -euo pipefail

# Verify semgrep command exists
if ! command -v semgrep &> /dev/null; then
    echo "[ERROR] Semgrep is not installed."
    echo "To install Semgrep, run: pip install semgrep"
    echo "Or on macOS: brew install semgrep"
    exit 1
fi

echo "[INFO] Running Semgrep static security scans..."
semgrep scan --config qa/semgrep/hoch-security.yml .
