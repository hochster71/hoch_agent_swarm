# Epic Fury lane-scope gate leak — root cause, fix, and deterministic proof

**Date:** 2026-07-16T20:08:59Z
**Sealed run under investigation:** `coordination/council/live_proof_packages/HELM-SOAK-24H-20260715T194547Z` (NOT modified)
**Verdict:** Leak root-caused, fixed fail-closed, and proven deterministically without re-running 24h.

---

## 1. The failure

The sealed 24h Phase C soak passed **19/20** checks. The only failure:

```
epic_fury_stayed_lane_scoped = false
```

Each round `seed_round(rnd)` (scripts/council/soak_runner.py:88) seeds an Epic Fury task
`SOAK-EF-<n>` with `required_capability = "APP_STORE_CONNECT_OBSERVATION"` that must be
BLOCKED every cycle. Over 1383 rounds it dispatched **once**.

Evidence — the exact leak round in the sealed `scheduler_cycles.jsonl`:

```
round 644  2026-07-16T07:30:30Z  ids: ["SOAK-HASF-644","SOAK-EF-644","T-EF-DIST-01","SOAK-HRF-644"]
round 642/643/645/646  →  normal 4-pod batches, NO EF
```

Round 644 is the *only* one of 1383 rounds where `SOAK-EF-` appears in `ids`. Note that a
*second* Epic Fury distribution task, `T-EF-DIST-01`, also dispatched that same round and HCF/HSF
dropped from the batch — both externally-gated EF tasks leaked simultaneously, confirming a
transient state where the Apple block was momentarily not in effect.

## 2. Root cause (fail-OPEN capability gate)

The dispatch-time capability gate lives in
`backend/mission_control/persistent_scheduler.py :: rank_tasks()` (called by `run_once()` at
line 890). Pre-fix, a task with a `required_capability` was skipped ONLY if that capability
appeared in a **dynamically-derived** `blocked_capabilities` set:

```python
blocked_caps = set(f_info.get("blocked_capabilities") or [])
t_cap = (t.get("required_capability") or "").upper()
if t_cap and t_cap in {c.upper() for c in blocked_caps}:
    continue      # skip
```

`blocked_capabilities` is produced by
`backend/mission_control/scoped_states.py :: evaluate_states()` (lines 84-87) and is populated
**only when `epic_fury_blocked` is True**:

```python
epic_fury_blocked = False
for b in blockers:
    if b.get("id") in ("G-6","G-7") and b.get("status") not in ("RESOLVED","PASS"):
        epic_fury_blocked = True
...
"blocked_capabilities": (["APP_STORE_CONNECT_OBSERVATION", ...] if epic_fury_blocked else []),
```

`blockers` comes from `load_blockers()` (persistent_scheduler.py:162), which reads
`has_live_project_tracker/data/goal_blocker_register.json` and **fails OPEN**:

```python
if not blocker_file.exists():
    return []
try: ...
except Exception:
    return []        # parse error / partial read -> "no blockers"
```

**The leak:** the capability hold was tied to the *presence of an active external blocker*, not
to the capability itself. Whenever `epic_fury_blocked` evaluated False for even one cycle —
because the register momentarily had no active G-6/G-7 (resolved/absent) **or** because a
concurrent non-atomic rewrite of `goal_blocker_register.json` produced a transient read/parse
failure so `load_blockers()` returned `[]` — `blocked_capabilities` was empty, the
`t_cap in blocked_caps` test was False, and the EF `APP_STORE_CONNECT_OBSERVATION` task sailed
through `rank_tasks` into dispatch. That is exactly round 644: no active Apple block visible that
cycle ⇒ two EF tasks admitted. "Can't tell / nothing blocked" was treated as "allow".

## 3. The fix (fail-CLOSED, positive-grant required)

Smallest correct change, at the gate itself — make dispatch of a capability-bearing task require
a **positive grant** instead of the absence of a block. File:
`backend/mission_control/persistent_scheduler.py`.

Added a module-level grant set:

```python
DISPATCH_GRANTED_CAPABILITIES: frozenset = frozenset({"LOCAL_ONLY"})
```

and a default-DENY check at the top of the per-task loop in `rank_tasks()`:

```python
# (b0) FAIL-CLOSED CAPABILITY GATE — dispatch only if positively granted.
if t_cap and t_cap not in {c.upper() for c in DISPATCH_GRANTED_CAPABILITIES}:
    logger.info(f"Skipping {t['task_id']}: capability {t_cap} not positively granted (fail-closed)")
    continue
```

- `LOCAL_ONLY` = self-contained local work needing no external/founder authority (all 8factory
  **moonshot** tasks carry it — verified they remain dispatchable, so the 3:30 moonshot is unaffected).
- `APP_STORE_CONNECT_OBSERVATION` / `APPLE_DISTRIBUTION_PROMOTION` and any other externally-gated
  capability are **absent from the grant set ⇒ denied by default**, independent of blocker state.
- The pre-existing `blocked_missions` / `blocked_capabilities` checks are retained beneath it for
  mission-level lane-scoping semantics and defense-in-depth, but they are no longer load-bearing
  for the hold: even with `blockers == []` the EF task is denied. The race window is closed
  deterministically — no blocker file, resolved blocker, or parse failure can open the gate.
- Capability-free tasks (`required_capability = None`, e.g. all SOAK pod / unrelated HASF work)
  are unaffected: `if t_cap and ...` short-circuits, so "unrelated HASF work continues" holds.

Distinct `required_capability` values across the live DB at fix time: `None` (5537 tasks),
`APP_STORE_CONNECT_OBSERVATION` (1383). No legitimate task depends on an ungranted capability.

## 4. Deterministic proof (fast, no 24h)

New test: `tests/test_capability_gate_fail_closed.py` drives the SAME dispatch path
(`PersistentScheduler.rank_tasks`) used by `run_once()`.

Key test `test_ef_blocked_every_cycle_5000_iterations`: 5000 cycles, cycling through EVERY
blocker state — including the exact round-644 shapes `[]` (parse-fail/missing) and both G-6/G-7
cleared — asserting the EF `APP_STORE_CONNECT_OBSERVATION` task is admitted **0/5000** times.
Targeted tests also cover: leak condition (no active blocker → denied), UNKNOWN capability →
denied, `LOCAL_ONLY` granted → dispatches under all states, unrelated HASF work continues, and a
mixed batch. Because the `[]` / both-cleared states leave `blocked_capabilities` empty, denial in
those cases can come ONLY from the new fail-closed grant gate — proving the fix, not the old path.

Real output:

```
$ python3 -m pytest tests/test_capability_gate_fail_closed.py -q
.......                                                                  [100%]
7 passed in 0.26s
```

Blocked every cycle: **YES (0/5000 admissions)**.

Regression check — related scheduler/auth suites still green:

```
$ python3 -m pytest tests/test_soak_select_freshness.py tests/test_h1b_authorization_enforcement.py -q
31 passed, 3 warnings in 33.00s
```

## 5. Short confirmation soak — SKIPPED (honest timing call)

The 120s confirmation soak was **not run**. Current time at decision was 15:07 CDT, already past
the 3:05 PM CDT cutoff (with the 3:15 seal-check and 3:30 moonshot immediately after). Running a
soak would also have seeded EF tasks and churned the live DB right before the seal-check. Per
instruction, skipped and relying on the deterministic unit/integration proof above.

## 6. Endurance already proven; this fix proven without re-running 24h

24h/24-7 endurance was already established by the sealed run
`HELM-SOAK-24H-20260715T194547Z` (19/20, the single failure being this gate). The gate fix is a
localized, default-deny enforcement change proven deterministically across 5000 iterations and
every blocker state — no 24h re-run required to establish the fix holds.

## 7. Guardrails honored

- **Sealed proof package NOT modified** (`find` shows no files newer than seal time; only reads).
- **No daemon / uvicorn restarted.** No `soak_runner.py` process running (verified via `ps aux`).
- **NO FAKE GREEN:** the soak check `epic_fury_stayed_lane_scoped` was NOT weakened; the actual
  dispatch gate was made fail-closed. The sealed run still honestly records the pre-fix failure.

### Files changed
- `backend/mission_control/persistent_scheduler.py` — added `DISPATCH_GRANTED_CAPABILITIES` +
  fail-closed capability check in `rank_tasks()`.
- `tests/test_capability_gate_fail_closed.py` — new (7 tests, 5000-iteration EF block proof).
- `docs/evidence/runtime/epic_fury_gate_fix_20260716T200859Z.md` — this document.
