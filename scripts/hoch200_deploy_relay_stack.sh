#!/usr/bin/env bash
# =============================================================================
# hoch200_deploy_relay_stack.sh
# HOCH-200 — Deploy relay stack to hoch-relay-001
# =============================================================================
# Usage: bash scripts/hoch200_deploy_relay_stack.sh
# Requires: ssh access to root@50.116.41.183 (key auth)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VPS_USER="root"
VPS_HOST="50.116.41.183"
VPS_DEPLOY_DIR="/opt/hoch-relay"
LOCAL_INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/infra/hoch-200/vps"
TAILSCALE_IP="100.87.18.15"
RELAY_PORT=3012
COMPOSE_PROJECT="hoch-relay"

PASS="\033[0;32m✅\033[0m"
FAIL="\033[0;31m❌\033[0m"
INFO="\033[0;36mℹ\033[0m"
WARN="\033[0;33m⚠\033[0m"

log_pass() { echo -e "${PASS}  $*"; }
log_fail() { echo -e "${FAIL}  $*"; }
log_info() { echo -e "${INFO}  $*"; }
log_warn() { echo -e "${WARN}  $*"; }

GATE="CONDITIONAL_GO"
FAILURES=()

check_fail() {
  GATE="FAIL"
  FAILURES+=("$*")
  log_fail "$*"
}

# ---------------------------------------------------------------------------
# Pre-flight: confirm SSH key auth
# ---------------------------------------------------------------------------
log_info "HOCH-200 Relay Stack Deploy"
log_info "Target: ${VPS_USER}@${VPS_HOST}  Deploy dir: ${VPS_DEPLOY_DIR}"
log_info "Tailscale dashboard: http://${TAILSCALE_IP}:${RELAY_PORT}"
echo ""

log_info "Pre-flight: testing SSH connectivity..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "${VPS_USER}@${VPS_HOST}" "echo ssh-ok" &>/dev/null; then
  log_fail "SSH key auth to ${VPS_USER}@${VPS_HOST} failed."
  log_info "Set up SSH key auth first: ssh-copy-id ${VPS_USER}@${VPS_HOST}"
  exit 1
fi
log_pass "SSH connectivity confirmed"

# ---------------------------------------------------------------------------
# Step 1: rsync infra dir to VPS
# ---------------------------------------------------------------------------
log_info "Step 1/5: Syncing relay stack to VPS..."
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${VPS_DEPLOY_DIR}"
rsync -avz --delete \
  --exclude '.DS_Store' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "${LOCAL_INFRA_DIR}/" \
  "${VPS_USER}@${VPS_HOST}:${VPS_DEPLOY_DIR}/"
log_pass "Sync complete → ${VPS_DEPLOY_DIR}/"

# ---------------------------------------------------------------------------
# Step 2: Build + start containers
# ---------------------------------------------------------------------------
log_info "Step 2/5: Building and starting containers..."
ssh "${VPS_USER}@${VPS_HOST}" bash <<REMOTE_EOF
  set -euo pipefail
  cd ${VPS_DEPLOY_DIR}
  docker compose -p ${COMPOSE_PROJECT} pull --ignore-pull-failures 2>/dev/null || true
  docker compose -p ${COMPOSE_PROJECT} up -d --build --remove-orphans
  echo "docker-compose-up-ok"
REMOTE_EOF
log_pass "docker compose up completed"

# ---------------------------------------------------------------------------
# Step 3: Verify containers are healthy
# ---------------------------------------------------------------------------
log_info "Step 3/5: Waiting for container health (up to 60s)..."
WAIT=0
HEALTHY=false
while [ $WAIT -lt 60 ]; do
  CONTAINER_STATUS=$(ssh "${VPS_USER}@${VPS_HOST}" \
    "docker inspect --format='{{.State.Health.Status}}' hoch-relay-api 2>/dev/null || echo 'not-found'")
  if [ "$CONTAINER_STATUS" = "healthy" ]; then
    HEALTHY=true
    break
  fi
  sleep 5
  WAIT=$((WAIT + 5))
  log_info "  Still waiting… (${WAIT}s) container=${CONTAINER_STATUS}"
done

if $HEALTHY; then
  log_pass "hoch-relay-api container is healthy"
else
  log_warn "Container health status: ${CONTAINER_STATUS:-unknown} — proceeding with endpoint check"
fi

# ---------------------------------------------------------------------------
# Step 4: Confirm /health endpoint via Tailscale IP
# ---------------------------------------------------------------------------
log_info "Step 4/5: Verifying /health endpoint via Tailscale..."
HEALTH_RESP=$(ssh "${VPS_USER}@${VPS_HOST}" \
  "curl -sf --max-time 10 http://${TAILSCALE_IP}:${RELAY_PORT}/health 2>/dev/null || echo 'CURL_FAIL'")

if echo "${HEALTH_RESP}" | grep -q '"status":"ok"'; then
  log_pass "/health returned OK: ${HEALTH_RESP}"
else
  check_fail "/health check failed. Response: ${HEALTH_RESP}"
fi

# ---------------------------------------------------------------------------
# Step 5: Confirm port 3012 is NOT publicly reachable
# ---------------------------------------------------------------------------
log_info "Step 5/5: Verifying port 3012 is NOT publicly exposed..."

# Check UFW rules
UFW_CHECK=$(ssh "${VPS_USER}@${VPS_HOST}" \
  "ufw status numbered 2>/dev/null | grep -E '3012' || echo 'no-3012-rule'")
log_info "UFW rules for 3012: ${UFW_CHECK}"

# Attempt public-IP reach from VPS itself (loopback to public interface)
PUB_REACH=$(ssh "${VPS_USER}@${VPS_HOST}" \
  "curl -sf --max-time 5 --interface eth0 http://${VPS_HOST}:${RELAY_PORT}/health 2>/dev/null && echo REACHABLE || echo NOT_REACHABLE")

if [ "$PUB_REACH" = "NOT_REACHABLE" ]; then
  log_pass "Port ${RELAY_PORT} is NOT reachable on public IP — constraint satisfied"
elif [ "$PUB_REACH" = "REACHABLE" ]; then
  check_fail "SECURITY VIOLATION: Port ${RELAY_PORT} is reachable on public IP ${VPS_HOST}!"
  log_warn "Run: ufw deny ${RELAY_PORT} && ufw reload"
else
  log_warn "Public reach check inconclusive: ${PUB_REACH}"
fi

# Also verify docker port binding
DOCKER_BINDING=$(ssh "${VPS_USER}@${VPS_HOST}" \
  "docker port hoch-relay-api ${RELAY_PORT} 2>/dev/null || echo 'not-found'")
log_info "Docker port binding: ${DOCKER_BINDING}"
if echo "${DOCKER_BINDING}" | grep -q "0.0.0.0"; then
  check_fail "Container port ${RELAY_PORT} is bound to 0.0.0.0 — must be Tailscale IP only!"
elif echo "${DOCKER_BINDING}" | grep -q "${TAILSCALE_IP}"; then
  log_pass "Docker port binding confirmed: ${TAILSCALE_IP}:${RELAY_PORT} only"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "  HOCH-200 Deploy Result: ${GATE}"
echo "================================================================"

if [ "${#FAILURES[@]}" -gt 0 ]; then
  echo ""
  echo "  FAILURES:"
  for f in "${FAILURES[@]}"; do
    echo "    ❌ ${f}"
  done
fi

echo ""
echo "  Dashboard: http://${TAILSCALE_IP}:${RELAY_PORT}"
echo "  Health:    http://${TAILSCALE_IP}:${RELAY_PORT}/health"
echo "  Registry:  http://${TAILSCALE_IP}:${RELAY_PORT}/api/registry"
echo "================================================================"

if [ "$GATE" = "FAIL" ]; then
  exit 1
fi
exit 0
