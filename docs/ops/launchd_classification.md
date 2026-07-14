# launchd Agent Classification (GAP-16)

**Date:** 2026-07-14 · **Mode:** READ-ONLY. Nothing unloaded, disabled, killed, or deleted.
**Machine-readable registry:** `coordination/ops/LAUNCHD_AGENT_REGISTRY.json`

## First: the count was wrong

The brief said **63 plists / 31 loaded**. The truth is **62 plists / 30 loaded**.

`grep -i hoch` also matches `actions.runner.hochster71-hoch_agent_swarm.has-qa-runner-mac` — a GitHub
Actions runner that matches only because the *repo name* contains "hoch". Subtract it and both numbers
land: 62 + 1 = 63, 30 + 1 = 31.

Two agents are naming outliers — `com.hochmesh.autonomous-audit` and `com.hochster71.has.tracker`.
Both are **loaded**, both are **BROKEN**, and both are invisible to a strict `com.hoch.*` sweep.
Every loaded label has a real plist file; there are no fileless ghosts.

## Counts

| Classification | Count |
|---|---|
| AUTHORITATIVE | 5 |
| SUPPORTING | 11 |
| LEGACY | 25 |
| DUPLICATE | 5 |
| BROKEN | 12 |
| FOUNDER_REVIEW | 4 |
| UNKNOWN | 0 |
| **Total** | **62** |

## The four things that can hurt the soak

**1. `com.hoch.helm.operations` — owns the running scheduler. Do not touch.**
`helm_supervisor.py` (PID 12844) is the **parent** of the live `PersistentScheduler` (PID 17807) and
of a `backend.main` uvicorn (PID 12846). Its loop polls every 5s and `Popen`s any dead child straight
back. Unloading this agent kills the scheduler the soak depends on. **SAFE_TO_DISABLE: no.**

**2. `com.hoch.helm-autoloop` — will respawn a competing API.**
`helm_autoloop.sh` (PID 41697) loops forever. Every pass it curls `127.0.0.1:8770/api/v1/helm/wall`
with a 5s timeout, and **if that check fails it spawns a new `uvicorn backend.helm_live_api:app` on
`0.0.0.0:8770`**. The live API (PID 98242) is on `127.0.0.1:8770` and is **not launchd-managed by any
of the 62 plists** — someone started it by hand. So a hiccup on :8770 produces a second uvicorn
fighting for the same port. It also re-asserts a `tailscale serve --https=443` route and sends
outbound founder notifications every 60s.

**3. Port 8000 has two live owners.** Confirmed by `lsof`, not inferred:

| PID | Bind | Owner agent |
|---|---|---|
| 11911 | `127.0.0.1:8000` | `com.hoch.agent.swarm.runtime` |
| 12846 | `*:8000` | `com.hoch.helm.operations` |

Two independent instances of the same FastAPI app, running right now. A **third** plist
(`com.hoch.api.server`) claims the same port and is mercifully unloaded. This is the duplicate-telemetry
and incident-attribution problem, and it is real, not theoretical.

**4. `com.hoch.helm-council` — can autonomously edit a protected file.**
`council_sweep.sh` runs every 6h and audits a target list that explicitly includes
`backend/mission_control/per_task_lease.py` — one of the files this mission forbids modifying. It
dispatches to Grok (paid, credentialed) and `auto_council.py` states plainly that CONFIRMED findings
become *"remediation task queued for the autonomous factory"*. A 6-hourly timer that can rewrite the
lease manager under a live soak.

## BROKEN — 12, of which 9 are dead targets

Nine plists point at files that **do not exist**. Several have been failing on a timer for a long time.

| Agent | Missing target | Last exit | Retry |
|---|---|---|---|
| `com.hoch.council-watch` | `scripts/council_watch.sh` | 127 | every **20s** |
| `com.hoch.status-listener` | `scripts/status_listener.sh` | 127 | every 20s |
| `com.hoch.relay-refresh` | `scripts/relay_refresh.sh` | 127 | every 60s |
| `com.hoch.rollcall-digest` | `scripts/status_notify.sh` | 127 | 3×/day |
| `com.hoch.frontier-council` | `scripts/frontier_council_caller.py` | 2 | every 30m |
| `com.hoch.mesh-broker` | `mesh-os/mesh_broker.py` | 2 | KeepAlive loop |
| `com.hochmesh.autonomous-audit` | `mesh-os/scripts/mesh_autonomous_cycle.sh` | 127 | every 15m |
| `com.hochster71.has.tracker` | `has_live_project_tracker/server.js` | 1 | KeepAlive loop |
| `com.hoch.phase50.e2e.tick` | `phase50/phase50_e2e_tick.sh` | — | not loaded |

`council_watch.err.log` is exactly the `helm_autoloop.sh` story repeating: *"No such file or directory"*,
forever, silently. **Note `rollcall-digest`:** if the founder believes he gets a 3×-daily digest, he
does not — that channel has never fired from this agent.

The other 3 BROKEN have targets that exist but fail: `family.morning` (exit 141 / SIGPIPE),
`family.neo.ops.seeder` (exit 1, every 15m), and `model-upgrade` — see below.

### `com.hoch.model-upgrade` is a fake green

The plist is **malformed XML**: line 7 contains a raw unescaped `&&` inside a `<string>`. `plutil` and
`PlistBuddy` both refuse to parse it (*"unknown ampersand-escape sequence"*). `launchctl print` shows
`inferred program = /bin/bash` — launchd never got a clean `ProgramArguments`. It is scheduled Sundays
at 03:00; the last Sunday was 2026-07-12, and its log has not been written since **2026-07-07**.

And `launchctl list` reports **last exit code 0**.

An agent that cannot be parsed and has not run in a week is reporting success. The target script
(`scripts/model_upgrade.py`) *does* exist — the fix is to escape the ampersands, not to delete anything.

## FOUNDER_REVIEW — 4

- **`com.hoch.release.gowatch`** — *not loaded, and it must stay that way.* It would run
  `sign_release_go.py --operator "Michael Hoch" --confirm --watch` with `RunAtLoad` + `KeepAlive`:
  a daemon that continuously signs releases **as the founder with the confirmation flag pre-baked in**.
  The human approval step is hardcoded into the plist.
- **`com.hoch.helm-council`** — spends money, can autonomously edit `per_task_lease.py`.
- **`com.hoch.helm-autoloop`** — external `:443` exposure + outbound notification channel.
- **`com.hoch.ollama.tailscale`** — not loaded; would expose an unauthenticated model endpoint on the tailnet.

Also worth the founder's eye: `com.hoch.mesh-broker.plist` stores `MESH_API_KEY` in **cleartext** in the
plist. Weak key, but it is the pattern that matters.

## What I could not determine

- **`soak_runner.py` is not in the process table.** The brief says a 2-hour soak is running. `ps` shows
  only two `watch_soak.sh` *watchers* (PIDs 50254, 81170) and no `soak_runner.py`. Nothing was touched
  either way — but this registry will not call the soak healthy when it cannot see it. **Verify.**
- **`~/bin/memory-response.sh`** runs every 300s and its name implies it acts under memory pressure. It
  lives outside the repo and was not read line-by-line. If it kills memory-heavy processes, the
  long-lived soak and scheduler are candidates. *Not confirmed — flagged, not asserted.*
- **What `model-upgrade` actually executes**, given launchd half-parsed its plist.
- **Whether the `hoch-swarm` family-ops line is still wanted.** 25 LEGACY agents live in
  `/Users/michaelhoch/hoch-swarm` and the mesh trees, not in HELM. Their targets mostly exist. That is
  a product decision, not something disk evidence can settle. Every *running* one is marked
  `needs-founder`.

Three sibling repos with near-identical names — `hoch_agent_swarm` (HELM), `hoch-swarm` (family ops),
`hoch-agent-swarm` (abandoned) — are themselves an incident-attribution hazard.

## Recommendation

**No mass deletion.** Nothing was disabled here and nothing should be, mid-soak.

- **Do not touch during the soak:** `helm.operations`, `helm-autoloop`, `has.pert-server`,
  `has.live-truth-sidecar`, `daemon`, `goal.runtime.loop`, `agent.swarm.runtime`.
- **Zero-risk once the soak lands:** the 9 dead-target agents. Check `rollcall-digest`'s digest is
  delivered some other way first.
- **The one structural fix that pays for this whole exercise:** pick a single owner for `backend.main`
  on port 8000. Two live instances and a third plist claiming the port is the root of the ambiguity
  this classification was called to end.
