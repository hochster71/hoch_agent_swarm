#!/usr/bin/env bash
set -euo pipefail

OWNER="hochster71"
REPO="hoch_agent_swarm"
REPO_URL="https://github.com/${OWNER}/${REPO}"
RUNNER_NAME="has-qa-runner-mac"
RUNNER_LABELS="self-hosted,macOS,ARM64,has-qa-runner"
RUNNER_ROOT="$HOME/actions-runners"
RUNNER_DIR="$RUNNER_ROOT/has-qa-runner"
RUNNER_VERSION="2.335.1"
RUNNER_FILE="actions-runner-osx-arm64-${RUNNER_VERSION}.tar.gz"
RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_FILE}"

echo "============================================================"
echo " HAS/HASF GitHub Actions QA Runner Setup"
echo " Repo:   ${REPO_URL}"
echo " Runner: ${RUNNER_NAME}"
echo " Path:   ${RUNNER_DIR}"
echo "============================================================"
echo

echo "This script needs a GitHub PAT with admin access to:"
echo "  ${OWNER}/${REPO}"
echo
echo "The token will NOT be printed or saved."
echo

printf "Paste GitHub PAT now: "
stty -echo
IFS= read -r GITHUB_PAT
stty echo
printf "\n"

if [ -z "$GITHUB_PAT" ]; then
  echo "NO-GO: empty token."
  exit 1
fi

cleanup() {
  unset GITHUB_PAT || true
  unset RUNNER_TOKEN || true
}
trap cleanup EXIT

api() {
  local method="$1"
  local path="$2"
  curl -fsSL \
    -X "$method" \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_PAT}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com${path}"
}

echo
echo "1/8 Checking local platform..."
OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" != "Darwin" ]; then
  echo "NO-GO: this script is for macOS. Detected: $OS"
  exit 1
fi

if [ "$ARCH" != "arm64" ]; then
  echo "NO-GO: this script is for Apple Silicon ARM64. Detected: $ARCH"
  exit 1
fi

echo "PASS: macOS ARM64"

echo
echo "2/8 Verifying GitHub repo access..."
REPO_CHECK="$(api GET "/repos/${OWNER}/${REPO}")"

python3 - "$REPO_CHECK" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
full_name = data.get("full_name")
if full_name != "hochster71/hoch_agent_swarm":
    print(f"NO-GO: wrong repo or no access: {full_name}")
    sys.exit(1)
print(f"PASS: repo access verified: {full_name}")
PY

echo
echo "3/8 Requesting fresh runner registration token from GitHub..."
TOKEN_RESPONSE="$(api POST "/repos/${OWNER}/${REPO}/actions/runners/registration-token")"

RUNNER_TOKEN="$(python3 - "$TOKEN_RESPONSE" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
token = data.get("token")
if not token:
    print("")
    sys.exit(1)
print(token)
PY
)"

if [ -z "$RUNNER_TOKEN" ]; then
  echo "NO-GO: could not get GitHub runner registration token."
  exit 1
fi

echo "PASS: fresh registration token received from GitHub API"

echo
echo "4/8 Preparing runner directory..."
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo "Removing failed/partial old local config if present..."
if [ -f ".runner" ]; then
  ./config.sh remove --token "$RUNNER_TOKEN" || true
fi

echo
echo "5/8 Downloading/extracting macOS ARM64 runner..."
if [ ! -f "$RUNNER_FILE" ]; then
  curl -fL -o "$RUNNER_FILE" "$RUNNER_URL"
else
  echo "Runner archive already exists: $RUNNER_FILE"
fi

if [ ! -x "./config.sh" ] || [ ! -x "./run.sh" ]; then
  tar xzf "$RUNNER_FILE"
fi

chmod +x ./config.sh ./run.sh || true

echo
echo "6/8 Configuring runner..."
./config.sh \
  --url "$REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABELS" \
  --unattended \
  --replace

echo "PASS: runner configured"

echo
echo "7/8 Starting runner..."

if [ -f "./svc.sh" ]; then
  chmod +x ./svc.sh || true
  echo "svc.sh found. Installing as macOS service."

  if ./svc.sh install; then
    true
  else
    echo "Non-sudo service install failed. Trying sudo..."
    sudo ./svc.sh install
  fi

  if ./svc.sh start; then
    true
  else
    echo "Non-sudo service start failed. Trying sudo..."
    sudo ./svc.sh start
  fi

  echo
  echo "Service status:"
  ./svc.sh status || true

  START_MODE="service"
else
  echo "svc.sh not found after config."
  echo "Starting runner with nohup fallback."
  echo "This proves the runner online, but service persistence may still need later fix."

  nohup ./run.sh > "$RUNNER_DIR/has-qa-runner.log" 2>&1 &
  START_MODE="nohup"
fi

echo
echo "8/8 Checking GitHub runner online status..."
sleep 8

RUNNERS_JSON="$(api GET "/repos/${OWNER}/${REPO}/actions/runners")"

ONLINE_STATUS="$(python3 - "$RUNNERS_JSON" "$RUNNER_NAME" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
target = sys.argv[2]
for r in data.get("runners", []):
    if r.get("name") == target:
        labels = ",".join(x.get("name", "") for x in r.get("labels", []))
        print(f"name={r.get('name')} status={r.get('status')} busy={r.get('busy')} labels={labels}")
        sys.exit(0)
print("NOT_FOUND")
sys.exit(2)
PY
)" || true

echo "$ONLINE_STATUS"

cd /Users/michaelhoch/hoch_agent_swarm

mkdir -p has_live_project_tracker/data docs/evidence/runtime

cat > has_live_project_tracker/data/live_runner_status.json <<JSON
{
  "runner": "has-qa-runner-mac",
  "repo": "hochster71/hoch_agent_swarm",
  "start_mode": "$START_MODE",
  "github_status": "$ONLINE_STATUS",
  "deployment_blocked": true,
  "stripe_blocked": true,
  "apple_google_submission_blocked": true,
  "paid_provider_blocked": true,
  "next_action": "Run GitHub Actions workflow: HAS QA Runner"
}
JSON

cat > docs/evidence/runtime/has-qa-runner-setup-result.md <<MD
# HAS QA Runner Setup Result

- Repo: \`hochster71/hoch_agent_swarm\`
- Runner: \`has-qa-runner-mac\`
- Labels: \`self-hosted, macOS, ARM64, has-qa-runner\`
- Start mode: \`$START_MODE\`
- GitHub status: \`$ONLINE_STATUS\`

## Boundaries

- Production deploy: BLOCKED
- Stripe/live monetization: BLOCKED
- Apple/Google submission: BLOCKED
- Paid providers: BLOCKED

## Next Action

Open GitHub Actions and run:

\`HAS QA Runner\`
MD

echo
echo "============================================================"
echo " RESULT"
echo "============================================================"
echo "Runner:      $RUNNER_NAME"
echo "Start mode:  $START_MODE"
echo "GitHub says: $ONLINE_STATUS"
echo
echo "Open this page:"
echo "https://github.com/hochster71/hoch_agent_swarm/settings/actions/runners"
echo
echo "Then open Actions:"
echo "https://github.com/hochster71/hoch_agent_swarm/actions"
echo
echo "Run workflow:"
echo "HAS QA Runner"
echo "============================================================"

if echo "$ONLINE_STATUS" | grep -q "status=online"; then
  echo "FINAL GO: runner is online."
else
  echo "CONDITIONAL: runner configured, but GitHub online status not confirmed yet."
  echo "Wait 30 seconds and refresh the GitHub runners page."
fi
