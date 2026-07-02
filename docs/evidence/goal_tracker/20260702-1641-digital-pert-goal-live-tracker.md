# Digital PERT /GOAL Live Tracker Evidence

* **Created At**: 2026-07-02T16:41:54-05:00
* **Goal**: Implement the Digital PERT Live Tracker for `/GOAL` into Moonshot UI and expose endpoints.

---

## Data Model & Calculations
* **File**: [pert_model.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/goal_tracker/pert_model.py)
* **API Endpoints**:
  - `GET /api/v1/goal/pert`
  - `POST /api/v1/goal/pert/recalculate`
  - `GET /api/v1/goal/live-tracker`
  - `GET /api/v1/goal/critical-path`

### Calculations Output Sample
```json
{
  "goal_id": "HAS-HASF-GOAL",
  "goal_name": "/GOAL",
  "north_star": "Complete HAS/HASF as an operational, verified, AI-assisted command system...",
  "status": "NO-GO",
  "final_verifier": "BLOCKED",
  "readiness_score": 50,
  "active_blocker": "NO_ACTIVE_RELEASE_GO",
  "critical_path": ["A", "E", "B", "D", "G", "H"],
  "expected_completion_minutes": 600.0,
  "confidence": "Medium-high"
}
```

---

## UI Integration
* **UI File**: [hoch_pods_liftoff.html](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/ui/hoch_pods_liftoff.html)
* **Section**: `DIGITAL PERT /GOAL TRACKER`
* **Displays**:
  - North Star card
  - GO/NO-GO status and active blocker
  - Expected completion (600 min) and confidence
  - Primary execution agent (HELM)
  - Next safe action
  - Horizontal critical path visualization chain
  - Table showing lanes, owners, PERT estimates, critical flags, evidence links, and commit refs.

---

## Test Verification

### Unit Tests
```bash
$ uv run pytest tests/unit/goal_tracker -v
tests/unit/goal_tracker/test_pert_model.py::test_pert_estimates_calculation PASSED
tests/unit/goal_tracker/test_pert_model.py::test_goal_pert_analysis PASSED
2 passed in 0.02s
```

### E2E Playwright Tests
```bash
$ npx playwright test tests/e2e/goal-pert-live-tracker.spec.ts --workers=1
Running 2 tests using 1 worker
  ✓  1 [antigravity-chromium] › tests/e2e/goal-pert-live-tracker.spec.ts:5:9 › 1. Verify /api/v1/goal/pert returns correct data model and formulas (14ms)
  ✓  2 [antigravity-chromium] › tests/e2e/goal-pert-live-tracker.spec.ts:31:9 › 2. Verify Moonshot UI displays DIGITAL PERT /GOAL TRACKER (4.6s)
2 passed (4.9s)
```

---

## Release Posture
* **Final Verifier Verdict**: `BLOCKED` (expected, due to active `NO_ACTIVE_RELEASE_GO`)
* **Fake Closeout Blocker**: PromptOps claim submission successfully blocked.
