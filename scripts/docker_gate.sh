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

echo "==> Starting HAS Docker-First Compliance Gate..."

# 1. Docker Daemon Health Gate
echo "Verifying Docker Daemon health..."
if ! docker version >/dev/null 2>&1 || \
   ! docker info >/dev/null 2>&1 || \
   ! docker compose version >/dev/null 2>&1 || \
   ! docker ps >/dev/null 2>&1; then
  echo "❌ ERROR: Docker daemon is unresponsive or failed to return status!"
  echo "------------------------------------------------------------"
  echo "OPERATOR REMEDIATION PLAYBOOK STEPS:"
  echo "1. Restart Docker Desktop: osascript -e 'quit app \"Docker\"' && open -a Docker"
  echo "2. If still unresponsive, remove backup settings: rm -f ~/Library/Group\ Containers/group.com.docker/settings-store.json.backup 2>/dev/null || true"
  echo "3. Run 'docker ps' to verify it is responsive before retrying."
  echo "------------------------------------------------------------"
  exit 1
fi
echo "Docker Daemon is healthy."

# 2. Build and Start Services
echo "Rebuilding and starting HAS services..."
docker compose build --pull=false has-api has-ui has-worker
bash scripts/docker_up.sh

# 2.5 Run Docker Role Separation Check
echo "Running Docker Role Separation Check..."
bash scripts/docker_role_separation_check.sh

# 3. Print Docker state
docker compose ps
echo "Fetching recent service logs..."
docker compose logs --tail=50

# 4. Run Pytest Suite inside tools container
echo "Running Python pytest suite inside has-tools container..."
docker compose run --rm has-tools uv run pytest tests/test_docker_files.py tests/unit/final_verifier/ tests/integration/test_final_verifier_runtime_truth.py tests/integration/test_zero_defect_runtime_truth_consistency.py

# 5. Run Playwright E2E Specs inside tools container
echo "Running Playwright E2E specs inside has-tools container..."
docker compose run --rm -e E2E_BASE_URL=http://has-ui has-tools npx playwright test tests/e2e/docker-visible-runtime-truth.spec.ts

# 6. Verify Docker UI/API Truth Check
echo "Running UI and API truth alignment checks..."
bash scripts/docker_truth_check.sh

echo "==> Docker-first Compliance Gate Completed Successfully."
exit 0
