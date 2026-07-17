# Runtime Freshness Service — Evidence

- **Authored (UTC):** 2026-07-16T16:15:24Z
- **Author:** freshness subagent (HELM swarm)
- **Goal:** Make the HELM UIs "always current or honestly stale." Replace the blanket
  24h (`fresh = "FRESH" if age < 86400 else "STALE"`) window in `backend/helm_live_api.py`
  (~line 192) with TIGHT, per-signal budgets that yield **FRESH / STALE / UNKNOWN** so
  panels can badge/grey correctly.
- **Soak safety:** NOTHING was restarted. No daemon/launchd/uvicorn touched; no mission
  dispatch; `backend.main` / `helm_live_api` untouched. The live 24h Phase C soak was
  **not disturbed** — it was only READ (last-line `at`) to compute freshness. All state
  files were read-only.

## What was built (NEW files only)

| File | Purpose |
|---|---|
| `backend/runtime_freshness.py` | Pure-stdlib, read-only freshness engine: `FRESHNESS_BUDGETS`, `SIGNAL_SPECS`, `evaluate_signal`, `evaluate_all`, `render_board`, and `__main__` so it runs standalone with no server. |
| `backend/runtime_freshness_api.py` | Ready-to-mount FastAPI `APIRouter` exposing `GET /api/v1/helm/freshness` → `evaluate_all()`. **Deliberately NOT wired** into the running app. |
| `tests/test_runtime_freshness.py` | 11 tests, tmp-file only — never touches real state. |
| this doc | Evidence. |

## Per-signal budgets + justification

Each budget is tied to how often the producer actually rewrites the file. All are far
tighter than the old 86400s blanket; a signal is FRESH only while `age <= budget`.

| Signal | Source | Budget | Justification |
|---|---|---:|---|
| `control_plane` | `has_live_project_tracker/data/control_plane_status.json` | **120s** | Sidecar self-rebuilds ~30s TTL; file declares `max_age_seconds=60`. 120s = 2× its own contract. |
| `supervisor_heartbeat` | `.../helm_supervisor_heartbeat.json` | **300s** | Heartbeat should tick continuously; 5 min flags a quiet supervisor without alerting on one skipped beat. |
| `orchestration_authority` | `.../orchestration_bridge_control.json` | **600s** | The file's OWN `max_age` is 600s; we mirror it so our badge agrees with the runtime's own staleness contract. (No whole-file timestamp field → aged by real file mtime.) |
| `helm_runtime_state` | `.../helm_runtime_state.json` | **600s** | Polled on the supervisor loop; matches authority cadence; catches a frozen runtime loop. |
| `helm_agent_registry` | `.../helm_agent_registry.json` | **1800s** | Registry changes rarely, but 24h is absurd (it silently went **73h** stale). 30 min is generous yet surfaces a stopped factory-rebuild pipeline. |
| `goal_state` | `coordination/goal/goal_state.json` | **3600s** | Recomputed ~hourly (`computed_at`). |
| `mission_state` | `coordination/goal/mission_state.json` | **3600s** | Shares the goal recompute cadence. |
| `runtime_truth_snapshot` | newest `.../HELM-SOAK-24H-*/runtime_truth_snapshots.jsonl` (last-line `at`) | **300s** | Live soak writes snapshots frequently; 5 min proves the soak is advancing, not frozen. |

**Timestamp resolution:** prefer an explicit in-file field (`as_of`, `computed_at`,
`timestamp`, `last_checked`, `at`, …), else fall back to the real file **mtime**
(tz-independent epoch). Missing / empty / unparseable / no-usable-timestamp → **UNKNOWN**
(never invented FRESH). **Overall = worst of all signals** (UNKNOWN > STALE > FRESH).

## Real test output

```
$ python3 -m pytest tests/test_runtime_freshness.py -q
...........                                                              [100%]
11 passed in 0.16s
```

Covered: FRESH within budget, STALE past budget, UNKNOWN when missing, UNKNOWN when
source unreadable, mtime fallback ages honestly (no invented FRESH), jsonl last-line
timestamp, **per-signal budget** (same source/age → STALE under a tight budget, FRESH
under a loose one), overall = worst, all-fresh → FRESH, board renders, and a regression
guard that no budget equals the old 86400s blanket.

## Real freshness board — current system (READ-ONLY snapshot)

```
$ python3 -m backend.runtime_freshness
HELM RUNTIME FRESHNESS BOARD
evaluated_at: 2026-07-16T16:15:17.530818Z
OVERALL: STALE   (FRESH=1 STALE=7 UNKNOWN=0)
------------------------------------------------------------------------------
[STALE]   control_plane            age=   52477s / budget=120s  :: age 52477s exceeds budget 120s
[STALE]   supervisor_heartbeat     age=  158843s / budget=300s  :: age 158843s exceeds budget 300s
[STALE]   orchestration_authority  age=  157822s / budget=600s  :: age 157822s exceeds budget 600s
[STALE]   helm_runtime_state       age=  271644s / budget=600s  :: age 271644s exceeds budget 600s
[STALE]   helm_agent_registry      age=  271644s / budget=1800s  :: age 271644s exceeds budget 1800s
[STALE]   goal_state               age=    9809s / budget=3600s  :: age 9809s exceeds budget 3600s
[STALE]   mission_state            age=    9809s / budget=3600s  :: age 9809s exceeds budget 3600s
[FRESH]   runtime_truth_snapshot   age=      30s / budget=300s  :: age 30s within budget 300s
------------------------------------------------------------------------------
```

**Reading of the snapshot (honest):** Only the live **soak snapshot is FRESH** (30s) —
the Phase C soak IS advancing. Everything else is genuinely STALE against its tight
budget: the control-plane sidecar has not rebuilt in ~14.6h, the supervisor heartbeat is
~44h old, orchestration authority ~43.8h, runtime state + factory registry ~75.5h, and
goal/mission state ~2.7h (past their 1h recompute budget). Under the OLD blanket 24h rule,
goal_state, mission_state, and control_plane would all still have badged **FRESH** — this
is exactly the false-green the tight budgets now catch.

## Exact ONE-LINE wiring (for the next SAFE restart — do NOT apply during the soak)

In the app that owns `/api/v1/helm/*` (`backend/helm_live_api.py`, or `backend/main.py`):

```python
from backend.runtime_freshness_api import router as freshness_router
app.include_router(freshness_router)
```

Then `GET /api/v1/helm/freshness` returns `evaluate_all()`. No other change is needed;
nothing must restart *now* — this is queued for the next safe restart.

## How the 14 UIs should badge off it

- **Page banner:** drive a global badge from `overall_state` — green FRESH, amber STALE,
  grey/hatched UNKNOWN.
- **Per-panel:** each panel maps to a signal `name`; when that signal is `STALE`, grey the
  panel and show `stale {age_seconds}s`; when `UNKNOWN`, hatch it and show `UNKNOWN — {reason}`
  (never render UNKNOWN as live). When `FRESH`, show `updated {age_seconds}s ago`.
- Poll `/api/v1/helm/freshness` on the same cadence as the tightest budget (~60–120s).

## Recommendation — continuous refresher + SSE push (design only, NOT built)

1. **Continuous refresher (server-side):** a lightweight asyncio task in the live app that
   calls `evaluate_all()` every ~15s and caches the result. Endpoints read the cache (O(1))
   instead of re-reading files per request, so a busy wall never starves. Pure-read; no
   writes to state files.
2. **SSE push:** add `GET /api/v1/helm/freshness/stream` (text/event-stream) that emits the
   cached `evaluate_all()` on change (and a heartbeat every ~10s). UIs subscribe once and
   badge in real time instead of polling — panels flip to grey the instant a signal crosses
   its budget. Debounce to emit only on state transitions to keep the stream quiet.
3. **Self-freshness of the refresher:** stamp each cache with `evaluated_at`; if the refresher
   task itself stalls, the stream's own heartbeat gap tells the UI to badge the whole board
   UNKNOWN — the monitor is monitored.

*No fake green:* the board above reports exactly what the files show right now; every STALE
is a real age past a real budget, and the one FRESH is the live soak snapshot.
