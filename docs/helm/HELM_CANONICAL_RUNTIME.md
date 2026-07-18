# HELM Canonical Runtime — derived from the existing implementation

> Authored 2026-07-18 from a full read-only inventory (960 Python files). Every row
> is backed by code that exists today. The purpose is a single continuously-running
> runtime booted by `python helm.py`. **The problem was never missing capability —
> it was fragmentation** (competing implementations of the same subsystem, only one
> of which is actually wired/running).

## Entry point

`helm.py` (repo root) — the single front door. Reuses the proven pieces; reimplements none.
- `python helm.py` / `status` — verify-first, read-only runtime truth (no fake green).
- `python helm.py up` — idempotent supervisor for the founder-facing services (never
  double-spawns a service already served by launchd/autoloop).
- `python helm.py up --autonomous` — also runs the executive loop (gated: it *acts*).
- `python helm.py doctor` — diagnose the independent-observer CONTRADICTED gap.

## Canonical subsystem map (chosen from what exists)

| Required subsystem | CANONICAL implementation | Backing state | Duplicates to retire/converge |
|---|---|---|---|
| **Executive Loop** | `scripts/council/run_helm_council_daemon.py` (scheduler cycle + ConMon + QA sentinel + heartbeat) | `coordination/council/council_heartbeat.jsonl` | `helm_supervisor.py` (runs the *bare* scheduler, no ConMon/QA); `helm_goal_runner.py` (bounded build driver, not a daemon) |
| **Scheduler engine** | `backend/mission_control/persistent_scheduler.py::run_loop()` | `backend/swarm_ledger.db` → `mission_control_tasks` | — |
| **Mission Queue** | `mission_control_tasks` in `swarm_ledger.db` (what the scheduler dispatches) | `swarm_ledger.db` | `scripts/ag_execution_daemon.py`→`helm_task_queue.json`; `backend/brain/mission_queue.py`→`pert_tracker.json` |
| **Mission control object** | `backend/helm_runtime/{mission_store,transaction}.py` (OCC, versioned) | `coordination/goal/executive_mission.json` | `orchestration.task_queue` field (declared, never used) |
| **Dispatch choke point** | `scripts/council/gateway.py::CouncilDispatchGateway` → `spend_gate.py` (`subprocess.run`) | `coordination/council/relay/gateway_dispatch_ledger.jsonl` | `backend/dispatch/live_adapters.py`+`live_gateway.py` (real HTTP, dormant, stale model IDs) |
| **Routing / roles** | `backend/dispatch/{council_router,guarded_council}.py` + `helm_runtime/{capability_registry,provider_router}.py` | `coordination/governance/{role_bindings,capability_registry}.json` | `scripts/council/dispatch.py::CouncilRouter` (overlapping); `scripts/council/{adapters,registry,harness}.py` (obsolete precursors) |
| **Event Bus** | `backend/helm_runtime/event_bus.py` (append-only, fsync) | `coordination/events/helm_events.jsonl` | `backend/runtime_process.py::RuntimeProcessBus`; `backend/detection_events.py::DetectionEventBus` |
| **Governance** | `backend/helm_runtime/{governance_engine,governed_emit,role_router}.py` (fail-closed gate + Proof Record) | `helm_events.jsonl` | — |
| **Memory** | *(no canonical winner)* `knowledge_engine.py` is retrieval-only (no persistence) | `docs/helm`, `docs/evidence`, `coordination/goal` | `DoctrineMemory`, `LessonMemory`, `data/prompt_brain/*` (fragmented, none wired to knowledge_engine) |
| **Mission Control UI** | `backend/helm_live_api.py` (:8770 TLS) — `/founder`, `/overview`, `/council` | `frontend_live/*.html` | `backend/pert_server.py` (:8765, duplicate PERT); `has_live_project_tracker` (:3001, **dead** — plist points at a nonexistent `server.js`) |
| **Control API / shell** | `backend/main.py` (:8000, launchd-supervised) | `frontend/dist` | — |
| **Bridge (role door)** | `backend/helm_runtime/bridge_api.py` (mounted into both APIs) | `executive_mission.json` | — |
| **Independent observer** | `backend/jspace/` (HJOS) → `coordination/jspace/health.json` | jspace ledgers | — |
| **Verification** | `scripts/helm_fire_verification.py` (Grok audit + OCC replay proof, founder-gated) | `docs/evidence/audit/…` | — |
| **Providers (live, $0 default)** | local Ollama (subprocess) + Grok CLI; `metered_api_allowed:false` | `gateway_policy.json` | HTTP `live_adapters` path (gated off) |
| **Factories** | product: `factory_registry.json` + scheduler; brain: `backend/factory/registry.py` + `backend/brain_convergence/`; cyber: `backend/swarm/cyber_swarm.py` | `data/prompt_brain/*`, `products/*` | — |

## Honest runtime state (2026-07-18)

- **Model dispatch is proven live today** — `gateway_dispatch_ledger.jsonl` shows `COMPLETED`
  dispatches for local Ollama and Grok CLI at 18:27, fail-closed and $0-default.
- **The executive loop is NOT running** — last `council_heartbeat.jsonl` entry is
  2026-07-15 cycle 506, `state=ERROR: "database is locked"` (SQLite contention killed it).
- **The runtime is NOT verified-clean** — HJOS `health.json` = `CONTRADICTED /
  WITHHOLD_PROMOTION`, ~9,000+ unresolved findings, a canonical lease-ledger pointer that
  the running components don't satisfy. `helm_pert.json` says `GOAL_HELM: DONE`; the live
  observer contradicts that. **NO FAKE GREEN: the observer wins.**

## Critical path to "verified-clean continuously-running HELM"

1. **Close the CONTRADICTED gap** — reconcile the observer's canonical lease/dispatch
   ledger pointer with the `evidence_dir` the live scheduler writes to
   (`persistent_scheduler.py`); resolve or triage the finding backlog. *Do not suppress.*
2. **Fix the `database is locked` failure** — the loop must survive SQLite contention
   (WAL + busy_timeout on the scheduler's writes, as `start_has_runtime.sh` already does).
3. **Wire `python helm.py up` as the one supervisor** — retire the scattered
   `helm_autoloop.sh` / `helm_supervisor.py` / plist duplication onto one entry point
   *(founder-gated: touches OS supervision)*.
4. **Converge duplicates** — one mission queue, one event-bus stream, one memory store.

Founder-only gates (unchanged, never auto-crossed): Apple review, spend, credentials,
production deploy, code signing, external submissions.
