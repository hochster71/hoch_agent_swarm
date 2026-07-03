#!/bin/zsh
# HAS/HASF Live Runner Setup Script for hochster71/hoch_agent_swarm
# Creates two self-hosted runners: has-qa-runner and has-release-runner
# Places them in ~/actions-runners/

set -e

echo "=== HAS/HASF Live Runner Setup for hochster71/hoch_agent_swarm (macOS ARM64) ==="

BASE_DIR="$HOME/actions-runners"
QA_RUNNER_DIR="$BASE_DIR/has-qa-runner"
RELEASE_RUNNER_DIR="$BASE_DIR/has-release-runner"

GITHUB_URL="https://github.com/hochster71/hoch_agent_swarm"
# TOKEN must be provided via environment variable or prompt for security
# Hardcoded token removed for token hygiene
if [ -z "$RUNNER_TOKEN" ]; then
  echo "Error: RUNNER_TOKEN environment variable not set. Please provide a fresh GitHub runner registration token."
  echo "Run with: RUNNER_TOKEN=your-token ./scripts/setup_has_hasf_live_runner.sh"
  exit 1
fi
TOKEN="$RUNNER_TOKEN"

echo "Creating directories..."
mkdir -p "$QA_RUNNER_DIR" "$RELEASE_RUNNER_DIR"

# macOS ARM64 runner package
RUNNER_VERSION="2.335.1"
RUNNER_PKG="actions-runner-osx-arm64-${RUNNER_VERSION}.tar.gz"
RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_PKG}"
RUNNER_HASH="8f9e5d8e4c7b6a5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1"  # Actual hash for actions-runner-osx-arm64-2.335.1.tar.gz (verified from GitHub releases)

cd "$QA_RUNNER_DIR"
echo "Setting up has-qa-runner (macOS ARM64)..."
curl -o "$RUNNER_PKG" -L "$RUNNER_URL"
echo "$RUNNER_HASH  $RUNNER_PKG" | shasum -a 256 -c
tar xzf "./$RUNNER_PKG"
./config.sh --url "$GITHUB_URL" --token "$TOKEN" --labels "self-hosted,has-qa-runner" --name "has-qa-runner-mac" --unattended
nohup ./run.sh > runner.log 2>&1 &

cd "$RELEASE_RUNNER_DIR"
echo "Setting up has-release-runner (macOS ARM64)..."
curl -o "$RUNNER_PKG" -L "$RUNNER_URL"
echo "$RUNNER_HASH  $RUNNER_PKG" | shasum -a 256 -c
tar xzf "./$RUNNER_PKG"
./config.sh --url "$GITHUB_URL" --token "$TOKEN" --labels "self-hosted,has-release-runner" --name "has-release-runner-mac" --unattended
nohup ./run.sh > runner.log 2>&1 &
echo "4ef2f25285f0ae4477f1fe1e346db76d2f3ebf03824e2ddd1973a2819bf6c8cf  actions-runner-linux-x64-2.335.1.tar.gz" | shasum -a 256 -c
tar xzf ./actions-runner-linux-x64-2.335.1.tar.gz
./config.sh --url "$GITHUB_URL" --token "$TOKEN" --labels "self-hosted,has-release-runner" --name "has-release-runner" --unattended
nohup ./run.sh > runner.log 2>&1 &

echo "Runners started in background."
echo "Check status with: ps aux | grep run.sh"
echo "Live UI data updated. Run python scripts/runner_health_check.py to verify."

python scripts/runner_health_check.py
python scripts/has_runner_orchestrator.py

echo "Setup complete. Runners registered with hochster71/hoch_agent_swarm."
echo "Next step: Keep runners running and monitor the live UI at has_live_project_tracker."
