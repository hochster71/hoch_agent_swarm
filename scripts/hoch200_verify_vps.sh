#!/usr/bin/env bash
# =============================================================================
# hoch200_verify_vps.sh
# HOCH-200 — Verify VPS state and relay stack
# =============================================================================
# Usage: bash scripts/hoch200_verify_vps.sh
# Outputs structured evidence to stdout and updates hoch_pods/compute/setup_status.json
# =============================================================================
set -euo pipefail

VPS_USER="root"
VPS_HOST="50.116.41.183"
TAILSCALE_IP="100.87.18.15"
RELAY_PORT=3012
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS_FILE="${REPO_ROOT}/hoch_pods/compute/setup_status.json"

PASS="\033[0;32m✅\033[0m"
FAIL="\033[0;31m❌\033[0m"
INFO="\033[0;36mℹ\033[0m"
WARN="\033[0;33m⚠\033[0m"
UNKNOWN="\033[0;35m?\033[0m"

log_pass()    { echo -e "${PASS}  $*"; }
log_fail()    { echo -e "${FAIL}  $*"; }
log_info()    { echo -e "${INFO}  $*"; }
log_warn()    { echo -e "${WARN}  $*"; }
log_unknown() { echo -e "${UNKNOWN}  UNKNOWN: $*"; }

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GATE="CONDITIONAL_GO"
CHECKS=()
FAILURES=()

record_check() {
  local name="$1" status="$2" detail="$3"
  CHECKS+=("{\"check\":\"${name}\",\"status\":\"${status}\",\"detail\":\"${detail}\"}")
  case "$status" in
    PASS)    log_pass    "${name}: ${detail}" ;;
    FAIL)    log_fail    "${name}: ${detail}"; GATE="FAIL"; FAILURES+=("${name}") ;;
    WARN)    log_warn    "${name}: ${detail}" ;;
    UNKNOWN) log_unknown "${name}: ${detail}" ;;
  esac
}

# ---------------------------------------------------------------------------
# SSH connectivity
# ---------------------------------------------------------------------------
echo ""
log_info "HOCH-200 VPS Verification"
log_info "Target: ${VPS_USER}@${VPS_HOST}"
log_info "Timestamp: ${NOW}"
echo "---"

if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "${VPS_USER}@${VPS_HOST}" "echo ok" &>/dev/null; then
  record_check "ssh-connectivity" "FAIL" "Cannot reach ${VPS_HOST}"
  echo "GATE: FAIL (no SSH)"
  exit 1
fi
record_check "ssh-connectivity" "PASS" "${VPS_HOST} reachable"

# ---------------------------------------------------------------------------
# Remote checks (single SSH session for efficiency)
# ---------------------------------------------------------------------------
REMOTE_OUT=$(ssh "${VPS_USER}@${VPS_HOST}" bash << 'REMOTE'
set -euo pipefail

echo "HOSTNAME=$(hostname)"
echo "OS=$(. /etc/os-release && echo "${PRETTY_NAME}")"
echo "KERNEL=$(uname -r)"

# Docker
DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "not-found")
echo "DOCKER=${DOCKER_VER}"

# Docker compose
DC_VER=$(docker compose version --short 2>/dev/null || echo "not-found")
echo "DC=${DC_VER}"

# UFW active
UFW_STATUS=$(ufw status 2>/dev/null | head -1 | awk '{print $2}' || echo "unknown")
echo "UFW_STATUS=${UFW_STATUS}"

# UFW port 3012 rule
UFW_3012=$(ufw status numbered 2>/dev/null | grep "3012" | head -5 | tr '\n' '|' || echo "none")
echo "UFW_3012=${UFW_3012}"

# fail2ban
F2B=$(systemctl is-active fail2ban 2>/dev/null || echo "unknown")
echo "FAIL2BAN=${F2B}"

# Container running
CONT_STATUS=$(docker inspect --format='{{.State.Status}}' hoch-relay-api 2>/dev/null || echo "not-found")
echo "CONTAINER_STATUS=${CONT_STATUS}"

# Container health
CONT_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' hoch-relay-api 2>/dev/null || echo "no-healthcheck")
echo "CONTAINER_HEALTH=${CONT_HEALTH}"

# Docker port binding
PORT_BIND=$(docker port hoch-relay-api 3012 2>/dev/null || echo "not-bound")
echo "PORT_BIND=${PORT_BIND}"

# /health endpoint via Tailscale
HEALTH=$(curl -sf --max-time 8 http://100.87.18.15:3012/health 2>/dev/null || echo "FAIL")
echo "HEALTH_RESP=${HEALTH}"

# Public IP reach attempt
PUB_REACH=$(curl -sf --max-time 5 http://50.116.41.183:3012/health 2>/dev/null && echo "REACHABLE" || echo "NOT_REACHABLE")
echo "PUB_REACH=${PUB_REACH}"

# Evidence file
EV_FILE=$(test -f /root/hoch200_node_status.txt && echo "exists" || echo "missing")
echo "EVIDENCE_FILE=${EV_FILE}"

REMOTE
)

# Parse remote output
get_val() { echo "${REMOTE_OUT}" | grep "^${1}=" | cut -d= -f2-; }

HOSTNAME=$(get_val HOSTNAME)
OS=$(get_val OS)
KERNEL=$(get_val KERNEL)
DOCKER=$(get_val DOCKER)
DC=$(get_val DC)
UFW_STATUS=$(get_val UFW_STATUS)
UFW_3012=$(get_val UFW_3012)
FAIL2BAN=$(get_val FAIL2BAN)
CONT_STATUS=$(get_val CONTAINER_STATUS)
CONT_HEALTH=$(get_val CONTAINER_HEALTH)
PORT_BIND=$(get_val PORT_BIND)
HEALTH_RESP=$(get_val HEALTH_RESP)
PUB_REACH=$(get_val PUB_REACH)
EVIDENCE_FILE=$(get_val EVIDENCE_FILE)

# ---------------------------------------------------------------------------
# Evaluate checks
# ---------------------------------------------------------------------------
echo ""

# OS / infra
record_check "hostname"         "PASS"    "${HOSTNAME}"
record_check "os"               "PASS"    "${OS}"
record_check "kernel"           "PASS"    "${KERNEL}"

# Docker
if [ -n "$DOCKER" ] && [ "$DOCKER" != "not-found" ]; then
  record_check "docker-version" "PASS" "${DOCKER}"
else
  record_check "docker-version" "FAIL" "Docker not found or version check failed"
fi

if [ -n "$DC" ] && [ "$DC" != "not-found" ]; then
  record_check "docker-compose-version" "PASS" "${DC}"
else
  record_check "docker-compose-version" "FAIL" "Docker Compose not found"
fi

# UFW
if [ "$UFW_STATUS" = "active" ]; then
  record_check "ufw-active" "PASS" "UFW is active"
else
  record_check "ufw-active" "FAIL" "UFW status: ${UFW_STATUS}"
fi

# UFW port 3012 — must NOT have a ALLOW rule from ANY
if echo "$UFW_3012" | grep -qiE "ALLOW.*Anywhere|allow.*any"; then
  record_check "ufw-port-3012-blocked" "FAIL" "UFW has ALLOW rule for 3012: ${UFW_3012}"
else
  record_check "ufw-port-3012-blocked" "PASS" "No public ALLOW rule for 3012 (rules: ${UFW_3012:-none})"
fi

# fail2ban
if [ "$FAIL2BAN" = "active" ]; then
  record_check "fail2ban-active" "PASS" "fail2ban running"
else
  record_check "fail2ban-active" "WARN" "fail2ban status: ${FAIL2BAN}"
fi

# Container
if [ "$CONT_STATUS" = "running" ]; then
  record_check "container-running" "PASS" "hoch-relay-api: running"
else
  record_check "container-running" "FAIL" "hoch-relay-api status: ${CONT_STATUS}"
fi

if [ "$CONT_HEALTH" = "healthy" ] || [ "$CONT_HEALTH" = "no-healthcheck" ]; then
  record_check "container-healthy" "PASS" "hoch-relay-api health: ${CONT_HEALTH}"
else
  record_check "container-healthy" "WARN" "hoch-relay-api health: ${CONT_HEALTH}"
fi

# Port binding — must be Tailscale IP only
if echo "$PORT_BIND" | grep -q "100.87.18.15"; then
  record_check "port-binding-tailscale-only" "PASS" "Bound to ${PORT_BIND}"
elif echo "$PORT_BIND" | grep -q "0.0.0.0"; then
  record_check "port-binding-tailscale-only" "FAIL" "Port bound to 0.0.0.0 — security violation!"
elif [ "$PORT_BIND" = "not-bound" ]; then
  record_check "port-binding-tailscale-only" "FAIL" "Port 3012 not bound at all"
else
  record_check "port-binding-tailscale-only" "UNKNOWN" "Binding: ${PORT_BIND}"
fi

# Health endpoint
if echo "$HEALTH_RESP" | grep -q '"status":"ok"'; then
  record_check "relay-health-endpoint" "PASS" "http://${TAILSCALE_IP}:${RELAY_PORT}/health → OK"
else
  record_check "relay-health-endpoint" "FAIL" "Health endpoint returned: ${HEALTH_RESP}"
fi

# Public IP must NOT be reachable
if [ "$PUB_REACH" = "NOT_REACHABLE" ]; then
  record_check "port-3012-not-public" "PASS" "Public IP ${VPS_HOST}:3012 unreachable — constraint satisfied"
elif [ "$PUB_REACH" = "REACHABLE" ]; then
  record_check "port-3012-not-public" "FAIL" "SECURITY VIOLATION: ${VPS_HOST}:3012 is publicly reachable!"
else
  record_check "port-3012-not-public" "UNKNOWN" "Reach check result: ${PUB_REACH}"
fi

# Evidence file
if [ "$EVIDENCE_FILE" = "exists" ]; then
  record_check "evidence-file" "PASS" "/root/hoch200_node_status.txt exists"
else
  record_check "evidence-file" "WARN" "/root/hoch200_node_status.txt not found"
fi

# Worker registry check
if echo "$HEALTH_RESP" | grep -q '"worker":"HAS-WORKER-RELAY-001"'; then
  record_check "worker-registry-HAS-WORKER-RELAY-001" "PASS" "Worker ID confirmed in /health"
else
  record_check "worker-registry-HAS-WORKER-RELAY-001" "WARN" "Worker ID not in /health response (check /api/registry)"
fi

# ---------------------------------------------------------------------------
# Write setup_status.json
# ---------------------------------------------------------------------------
CHECKS_JSON=$(IFS=,; echo "${CHECKS[*]}")
cat > "${STATUS_FILE}" << JSON
{
  "schema_version": "1.0",
  "epic": "HOCH-200",
  "node": "hoch-relay-001",
  "public_ipv4": "${VPS_HOST}",
  "tailscale_ip": "${TAILSCALE_IP}",
  "relay_port": ${RELAY_PORT},
  "gate": "${GATE}",
  "verified_at": "${NOW}",
  "checks": [${CHECKS_JSON}],
  "failures": $(printf '"%s",' "${FAILURES[@]:-}" | sed 's/,$//' | sed 's/^/[/' | sed 's/$/]/')
}
JSON

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "  HOCH-200 VPS Verification: ${GATE}"
echo "================================================================"
echo "  Node:        ${HOSTNAME} (${VPS_HOST})"
echo "  Tailscale:   ${TAILSCALE_IP}"
echo "  Container:   ${CONT_STATUS} / ${CONT_HEALTH}"
echo "  Port 3012:   Tailscale-only = $([ "$PUB_REACH" = "NOT_REACHABLE" ] && echo YES || echo NO)"
echo "  Status file: ${STATUS_FILE}"
echo "================================================================"
echo ""
echo "  Failures: ${#FAILURES[@]}"
if [ "${#FAILURES[@]}" -gt 0 ]; then
  for f in "${FAILURES[@]}"; do echo "    ❌ ${f}"; done
fi
echo ""

if [ "$GATE" = "FAIL" ]; then exit 1; fi
exit 0
