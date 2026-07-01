# Merge and Package Readiness Ledger — rc30-merge-package-readiness

This ledger documents the complete release readiness and code-provenance baseline for the Swarm Relay & Computing feature set spanning **RC25 to RC29**.

---

## 1. Release Identification
- **Release Branch:** `rc30-merge-package-readiness` (fast-forward candidate to `master`)
- **Base Branch / Commit:** `master` / base of `rc25-local-model-routing-and-agent-execution-observability`
- **Sealing SHA:** `67b6b990b7a8684bb41e974de4810ee307d8ffeb` (head of RC29)
- **Validation Run:** `scripts/rc29_release_verify.sh`
- **Status:** **READY TO MERGE**

---

## 2. Combined Code Statistics

The total diff of modified files from the RC25 base (`2c2c620`) to the HEAD of this release readiness package represents **1,948 lines** of code, tests, configs, and evidence across **17 files**:

```
 backend/capability_router.py                       |   9 +-
 backend/main.py                                    |  55 ++++
 backend/relay_worker_adapter.py                    | 213 +++++++++++++++
 config/cluster_worker_profiles.json                |  59 +++++
 config/relay_routing_policy.json                   |  24 ++
 .../compute/rc26-relay-routing-integration.md      | 148 +++++++++++
 .../evidence/compute/rc27-doctrine-db-migration.md | 153 +++++++++++
 .../compute/rc28-mission-execution-proof.md        | 153 +++++++++++
 .../evidence/compute/rc29-release-consolidation.md | 108 ++++++++
 docs/release/rc29-release-ledger.md                |  66 +++++
 has_live_project_tracker/data/status.json          |  21 ++
 playwright.config.ts                               |   4 +-
 scripts/rc29_release_verify.sh                     | 110 ++++++++
 scripts/seed_relay_accountability.py               | 211 +++++++++++++++
 scripts/verify_doctrine_db.py                      | 138 ++++++++++
 tests/e2e/rc26-relay-routing.spec.ts               | 191 ++++++++++++++
 tests/e2e/rc28-mission-execution-proof.spec.ts     | 287 +++++++++++++++++++++
 17 files changed, 1948 insertions(+), 2 deletions(-)
```

---

## 3. Scope of Feature Deliverables

### Core Framework Adapters
- `backend/relay_worker_adapter.py`: Pure Python worker client proxying registry and health requests to the Tailscale VPS relay. Implements strict `UNKNOWN` recovery on exceptions to ensure no fake telemetry.
- `backend/capability_router.py` & `config/relay_routing_policy.json`: Mapped routing capability so `relay`, `heartbeat`, and `relay_forward` tasks get routed to `RELAY-001`. Enforces fallback to `L1` (local) on routing failure.
- `backend/main.py`: Created proxy endpoints (`/api/v1/relay/health`, `/api/v1/relay/registry`, `/api/v1/relay/status`) to shield raw VPS Tailscale IP address from the UI. Wired `init_brain_tables()` at module load time to fix the database startup gap.

### Operational Seeding and Registry
- `has_live_project_tracker/data/status.json`: Registered the relay node inside `relay_workers` key to prevent UI overwrite cycles.
- `scripts/seed_relay_accountability.py`: Idempotent SQLite script inserting `HAS-WORKER-RELAY-001` at baseline score 80 (GOLD/Trusted Autonomous).
- `config/cluster_worker_profiles.json`: Profile properties including routing priority and hardware configuration bounds.

### Verification Tools and E2E Tests
- `scripts/verify_doctrine_db.py`: Probes and asserts schema completeness for `doctrine_rules`.
- `scripts/rc29_release_verify.sh`: Script executing all tests, probes, and dirty checks in a single workflow.
- `tests/e2e/rc26-relay-routing.spec.ts` & `tests/e2e/rc28-mission-execution-proof.spec.ts`: Playwright suites verifying proxy contract bounds, public port closed state, DB mission registration, and trust updates.

---

## 4. Constraint Check Matrix

| Security / Design Rule | Checked Posture | Status |
|------------------------|-----------------|--------|
| **Public Port Isolation** | Port 3012 tested from public eth0 interface. Safe connection timeout. | **SECURE** |
| **No Secrets Committed** | Secrets/credentials avoided in commit index. Database and user preferences untracked. | **SECURE** |
| **No Fake Telemetry** | Default state is `UNKNOWN` when the VPS relay is offline. No forced `PASS` or synthesised states. | **COMPLIANT** |
| **Additive Relay Only** | Local runtime computing (`L1`) remains primary node and default fallback. | **COMPLIANT** |
| **Doctrine Init Fixed** | Startup sequence database initialized before orchestrator import. No startup warnings. | **RESOLVED** |

---

## 5. Merging and Packaging Proposal

It is recommended to merge the `rc30-merge-package-readiness` branch into `master` using a fast-forward or squash strategy.

### Proposed Annotated Tag Command
```bash
git tag -a v0.1.7 -m "Release v0.1.7: Swarm Relay & Computing Core Node Integration"
```
*(Do not run this command; it is presented here for operator review only.)*
