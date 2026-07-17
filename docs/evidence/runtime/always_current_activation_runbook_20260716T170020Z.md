# Always-Current UI — Post-Seal Activation Runbook

**Generated:** 2026-07-16T17:00:20Z
**Activator:** `scripts/activate_always_current.sh`
**Run it:** `bash scripts/activate_always_current.sh` — ONCE, **after the ~2:45pm CT Phase C soak seal**.
**Preview first (optional, read-only):** `bash scripts/activate_always_current.sh --dry-run`

This activator was **built inert** during the live soak. It performs **nothing** until the
founder runs it after the soak seals. It is idempotent and safe to re-run.

---

## What "always-current UI" is

`backend/runtime_freshness.py` is an honest freshness **scoreboard**: every HELM truth
source gets a tight per-signal budget and is badged **FRESH / STALE / UNKNOWN** (worst
signal wins the OVERALL). This activator makes that scoreboard **live** and keeps the
re-derivable signals **green**, replacing the once-daily blanket 86400s window.

Three pieces, wired by this script:

| Piece | File | Role |
|---|---|---|
| Scoreboard | `backend/runtime_freshness.py` | Read-only per-signal freshness; `python3 -m backend.runtime_freshness` prints the board. |
| API route | `backend/runtime_freshness_api.py` | Router → `GET /api/v1/helm/freshness` (UIs badge off `overall_state`). |
| Refresher | `scripts/runtime_refresher.py` + `deploy/launchd/com.hoch.runtime.refresher.plist` | Continuously re-derives the **COMPUTED** signals before their budgets expire. |

---

## Cited wiring facts (from the live repo)

- **App that owns `/api/v1/helm/*`:** `backend/helm_live_api.py`
  (`app = FastAPI(title="HELM LIVE")`). All `/api/v1/helm/{wall,runtime,factories,tasks,
  leases,authority,...}` routes are defined there. `backend/main.py` (:8000, title
  "Hoch Agent Swarm Control API") does **not** own these routes — so the freshness router
  is added to `helm_live_api.py`, per the note in `runtime_freshness_api.py` itself.
- **Launchd label serving that app:** **`com.hoch.helm-autoloop`** — the "hardened autoloop"
  `scripts/helm_autoloop.sh`, which keeps `uvicorn backend.helm_live_api:app` alive on
  **:8770** (loopback + self-signed TLS). The older launcher
  `scripts/run_helm_live_foreground.sh` (label `com.hoch.helm.voice`) **self-declares
  RETIRED / disabled** in its own source. The script detects which label is actually
  loaded at runtime and reloads only that one (`com.hoch.helm-autoloop` wins if both
  are present).
- **No `--reload`:** the autoloop starts uvicorn without `--reload`, so the new route
  requires the serving process to be cycled. The autoloop respawns uvicorn within its
  ~60s poll interval whenever `:8770` goes down; the script kills the current `:8770`
  listener and `kickstart -k`s the autoloop so the respawn happens promptly.

---

## Exactly what the script does (in order)

0. **HARD INTERLOCK.** `pgrep -f 'soak_runner.py'` → if **any** soak is alive, prints
   `ABORT: soak still active — activation must run after seal` and exits **3**. Nothing else runs.
1. **Step A — load the refresher.** Verifies `RunAtLoad=true`, copies
   `deploy/launchd/com.hoch.runtime.refresher.plist` → `~/Library/LaunchAgents/`, unloads
   first if already registered (idempotent), then `launchctl load -w`, and verifies the
   label `com.hoch.runtime.refresher` is registered. (Runs
   `scripts/runtime_refresher.py --loop --interval 300`.)
2. **Step B — wire the route.** Idempotently inserts, only if absent, right after the
   `voice_router` include in `backend/helm_live_api.py`:
   ```python
   from backend.runtime_freshness_api import router as freshness_router
   app.include_router(freshness_router)
   ```
   Then reloads **only** the serving API: `kickstart -k` for `com.hoch.helm.voice` if that
   is the loaded job, or (autoloop model) stop the `:8770` uvicorn listener + `kickstart -k
   com.hoch.helm-autoloop` so it respawns with the new code. Polls
   `GET /api/v1/helm/freshness` (https then http, `-k`) for a 200.
3. **Step C — producers (honest).** The refresher only covers the COMPUTED signals
   (`control_plane`, `goal_state`, `mission_state`). For the signals it must **not**
   fabricate, the script **reports** rather than guesses:
   - `supervisor_heartbeat` ← `backend/mission_control/helm_supervisor.py` (checked via `pgrep -f helm_supervisor`).
   - `helm_runtime_state`, `helm_agent_registry` ← `scripts/helm_autonomy_runner.py` /
     runtime dispatchers (checked via `pgrep -f helm_autonomy_runner`). Registry has no
     safe read-only regenerator.
   - `orchestration_authority` ← `secure_sync` (HOCH-200; remote/founder-owned).
   - `runtime_truth_snapshot` ← the live soak (frozen post-seal → honestly stale).

   **No on-disk launchd plist in this repo owns these**, so the script does **not**
   auto-start them (would be fake green). It prints the exact producer + FOUNDER STEP.
   `HOCH_STATUS.md` lists `com.hoch.goal.runtime.loop — goal runtime` as the runtime-loop
   job, but the script will not guess-start it.
4. **VERIFY.** Runs `python3 -m backend.runtime_freshness`, prints the board, parses
   `OVERALL`. Exits **0** if OVERALL is FRESH; otherwise exits **4**, listing each remaining
   STALE/UNKNOWN signal and its owed producer. **NO FAKE GREEN.**

Every irreversible action (`cp`, `launchctl load/unload/kickstart`, `kill`) is echoed with
an `[ACT]` prefix before it runs.

---

## What remains founder-owned

- Starting the **liveness producers** if they are down: the HELM supervisor
  (`helm_supervisor.py`) and the runtime loop / autonomy runner (`helm_autonomy_runner.py`).
  Until those run, `supervisor_heartbeat`, `helm_runtime_state`, and `helm_agent_registry`
  read STALE **honestly**, and the script exits 4 naming them.
- `orchestration_authority` refresh via `secure_sync` from HOCH-200 (remote authority).
- `runtime_truth_snapshot` is expected to be frozen (soak sealed) → stale by design.

Post-seal, the "never blanket-restart the execution daemon" burn-in constraint is lifted,
but this script still touches **only** the freshness refresher and the API service — it
never restarts the execution daemon, never dispatches missions, never moves money.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Activated; OVERALL FRESH (or `--dry-run` completed with no changes). |
| 3 | ABORT — a soak is still alive (interlock). |
| 4 | Plumbing live, but OVERALL still STALE/UNKNOWN; owed producers listed. |
| 1 / 2 | Setup error (missing plist, refresher failed to register, wiring anchor not found). |
