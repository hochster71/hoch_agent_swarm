# RC29 — Release Consolidation for Swarm Relay & Computing (RC25–RC28)

**Epic:** HOCH-200  
**RC:** RC29  
**Branch:** `rc29-release-consolidation`  
**Date:** 2026-07-01  
**Author:** automated (antigravity/RC29)

---

## 1. Executive Summary

This document serves as the final **Release Consolidation** validation and check ledger for the sequence of Release Candidates spanning **RC25 to RC28**. 

Over these iterations, we successfully designed, deployed, and verified a hardened, Tailscale-isolated VPS relay stack (`hoch-relay-001`), integrated it into existing HAS/HASF swarm capability routing and observability policies, fixed the module-level doctrine initialization gap, and verified E2E mission execution and accountability recording.

All safety, security, and architectural constraints have been fully met:
- **Port 3012** remains strictly closed to the public internet (eth0).
- **Tailscale connectivity** is the sole ingress channel for the relay worker API and dashboard.
- **Local runtime** remains the primary computing node; the relay stack is additive.
- **Doctrine startup logs** are clean (no `"no such table: doctrine_rules"` errors).
- **No secrets or credentials** are printed, stored, or committed.
- **No fake data or synthesized statuses** are used; the state defaults strictly to `UNKNOWN` when the live relay is unreachable.

---

## 2. Release Ancestry and Commit Ledger

The branches are stacked sequentially from the parent down:

```
master 
  └── rc25-local-model-routing-and-agent-execution-observability
        └── rc26-has-hasf-relay-routing
              └── rc27-doctrine-db-migration-and-mission-execution-proof
                    └── rc28-mission-execution-proof
                          └── rc29-release-consolidation (Current)
```

### Commit Breakdown by Release Candidate

#### RC25 — Local Model Routing & HOCH-200 VPS Setup
* `b3e1544` Add HOCH-200 relay compute foundation
* `61069cf` Document HOCH-200 SSH hardening
* `2c2c620` test: include HOCH-200 compute setup E2E in Playwright config

#### RC26 — HAS/HASF Relay Routing Integration
* `b64e405` feat(rc26): add relay worker adapter module
* `1f21062` feat(rc26): add relay routing policy and extend capability router
* `978b1f5` feat(rc26): add relay backend proxy endpoints
* `a2a8ebe` feat(rc26): seed relay worker into tracker status.json
* `2ff7840` feat(rc26): add accountability seed script for relay worker
* `b878d65` feat(rc26): add RC26 relay routing evidence document
* `2f83e46` test(rc26): add Playwright relay routing integration tests
* `2e20495` test(rc26): include relay routing E2E in Playwright config
* `5e69ffa` fix(rc26): use valid accountability database connection for relay seed

#### RC27 — Doctrine DB Migration
* `41f4bca` fix(rc27): call init_brain_tables before BrainOrchestrator instantiation
* `619b4e6` feat(rc27): add doctrine DB verification script
* `3a54249` feat(rc27): add RC27 doctrine DB migration evidence document

#### RC28 — Mission Execution Proof
* `d8c26d9` feat(rc28): add mission execution proof Playwright suite
* `68c8a95` chore(rc28): register rc28 spec in playwright testMatch
* `6f52024` feat(rc28): add mission execution proof evidence document

---

## 3. Consolidation Gate Checklist

| Release Candidate / Gate | Verification Check | Status | Verification Detail |
|-------------------------|--------------------|--------|---------------------|
| **RC25** | VPS base state & SSH hardening | **PASS** | SSH restricted to home IP (`99.22.37.25`), UFW active |
| | Port 3012 public isolation | **PASS** | Python socket timeout probe to VPS eth0:3012 is refused |
| **RC26** | Relay adapter & proxying | **PASS** | Endpoints live-proxied. Returns `UNKNOWN` on failure, no fake telemetry |
| | Capability router integration | **PASS** | Routes `relay_forward/heartbeat/relay` tasks to `RELAY-001` |
| | Accountability seeding | **PASS** | `HAS-WORKER-RELAY-001` seeded at score 80 (GOLD/Trusted Autonomous) |
| **RC27** | doctrine_rules initialization | **PASS** | `init_brain_tables()` runs before orchestration imports. Table has 74 rows |
| | Idempotency of schema | **PASS** | Verification script confirms no duplicate creation or data loss |
| **RC28** | Mission write & read roundtrip | **PASS** | Mission intake on `ops` pod inserts 2 tasks, reads back successfully |
| | E2E Playwright verification | **PASS** | 16/16 tests pass |
| | RC26 regression check | **PASS** | 13/13 tests pass |

---

## 4. Repeatable Verification Run Report

The verification runner `scripts/rc29_release_verify.sh` was executed against the localhost backend:

- **Check 1: Doctrine DB Table Verification** — **PASS**
  - Path: `backend/swarm_ledger.db`
  - Rules found: 74
  - Table: `doctrine_rules` exists with expected schema and columns
- **Check 2: RC26 Playwright E2E Regression Suite** — **PASS**
  - Total: 13 passed / 0 failed (including public port verification)
- **Check 3: RC28 Playwright E2E Mission Proof Suite** — **PASS**
  - Total: 16 passed / 0 failed (including R/A access permissions and real DB intake checks)
- **Check 4: Port 3012 Public Exposure Probe** — **PASS**
  - Status: `socket.connect((50.116.41.183, 3012))` timed out (Connection is safely dropped by VPS firewall)

---

## 5. Recommendation

**GO FOR MERGE**

All automated and manual security verification gates for the HOCH-200 relay stack and Swarm Computing pipeline are fully satisfied. The release branches are consolidated and ready for main master promotion.
