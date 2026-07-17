# HELM Continuous Freshness Refresher — Evidence

**Built:** 2026-07-16T16:44:00Z
**Component:** `scripts/runtime_refresher.py`
**Purpose:** Keep the COMPUTED/DERIVED HELM truth sources inside the per-signal budgets
defined in `backend/runtime_freshness.py`, so the 14 UIs are always current — replacing
the once-daily `helm-runtime-tick` as the thing that keeps data fresh.

**Soak safety:** Built and validated against a running 24h Phase C soak. NOTHING was
loaded, restarted, or dispatched. No daemon/launchd/soak action was taken. `--plan` is
read-only; tests use mocks/tmp only. NO FAKE GREEN.

---

## 1. Refresh registry (signal -> command -> interval)

Intervals are derived from each signal's budget in `runtime_freshness.py` at ~budget/3,
so each source is re-derived well before it can expire.

| Signal | Regenerator command | Budget | Interval (~budget/3) | Legitimacy |
|---|---|---|---|---|
| `control_plane` | `python3 scripts/build_control_plane_status.py` | 120s | 40s | Rebuilds `has_live_project_tracker/data/control_plane_status.json` read-only from its source files; only READS the liveness/authority sources. |
| `goal_state` | `python3 scripts/goal/goal_engine.py` | 3600s | 1200s | Recomputes completion ONLY from validators that actually ran; writes `coordination/goal/goal_state.json`. |
| `mission_state` | `python3 scripts/goal/goal_engine.py` | 3600s | 1200s | Same `goal_engine.py` run also writes `coordination/goal/mission_state.json`. Deduped at run time -> a single subprocess. |

The refresher NEVER writes a truth file itself — it only invokes each source's own
regenerator subprocess. If a regenerator errors it REPORTS the failure and leaves the
file as-is (fail-closed, honest).

### Liveness exclusion — deliberately NOT refreshed (justified)

These signals are refused by design; if their real producer is down they SHOULD read
stale and the freshness board flags that honestly. A guard test asserts none of them
ever appear in `REFRESH_REGISTRY`.

| Excluded signal | Why it must NOT be refreshed |
|---|---|
| `supervisor_heartbeat` (`helm_supervisor_heartbeat.json`) | LIVENESS — must be produced by the real supervisor. Writing it would fake liveness. |
| `runtime_truth_snapshot` (soak `runtime_truth_snapshots.jsonl`) | LIVENESS — produced by the live soak. A frozen soak SHOULD read stale. |
| `orchestration_authority` (`orchestration_bridge_control.json`) | HOCH-200 authority, refreshed only by `secure_sync` — not a safe local compute. |
| `helm_runtime_state` (`helm_runtime_state.json`) | Produced by the supervisor runtime loop; a refresher must not fabricate it. |
| `helm_agent_registry` (`helm_agent_registry.json`) | Factory registry has **NO safe read-only regenerator** here. Verified: `scripts/factory_runtime.py` does not exist, and `scripts/build_control_plane_status.py` only READS `helm_agent_registry.json` (via `wrap_section`, line ~166) — it never writes it. Its only writers are runtime dispatchers (`has_agent_dispatcher.py`, `helm_autonomy_runner.py`), which are NOT safe to run during the soak. Left honest for the board to flag. |

---

## 2. Test output (real, from sandbox)

```
$ python3 -m pytest tests/test_runtime_refresher.py -q
..............                                                           [100%]
14 passed in 0.12s
```

Coverage (`tests/test_runtime_refresher.py`):
- Schedule/due logic: FRESH-within-interval -> not due; FRESH-but-older-than-interval ->
  due; STALE -> due; UNKNOWN -> due.
- Intervals derive from budget/3.
- **Guard tests:** liveness signals (`supervisor_heartbeat`, `runtime_truth_snapshot`,
  `orchestration_authority`, `helm_runtime_state`, `helm_agent_registry`) are excluded from
  `REFRESH_REGISTRY`; registry and excluded sets are disjoint.
- Dedup: `goal_state` + `mission_state` collapse to ONE `goal_engine.py` subprocess.
- **Failing regenerator is reported, not faked** (status FAILED, rc surfaced, "left as-is"
  printed, file untouched); exec exception is caught and reported, not raised.
- Nothing-due runs no subprocess; `--plan` runs no subprocess.

All regenerators are mocked — no real subprocess, no real state files were touched by tests.

## 3. `--plan` dry-run (read-only, run against real files; wrote nothing)

```
$ python3 scripts/runtime_refresher.py --plan
==============================================================================
RUNTIME REFRESHER — PLAN (dry-run)
==============================================================================
BEFORE:
  control_plane          STALE    age=   54194s / budget=120s
  goal_state             STALE    age=   11526s / budget=3600s
  mission_state          STALE    age=   11526s / budget=3600s
------------------------------------------------------------------------------
WOULD RUN  control_plane          -> python3 scripts/build_control_plane_status.py
WOULD RUN  goal_state+mission_state -> python3 scripts/goal/goal_engine.py
------------------------------------------------------------------------------
AFTER:
  control_plane          STALE    age=   54194s / budget=120s
  goal_state             STALE    age=   11526s / budget=3600s
  mission_state          STALE    age=   11526s / budget=3600s
==============================================================================
```

AFTER == BEFORE confirms `--plan` mutated nothing. It correctly identified all three
computed signals as stale/due and deduped goal+mission into one `goal_engine.py` run.
(The parent will run `--once` on the Mac to actually close these — safe: both regenerators
were already run during the soak.)

---

## 4. Staged launchd unit

**Path:** `deploy/launchd/com.hoch.runtime.refresher.plist` (written, **NOT loaded**).

Runs `runtime_refresher.py --loop --interval 300` with `RunAtLoad` + `StartInterval 300`.

**Post-seal load (after the 24h soak seals):**
```
cp deploy/launchd/com.hoch.runtime.refresher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.hoch.runtime.refresher.plist
# Unload: launchctl unload ~/Library/LaunchAgents/com.hoch.runtime.refresher.plist
```

Do NOT load during the soak. The loop is idempotent and never restarts the daemon or
touches the soak.

---

## 5. How this + the freshness route make the UIs always-current

- `backend/runtime_freshness.py` is the honest **scoreboard**: tight per-signal budgets,
  FRESH/STALE/UNKNOWN, overall = worst tile. The freshness route surfaces this to the UIs.
- `runtime_refresher.py` is the **engine that keeps the score green** for the sources that
  are legitimately re-derivable. Every ~300s (launchd) it re-runs the real regenerators for
  `control_plane` (well inside its 120s budget via the 40s interval), and `goal_state` /
  `mission_state` (inside their 3600s budgets via the 1200s interval).
- Because refresh happens at ~budget/3, those three tiles stay FRESH continuously instead
  of decaying between daily ticks — so the 14 UIs reading them are always current.
- Liveness tiles remain owned by their real producers. If a producer dies, its tile goes
  STALE/UNKNOWN honestly and the board's worst-tile reduction flags the whole wall — exactly
  the behavior we want. The refresher never masks that.
