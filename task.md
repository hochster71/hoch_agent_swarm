# Task List — Device-as-a-Service Registry

- `[x]` Define SQLite tables in `init_execution_store_tables()` and write database helper functions
- `[x]` Create `backend/device_discovery.py` containing mDNS, neighbor table scanners, and fingerprint/classification rules
- `[x]` Create `backend/service_registry.py` containing approve/reject controllers
- `[x]` Update `backend/cluster_manager.py` to dynamically load approved service nodes
- `[x]` Add Pydantic schemas and REST routes in `backend/main.py`
- `[x]` Create discovery fixtures in `tests/fixtures/device-discovery-fixtures.json`
- `[x]` Add DaaS panels and safety disclaimers to `frontend/index.html`
- `[x]` Implement DaaS event handlers and list renderers in `frontend/app.js`
- `[x]` Create contract validation script `scripts/qa/test-device-service-registry-contract.ts`
- `[x]` Create Playwright E2E test `tests/e2e/device-service-registry.spec.ts`
- `[x]` Register script commands in `package.json`
- `[x]` Rebuild assets, run QA contract checks, and execute Playwright E2E tests
- `[x]` Update documentation: deep-swarm-page-audit-report.md, walkthrough.md, and task.md
