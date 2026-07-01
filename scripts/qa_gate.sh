#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "Running Swarm QA Gate Regression Tests..."
echo "========================================="

echo "1. Checking Python Unit Tests..."
uv run pytest tests/unit/test_artifact_autonomy.py tests/unit/test_monetization_audit.py

echo "2. Checking Integration Tests..."
uv run pytest tests/integration/test_workflow_integration.py

echo "3. Running Playwright E2E Tests..."
npx playwright test tests/e2e/brain-autonomy.spec.ts

echo "========================================="
echo "QA Gate Result: PASS"
echo "========================================="
exit 0
