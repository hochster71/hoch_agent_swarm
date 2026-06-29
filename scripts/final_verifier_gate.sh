#!/bin/bash
set -e

echo "==> Running Build Gate..."
npm run build

echo "==> Running Pytest Suite..."
uv run pytest tests/unit/ tests/integration/ -vv

echo "==> Restoring database state via collection pass..."
curl -s -X POST http://127.0.0.1:8000/api/v1/runtime-truth/collect > /dev/null

echo "==> Running Playwright E2E Specs..."
npx playwright test

echo "==> Running Anti-Fake Gate..."
bash scripts/anti_fake_gate.sh

echo "==> Running Hardcoded Status Scan..."
bash scripts/scan_hardcoded_status.sh

echo "==> Running Meta-Orchestrator Gates..."
bash scripts/meta_orchestrator_gates.sh

echo "==> Evaluating Final Verifier Verdict..."
VERDICT_RES=$(curl -s http://127.0.0.1:8000/api/v1/final-verifier/verdict)
STATUS=$(echo "$VERDICT_RES" | grep -o '"status":"[^"]*' | grep -o '[^"]*$')
CONTRAD_COUNT=$(echo "$VERDICT_RES" | grep -o '"contradiction_checker":{[^}]*}' | grep -o '"violations":\[[^\]]*\]' | grep -o '"violations":\[\]' | wc -l)

echo "  [final_verifier]: Status: $STATUS"
if [ "$STATUS" = "BLOCKED" ]; then
    echo "ERROR: final_verifier failed: release is BLOCKED by outstanding gaps, contradictions, or unowned defects!"
    exit 1
fi

echo "SUCCESS: Final Verifier Gates passed successfully."
