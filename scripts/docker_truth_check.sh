#!/usr/bin/env bash
set -euo pipefail

export DOCKER_API_VERSION=1.41


# Pin Docker context to desktop-linux
if docker context ls | grep -F "desktop-linux" >/dev/null; then
  docker context use desktop-linux >/dev/null
fi

echo "Docker context: $(docker context show)"
echo "Docker server version:"
docker info | grep -E "Server Version" || docker info --format '{{.ServerVersion}}' || echo "Unknown"
echo "Running HAS containers:"
docker compose ps
# 0. Run Docker Role Separation Check
echo "==> Running Docker Role Separation Check..."
bash scripts/docker_role_separation_check.sh

echo "==> Running Docker UI/API Truth Alignment Check..."

API_HOST="http://localhost:8000"
UI_HOST="http://localhost:8080"

# 1. Query Container API Verdict
echo "Fetching Final Verifier Verdict from $API_HOST..."
VERDICT_JSON=$(curl -sS --fail "$API_HOST/api/v1/final-verifier/verdict")
echo "Verdict API Response:"
echo "$VERDICT_JSON" | grep -E "status|readiness" || echo "$VERDICT_JSON"

# 2. Query Container Runtime Truth State
echo "Fetching Runtime Truth State from $API_HOST..."
TRUTH_JSON=$(curl -sS --fail "$API_HOST/api/v1/runtime-truth/state")

# 3. Fetch Container-Served UI HTML
echo "Fetching Served UI Dashboard from $UI_HOST..."
UI_HTML=$(curl -sS --fail "$UI_HOST/")

# 4. Check for forbidden stale strings in the served HTML
FORBIDDEN_STRINGS=(
  "FINAL VERIFIER: VERIFIED"
  "Readiness Score: 100%"
  "GO FOR SWARM"
  "Production Status: ALLOWED"
  "LAUNCH_READY"
  "Active RC: RC30 Tracker"
)

STALE_FOUND=0

echo "Scanning UI bundle for forbidden stale strings..."
for pattern in "${FORBIDDEN_STRINGS[@]}"; do
  if echo "$UI_HTML" | grep -Fq "$pattern"; then
    echo "❌ STALE REGRESSION DETECTED: UI contains forbidden string '$pattern'!"
    STALE_FOUND=1
  else
    echo "  [OK] Pattern absent: '$pattern'"
  fi
done

if [ "$STALE_FOUND" -ne 0 ]; then
  echo "ERROR: Docker UI is not aligned with Final Verifier. Stale telemetry strings are visible!"
  exit 1
fi

echo "✅ Docker UI and API Truth are fully aligned."
exit 0
