# Technical Report — HELM OMEGA ASSURANCE AUDIT v1.0

**Commit:** `2db7e0de` · **Branch:** `helm/h1b-r2-remediation` · **Date:** 2026-07-17 UTC

---

## 1. Repository Integrity (Phase 1)

### 1.1 Structure (observed)

Top-level operational surface (non-exhaustive):

| Path | Role (observed) |
|---|---|
| `backend/` | Primary Python control plane (395 py files under backend; 2464 functions sampled) |
| `frontend/`, `frontend_live/` | UI surfaces |
| `scripts/` | Goal engine, validation, deploy guards, refresher |
| `coordination/` | Runtime ledgers, goal state, council, founder, security posture |
| `products/`, `hsf/` | Factory product code |
| `has_live_project_tracker/` | Live tracker data + UI |
| `artifacts/` | Evidence packages (includes 11k+ factory artifacts) |
| `docs/` | Documentation (≈29k markdown files repo-wide) |
| `tests/` | Unit/e2e suites |
| `control/` | Authority policy, phase registry |
| `deploy/`, `k8s/`, `systemd/`, Dockerfiles | Packaging / ops |
| `_quarantine/` | Quarantined corrupt/stale artifacts |

### 1.2 Scale metrics (measured)

| Metric | Value | Evidence |
|---|---:|---|
| Python files (excl. venv/node/pyc) | 925 | `find` count |
| Markdown files | 29,436 | `find` count |
| JSON files | 7,546 | `find` count |
| FastAPI paths on `:8000` | 663 | live OpenAPI |
| FastAPI paths on `:8770` (HELM LIVE) | 68 | live OpenAPI |
| PERT server paths `:8765` | 16 | live OpenAPI |
| Dirty git paths | 289 | `git status --porcelain` |
| Backend mean cyclomatic complexity | 4.56 | AST heuristic |
| Backend functions with CC ≥ 25 | 43 | AST heuristic |
| Highest CC observed | 194 (`backend/pert_server.py:get_pert_data`) | AST |

### 1.3 Architecture consistency

**Finding A1 — Multiple concurrent “control planes.”**  
Runtime has simultaneous listeners:

| Port | Process (sample) | Role |
|---:|---|---|
| 8000 | `uvicorn backend.main:app` | Large HAS API |
| 8770 | `uvicorn backend.helm_live_api:app` (TLS) | HELM LIVE |
| 8765 | `uvicorn backend.pert_server:app` | PERT command center |
| 8788 | node/vite | Frontend dev |
| 8789 | node | Separate node service (root 404) |
| Others | 8010, 8080, 8777, 8797, 8810–8830, 8898–8899 | Assorted agents/services |

**Implication:** “Single authoritative runtime” is **not** established at the process topology layer. Mission consumers that hit the wrong port get different surfaces (e.g. `/api/mission/state` 404 on `:8000` vs `/api/v1/helm/mission` 200 on `:8770`).

### 1.4 Branch consistency

- Active branch: `helm/h1b-r2-remediation` (not `master`).
- Large branch zoo present (rc19–rc42, auth/*, integration/*).
- Working tree **not clean** — reproducibility of “what is running” vs “what is committed” is **degraded**.

### 1.5 Documentation staleness

| Doc | mtime (local) | vs runtime |
|---|---|---|
| `README.md` | 2026-06-28 | STALE |
| `HOCH_STATUS.md` | 2026-07-07 | STALE (claims Epic Fury NO-GO/local:3003; mission state newer) |
| `coordination/coordination_bus.json` heartbeats | 2026-07-09 | STALE vs “ONLINE” labels |
| `docs/founder/FACTORY_READINESS_BOARD.md` | 2026-07-17 | FRESH (generated) |
| `coordination/goal/mission_state.json` | 2026-07-17 | FRESH |

### 1.6 Dead / orphaned / duplicate logic

| Class | Observation | Status |
|---|---|---|
| Dead code | Not fully static-analyzed repo-wide; 43 high-CC functions indicate concentration of risk | **NOT FULLY VERIFIED** |
| Orphaned | `_quarantine/` retains corrupt DBs and lock residue; large `artifacts/factory` corpus | **PRESENT** |
| Duplicate readiness | factory_registry READY vs readiness board rungs vs products-on-disk | **CONFIRMED CONFLICT** |
| Circular deps | Not proven via full import graph this audit | **UNKNOWN** |

### 1.7 Build reproducibility

| Check | Result |
|---|---|
| Clean checkout identity | FAIL — 289 dirty paths |
| Lockfiles present | `uv.lock`, `package-lock.json` present |
| Deterministic “HELM binary” | NOT OBSERVED — multi-process LaunchAgent swarm |
| Container path | Dockerfiles present; primary runtime is macOS LaunchAgents | PARTIAL |

### Repository Health Score: **42 / 100**

Rationale: enormous capability surface and intentional evidence culture, undermined by dirty tree, dual APIs, stale docs, and readiness narrative conflict.

---

## 2. Architecture Graph (simplified, evidence-backed)

```
                    ┌─────────────────────────────┐
                    │  Founder (DOORSTEP gates)   │
                    └──────────────┬──────────────┘
                                   │ token / biometric / --go
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   coordination/founder     control/authority_policy   deploy scripts
          │                        │                        │
          ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ goal_engine.py   │───▶│ mission_state.py │◀───│ runtime_refresher │
│ goal_state.json  │    │ mission_state.jsn│    │ helm_autoloop     │
└──────────────────┘    └────────┬─────────┘    └──────────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
   helm_live_api:8770     voice router/briefing    (intended) dashboards
   /api/v1/helm/mission   write_mission_state()
           │
           ▼
   factories (HASF/HSF/HMF/HRF/HCF/HFF/HHF/HPF)
   products/*  +  hsf/deploy  +  external Vercel
```

**NOT a single kernel.** HELM behaves as a **federated control plane** over files + multiple uvicorn apps + LaunchAgents.

---

## 3. Dependency Graph (runtime services)

```
LaunchAgents (com.hoch.*)
  ├─ com.hoch.api.server          → :8000 backend.main
  ├─ com.hoch.* (helm live)       → :8770 backend.helm_live_api (observed)
  ├─ com.hoch.has.pert-server     → :8765 pert_server
  ├─ com.hoch.runtime.refresher   → scripts/runtime_refresher.py
  ├─ com.hoch.goal.runtime.loop   → goal loop
  ├─ com.hoch.daemon              → cadence
  ├─ com.hoch.liveness-producer   → factory registry refresh
  └─ mesh / family / widget / tracker agents

Model backends (gateway live probe 2026-07-17)
  ├─ lmstudio 127.0.0.1:1234  ALIVE (gemma-4-12b-qat)
  ├─ mac-local ollama         present in gateway status
  └─ relay / tailscale paths  declared in HOCH_STATUS (age-stale doc)

External
  ├─ Vercel product URLs (Story Studio, Epic Fury) — HTTP 200 homepage probes in readiness board
  ├─ Stripe — pending txn in revenue ledger
  └─ App Store Connect — UNVERIFIED
```

---

## 4. Dead Code / Complexity Report (sample)

### High complexity hotspots (CC ≥ 40, backend AST)

| CC | File | Function |
|---:|---|---|
| 194 | `backend/pert_server.py` | `get_pert_data` |
| 134 | `backend/instrument_integrity/h1c_activation.py` | `compute_h1c_truth` |
| 82 | `backend/evidence_graph.py` | `build_evidence_graph` |
| 81 | `backend/voice/briefing.py` | `execute_voice_command` |
| 68 | `backend/instrument_integrity/council_router.py` | `get_council_state` |
| 63 | `backend/runtime_truth/collector.py` | `collect_and_store_all` |
| 61 | `backend/helm_live_api.py` | `api_v1_agents` |
| 57 | `backend/mission_control/mission_state.py` | `build_mission_state` |

**Interpretation:** Complexity is concentrated in truth aggregation and voice/PERT surfaces — high blast radius for correctness bugs.

### Dead code

Full unreachable-code analysis **not executed** (tooling timeboxed). Status: **UNKNOWN (not proven clean)**.

---

## 5. Executive OS Capability Matrix (Phase 8)

| Capability | Code present? | Runtime proven? | Verdict |
|---|---|---|---|
| Mission intake | Partial (goal requirements, factories intake schemas) | Partial | PARTIAL |
| Planning | Goal engine + PERT server | Live PERT OpenAPI | PARTIAL |
| Scheduling | PersistentScheduler, leases, soak packages | Mixed PASS/FAIL soak | PARTIAL |
| PERT / critical path | `pert_server`, goal critical path fields | Live `:8765` | PARTIAL |
| Resource allocation | Budgets in factory registry; spend ledger | Spend rows exist | PARTIAL |
| Execution | Adapters, AG runner, product engines | Some product tests; champion blocked | PARTIAL |
| Monitoring | Conmon, freshness refresher, heartbeats | Some live; many stale files | PARTIAL |
| Evidence | Ledgers, seal_verdict, SHA256SUMS (51 packages) | Mixed integrity history | PARTIAL |
| Learning | Prompt brain / outcome ledgers | Present; not fully TEVV’d | PARTIAL |
| Closeout | Doorstep packages | Founder pending | NOT COMPLETE |
| Historical replay | Seal packages + forensics dirs | Some; superseded packs invalid | PARTIAL |
| Crash recovery | Fencing tokens; SIGKILL proof claims | CP-10 evidence cited; not re-run this audit | PARTIAL / NOT RE-PROVEN |
| Idempotency | Stripe webhook tests exist | Product-level | PARTIAL |
| Rollback | Quarantine/rollback tests (jspace) | Unit-level | PARTIAL |
| Checkpointing | Soak/state files | Not OS-grade proven | UNKNOWN |

**Executive OS verdict: NOT PROVEN as complete OS.** Best description: **mission-aware control plane with partial lifecycle coverage**.
