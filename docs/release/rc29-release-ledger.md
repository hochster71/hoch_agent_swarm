# Release Validation Ledger — rc29-release-consolidation (RC25–RC28)

This document serves as the formal release validation evidence ledger for the consolidated **RC25 to RC28** Swarm Relay & Computing feature set.

---

## 1. Release Metadata
- **Consolidation Branch:** `rc29-release-consolidation`
- **Base Branch:** `master`
- **Sealing Commit SHA:** `6f52024220b229864295beee3694f4c803dfa1bd` (head of RC28)
- **Validation Date:** 2026-07-01
- **CI & E2E Verdict:** **PASS (GO)**

---

## 2. Included Deliverables & Features

### RC25: HOCH-200 Base VPS Foundation
- Deployed a secure, hardened Ubuntu VPS (`hoch-relay-001`) with UFW restricting OpenSSH access to home source IP `99.22.37.25`.
- Configured isolated Docker Compose stack binding port 3012 strictly to Tailscale IP `100.87.18.15` (blocking public access).
- Created VPS diagnostics and verification scripts.

### RC26: Swarm Capability Routing Integration
- Created the `backend/relay_worker_adapter.py` module to proxy VPS health and registry checks over Tailscale.
- Extended the `backend/capability_router.py` logic to assign task types `relay_forward`, `heartbeat`, and `relay` to node `RELAY-001`.
- Added the VPS relay node profile in `config/cluster_worker_profiles.json` and registered the worker status card in tracker `status.json`.
- Implemented `scripts/seed_relay_accountability.py` to seed `HAS-WORKER-RELAY-001` with an initial trust score of 80 (GOLD / Tier 4: Trusted Autonomous).

### RC27: Doctrine DB Schema Fix
- Resolved the module-level database initialization gap by ensuring `init_brain_tables()` is called before `BrainOrchestrator` is instantiated at import-time.
- Verified that 74 rules are synced successfully from the YAML doctrine files to the `doctrine_rules` SQLite table without errors.

### RC28: Mission Execution Proof
- Implemented and ran Playwright test suite verifying real mission intake (registering a mission and tasks in `mission_control_missions` and `mission_control_tasks` databases) on the local backend.
- Verified accountability score updates and ledger logging endpoints.

---

## 3. Playwright Test Reports Summary

| Test File | Describes | Tests Passed | Status |
|-----------|-----------|:------------:|:------:|
| `tests/e2e/hoch200-compute-setup.spec.ts` | HOCH-200 VPS stack deployment verification | 26 / 26 | **PASS** |
| `tests/e2e/rc26-relay-routing.spec.ts` | Relay proxy routing and isolation invariants | 13 / 13 | **PASS** |
| `tests/e2e/rc28-mission-execution-proof.spec.ts` | End-to-end mission registration and accountability | 16 / 16 | **PASS** |

---

## 4. Security & Hard Constraints Status

### Public Port Closure (Port 3012)
- Checked via socket connect to VPS public IP `50.116.41.183`. The connection timed out successfully. Port is strictly closed to public incoming traffic.

### Telemetry & Synthesis Integrity
- Tested to ensure health endpoints default to `UNKNOWN` on network failure, preventing artificial `ONLINE` status generation.

### Secrets Protection
- Swarm ledger DB and tracker logs are correctly listed in `.gitignore` to prevent secret/artifact leaks. No API keys are hardcoded in the codebase.

---

## 5. Final Recommendation

**GO**

The release consolidation is fully verified and clean. Master branch merge is authorized.
