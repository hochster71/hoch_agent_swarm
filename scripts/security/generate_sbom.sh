#!/usr/bin/env bash
set -euo pipefail

echo "============================================="
echo "   Generating Software Bill of Materials      "
echo "============================================="

# Ensure artifacts/security directory exists
mkdir -p artifacts/security

# Try generating Python dependencies SBOM using uv/cyclonedx-py
if command -v uv &> /dev/null; then
    echo "[INFO] Found uv. Generating Python SBOM via uvx cyclonedx-py..."
    if uvx --from cyclonedx-bom cyclonedx-py environment --spec-version 1.5 --output-format JSON --output-file artifacts/security/sbom-rc21.json; then
        echo "[SUCCESS] SBOM generated successfully at artifacts/security/sbom-rc21.json"
        exit 0
    else
        echo "[ERROR] Failed to generate SBOM using cyclonedx-py."
        exit 1
    fi
elif command -v cyclonedx-py &> /dev/null; then
    echo "[INFO] Found cyclonedx-py. Generating Python SBOM..."
    if cyclonedx-py environment --spec-version 1.5 --output-format JSON --output-file artifacts/security/sbom-rc21.json; then
        echo "[SUCCESS] SBOM generated successfully at artifacts/security/sbom-rc21.json"
        exit 0
    else
        echo "[ERROR] Failed to generate SBOM using cyclonedx-py."
        exit 1
    fi
elif command -v syft &> /dev/null; then
    echo "[INFO] Found Syft. Generating filesystem SBOM..."
    if syft scan dir:. -o json > artifacts/security/sbom-rc21.json; then
        echo "[SUCCESS] SBOM generated successfully via Syft at artifacts/security/sbom-rc21.json"
        exit 0
    else
        echo "[ERROR] Failed to generate SBOM using Syft."
        exit 1
    fi
else
    echo "[ERROR] No SBOM generation tools found!"
    echo "Please install Astral uv to allow dynamic execution of cyclonedx-py:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Or install cyclonedx-py:"
    echo "  pip install cyclonedx-bom"
    echo "Or install Anchore Syft:"
    echo "  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
    exit 1
fi
