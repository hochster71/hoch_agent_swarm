#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/hochster71/hoch_agent_swarm"
RUNNER_NAME="has-qa-runner-mac"
RUNNER_LABELS="self-hosted,macOS,ARM64,has-qa-runner"
RUNNER_DIR="$HOME/actions-runners/has-qa-runner"
RUNNER_VERSION="2.335.1"
RUNNER_FILE="actions-runner-osx-arm64-${RUNNER_VERSION}.tar.gz"
RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_FILE}"

echo "============================================================"
echo " HAS/HASF QA Runner Setup using GitHub UI runner token"
echo " Repo:   ${REPO_URL}"
echo " Runner: ${RUNNER_NAME}"
echo " Path:   ${RUNNER_DIR}"
echo "============================================================"
echo
echo "Use the token from:"
echo "https://github.com/hochster71/hoch_agent_swarm/settings/actions/runners/new?arch=arm64&os=osx"
echo
echo "Copy ONLY the token after --token."
echo "Do not include ./config.sh, --url, --token, or dollar signs."
echo

printf "Paste GitHub UI runner token now: "
stty -echo
IFS= read -r RUNNER_TOKEN
stty echo
printf "\n"

if [ -z "${RUNNER_TOKEN}" ]; then
  echo "NO-GO: empty token."
  exit 1
fi

cleanup() {
  unset RUNNER_TOKEN || true
}
trap cleanup EXIT

echo
echo "1/7 Checking platform..."
if [ "$(uname -s)" != "Darwin" ]; then
  echo "NO-GO: this script is for macOS."
  exit 1
fi

if [ "$(uname -m)" != "arm64" ]; then
  echo "NO-GO: this script is for Apple Silicon ARM64."
  exit 1
fi

echo "PASS: macOS ARM64"

echo
echo "2/7 Preparing runner directory..."
mkdir -p "${RUNNER_DIR}"
cd "${RUNNER_DIR}"

echo
echo "3/7 Downloading runner if needed..."
if [ ! -f "${RUNNER_FILE}" ]; then
  curl -fL -o "${RUNNER_FILE}" "${RUNNER_URL}"
else
  echo "Runner archive already exists."
fi

echo
echo "4/7 Extracting runner if needed..."
if [ ! -x ./config.sh ] || [ ! -x ./run.sh ]; then
  tar xzf "${RUNNER_FILE}"
else
  echo "Runner already extracted."
fi

chmod +x ./config.sh ./run.sh || true

echo
echo "5/7 Removing old local runner config if present..."
if [ -f .runner ]; then
  ./config.sh remove --token "${RUNNER_TOKEN}" || true
fi

echo
echo "6/7 Configuring runner..."
./config.sh \
  --url "${REPO_URL}" \
  --token "${RUNNER_TOKEN}" \
  --name "${RUNNER_NAME}" \
  --labels "${RUNNER_LABELS}" \
  --unattended \
  --replace

unset RUNNER_TOKEN

echo
echo "7/7 Starting runner..."

START_MODE="manual"

if [ -f ./svc.sh ]; then
  chmod +x ./svc.sh || true
  echo "svc.sh found. Installing as macOS service."

  if ./svc.sh install; then
    true
  else
    echo "Trying sudo service install..."
    sudo ./svc.sh install || true
  fi

  if ./svc.sh start; then
    true
  else
    echo "Trying sudo service start..."
    sudo ./svc.sh start || true
  fi

  echo
  echo "Service status:"
  ./svc.sh status || true
  START_MODE="service"
else
  echo "svc.sh not found. Starting runner manually with nohup."
  nohup ./run.sh > "${RUNNER_DIR}/has-qa-runner.log" 2>&1 &
  START_MODE="nohup"
fi

cd /Users/michaelhoch/hoch_agent_swarm
mkdir -p has_live_project_tracker/data docs/evidence/runtime

cat > has_live_project_tracker/data/live_runner_status.json <<JSON
{
  "runner": "has-qa-runner-mac",
  "repo": "hochster71/hoch_agent_swarm",
  "start_mode": "${START_MODE}",
  "status": "CONFIGURED_CHECK_GITHUB_UI",
  "deployment_blocked": true,
  "stripe_blocked": true,
  "apple_google_submission_blocked": true,
  "paid_provider_blocked": true,
  "next_action": "Confirm runner is Online in GitHub, then run HAS QA Runner workflow."
}
JSON

cat > docs/evidence/runtime/has-qa-runner-setup-result.md <<MD
# HAS QA Runner Setup Result

- Repo: \`hochster71/hoch_agent_swarm\`
- Runner: \`has-qa-runner-mac\`
- Labels: \`self-hosted, macOS, ARM64, has-qa-runner\`
- Start mode: \`${START_MODE}\`

## Boundaries

- Production deploy: BLOCKED
- Stripe/live monetization: BLOCKED
- Apple/Google submission: BLOCKED
- Paid providers: BLOCKED

## Next Action

Confirm this runner is Online:

\`https://github.com/hochster71/hoch_agent_swarm/settings/actions/runners\`

Then run:

\`HAS QA Runner\`
MD

echo
echo "============================================================"
echo " RESULT"
echo "============================================================"
echo "Runner:     ${RUNNER_NAME}"
echo "Start mode: ${START_MODE}"
echo
echo "Open this page and confirm Online:"
echo "https://github.com/hochster71/hoch_agent_swarm/settings/actions/runners"
echo
echo "Then open Actions:"
echo "https://github.com/hochster71/hoch_agent_swarm/actions"
echo
echo "Run workflow:"
echo "HAS QA Runner"
echo "============================================================"
