#!/usr/bin/env bash
# scripts/pods_status.sh — Check status of HOCH Swarm Pods
set -uo pipefail

# Load secrets if present
SECRETS_PATH="$HOME/.hoch-secrets/has-tracker.env"
if [[ -f "$SECRETS_PATH" ]]; then
  # Source using a subshell parsing mechanism to avoid shell option collision
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[A-Za-z0-9_]+= ]]; then
      eval "export $line"
    fi
  done < "$SECRETS_PATH"
fi

PORT="${TRACKER_PORT:-3001}"
USER="${TRACKER_USER:-admin}"
PASS="${TRACKER_PASSWORD:-change-this-password}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${BOLD}==================================================${NC}"
echo -e "${BOLD}  HOCH Swarm Pods Status Summary${NC}"
echo -e "${BOLD}==================================================${NC}"

# Query /api/pods
echo -e "${CYAN}→ Fetching Pods list from Control Plane...${NC}"
curl -s -u "${USER}:${PASS}" "http://localhost:${PORT}/api/pods" | python3 -m json.tool || curl -s -u "${USER}:${PASS}" "http://localhost:${PORT}/api/pods"

# Query /api/v1/pods/missions
echo -e "\n${CYAN}→ Fetching Mission Control history from HAS Backend...${NC}"
curl -s -u "${USER}:${PASS}" "http://localhost:${PORT}/api/v1/pods/missions" | python3 -m json.tool || curl -s -u "${USER}:${PASS}" "http://localhost:${PORT}/api/v1/pods/missions"

echo ""
