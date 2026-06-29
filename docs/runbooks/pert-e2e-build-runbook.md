# Operations Runbook: PERT E2E Build Orchestration

## 1. Running the E2E Build
To run the automated E2E build orchestrator script and verify all 8 validation gates:
```bash
bash scripts/pert_e2e_build.sh
```

---

## 2. Gate Verification & Failures
If any gate returns a status of **FAIL**:
- **Gate 1 (App Build)**: Run `npm run build --prefix frontend` manually to trace compile errors.
- **Gate 2 (UI Render)**: Check that `index.html` has no duplicate IDs or unclosed tags.
- **Gate 3 (E2E Tests)**: Run `npx playwright test tests/e2e/pert-e2e-build.spec.ts --ui` to trace browser test failures.
- **Gate 4 (Docker Config)**: Run `docker compose config` to print syntax errors in config YAMLs.
- **Gate 5 (Runtime)**: Verify `redis` queue and API services are online.
- **Gate 8 (GO/NO-GO)**: Verify that no P0 gaps exist, monthly VPS costs are under $100, and agent limiters are active.

---

## 3. Rollback Procedure
If a release fails at the commit gate:
1. Revert changes to source files:
   `git checkout HEAD -- backend/main.py frontend/index.html frontend/app.js`
2. Remove any untracked PERT files:
   `rm -f frontend/data/pert_tracker.json scripts/pert_e2e_build.sh tests/e2e/pert-e2e-build.spec.ts`
