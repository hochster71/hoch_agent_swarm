#!/usr/bin/env bash
# HOCH Agent Swarm Production Deployment and Rollback Verification Utility
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0;30m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}=================================================="
echo -e "HOCH AGENT SWARM DEPLOYMENT & ROLLBACK ORCHESTRATOR"
echo -e "==================================================${NC}"

# Check for required commands
for cmd in docker git curl; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[ERROR] Required command '$cmd' is not installed. Aborting.${NC}"
        exit 1
    fi
done

# Defaults
PORT="8086"
HEALTH_URL="http://127.0.0.1:${PORT}/api/v1/operator/health"
ROLLBACK_TAG=""

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --rollback-tag <tag>   Git tag or commit SHA to revert to if health check fails"
    echo "  -h, --help             Show this help message"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rollback-tag)
            ROLLBACK_TAG="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}[ERROR] Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Check if git tree is clean
if [[ -n "$(git status --porcelain)" ]]; then
    echo -e "${YELLOW}[WARNING] Working tree is dirty. Proceeding with caution...${NC}"
fi

# Step 1: Boot docker compose service
echo -e "\n${BOLD}[1/4] Starting hoch-app container via Docker Compose...${NC}"
docker compose up -d hoch-app

# Step 2: Poll Health endpoint
echo -e "\n${BOLD}[2/4] Verifying runtime healthiness at ${HEALTH_URL}...${NC}"
HEALTHY=false
for i in {1..15}; do
    echo -e "Polling health check (attempt $i/15)..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || true)
    if [[ "$HTTP_STATUS" == "200" ]]; then
        HEALTHY=true
        break
    fi
    sleep 2
done

if [ "$HEALTHY" = true ]; then
    echo -e "${GREEN}[PASS] Runtime health check returned 200 OK.${NC}"
else
    echo -e "${RED}[FAIL] Runtime health check failed (timeout or non-200 status).${NC}"
    
    if [[ -n "$ROLLBACK_TAG" ]]; then
        echo -e "${YELLOW}[ALERT] Initiating automatic rollback to: ${ROLLBACK_TAG}${NC}"
        # Stop container first
        docker compose down
        # Execute rollback script
        if [[ -f "scripts/security/rc22_rollback.sh" ]]; then
            bash scripts/security/rc22_rollback.sh "$ROLLBACK_TAG"
        else
            echo -e "${RED}[ERROR] Rollback script scripts/security/rc22_rollback.sh not found.${NC}"
        fi
        exit 1
    else
        echo -e "${YELLOW}[WARNING] No rollback tag specified (--rollback-tag). Leaving container running for debugging.${NC}"
        exit 1
    fi
fi

# Step 3: Verify SBOM/Release artifacts exist locally
echo -e "\n${BOLD}[3/4] Checking release artifacts signature & SBOM files...${NC}"
VERSION=$(node -e "console.log(require('./package.json').version)")
RELEASE_DIR="dist/releases/${VERSION}"

if [[ -d "$RELEASE_DIR" ]]; then
    echo -e "Found release directory: ${RELEASE_DIR}"
    for file in sbom.spdx.json release_manifest.json verification_report.json; do
        if [[ -f "${RELEASE_DIR}/${file}" ]]; then
            echo -e "  - ${file}: ${GREEN}PRESENT${NC}"
        else
            echo -e "  - ${file}: ${RED}MISSING${NC}"
        fi
    done
else
    echo -e "${YELLOW}[WARNING] No compiled release artifacts folder found for version ${VERSION}.${NC}"
fi

# Step 4: Success Summary
echo -e "\n${BOLD}=================================================="
echo -e "${GREEN}DEPLOYMENT COMPLETED SUCCESSFULLY"
echo -e "URL: http://localhost:${PORT}/"
echo -e "==================================================${NC}"
exit 0
