# EDR-0009 — Live-State Collectors ("Connect the Board")

> HELM-GOV | extends: EDR-0008 Operational Mission Telemetry | doctrine: Governance-before-Capability | edr: self (EDR-0009) | why: a board of envelopes answers "which envelopes exist," not "what is the machine doing."

- **Status:** PROPOSED — Builder-authored 2026-07-20. **Founder ratification required.** Additive; no existing runtime path modified. Independent Auditor verification required before any claim of *completion*.
- **Author (Builder):** Claude · **Date:** 2026-07-20
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` (frozen). Introduces **no new truth vocabulary** — reuses `proof_contract.Truth`, in particular the already-ratified non-advancing `CACHED`.
- **Related:** `backend/helm_runtime/collectors.py`, `scripts/founder_live.py`, `tests/unit/test_collectors.py`, `backend/helm_runtime/mission_envelope.py` (EDR-0008).

## Context

Founder critique, 2026-07-20, on the EDR-0008 board:

> "This still isn't showing HELM. It's showing mission envelopes. Those are different
> things. Right now your Founder screen is effectively saying 'here are the envelopes
> that exist.' What I want is 'here is what the machine is doing.'"

Scored: Honesty 10/10, No-fake-green 10/10, Architecture 9/10, **Live telemetry 3/10** —
"honest about what it doesn't know, but not connected to the systems that do know."

The critique is correct and the distinction is architectural, not cosmetic:

    Mission Envelope  -> HISTORY.    What a mission did. Written once, at close.
    Collector Reading -> LIVE STATE. What the machine IS. Re-read at every render.

EDR-0008 built the first. This EDR builds the second and renders them in separate panels,
because blending them is how a six-day-old fact starts looking like a current one.

### What connecting the board actually found

The sprint premise was that HELM's runtime signals exist and merely need wiring. They do
exist. **Every one of them is stale, and most still claim health:**

| Signal | Claims | Last written | SLA |
|---|---|---|---|
| `helm_supervisor_heartbeat.json` | `HEALTHY`, backend PID 12846 `RUNNING` | 5.8 days ago | 5 min |
| `live_telemetry_freshness.json` | `status: PASS` | 16.7 days ago | 30 min |
| `council_heartbeat.jsonl` | `state: ACTIVE`, `loop_health: HEALTHY` | 36.3 hours ago | 10 min |
| `qa_sentinel_heartbeat.jsonl` | 4 checks `OBSERVED`, 0 unknown | 36.4 hours ago | 30 min |
| `ag_daemon_heartbeat_status.json` | `HEARTBEAT_NO_GO` | 7.1 days ago | 5 min |
| `worker_heartbeats.json` → macbook | alive | 5.0 days ago | 5 min |

A naive collector — one that reads the file and renders the payload — would have produced
the most dangerous board in the system: **a dead supervisor shown as HEALTHY with a
running PID**, the specific numeric precision lending false confidence. That is worse
than the narrative-only reporting this whole line of work is replacing, because it would
carry the authority of a live dashboard.

**This is therefore not a wiring exercise. It is a truth-gating exercise.**

## Decision

1. **Adopt the Collector / Reading model** (`backend/helm_runtime/collectors.py`). A
   `Reading` is one live observation. Collectors never raise: a collector that fails
   yields an `UNKNOWN` Reading rather than a gap.

2. **Freshness gates truth, non-overridably.** A Reading's truth class is computed from
   its age against a declared SLA. The payload's opinion of itself is never consulted:

   | Condition | Truth | Advancing |
   |---|---|---|
   | read succeeded, within SLA | `OBSERVED` | yes |
   | computed from fresh inputs | `DERIVED` | yes |
   | read succeeded, **past SLA** | `CACHED` | **no** |
   | absent / unreadable / no timestamp / no target | `UNKNOWN` | no |

   Because `CACHED` is already non-advancing in the ratified vocabulary, a stale
   `HEALTHY` is *structurally incapable* of turning a panel green. The board still shows
   the claim — always quoted, always paired with its age — so the founder sees both what
   the daemon believed and how long ago it believed it.

3. **Host scope is explicit; reading a file is not observing a host.** Collectors declare
   `LOCAL` (this process), `INDIRECT` (a file another host wrote), or `REMOTE` (needs
   network access we lack). The process collector, asked for PID/CPU/RAM, **refuses** when
   it is not running on `michaels-macbook-pro` and reports why, rather than presenting
   sandbox PIDs as HELM's runtime. Conflating "I read a file the Mac wrote" with "I can
   see the Mac" is the error this rule exists to prevent.

4. **Policy consequence requiring founder ratification: fake red is prohibited on the
   same terms as fake green.** A test suite that cannot execute — missing dependency,
   import error — is reported `UNKNOWN` with the missing modules named, **not** `FAIL`.
   An environmental failure is not evidence that the code is broken. Currently
   `tests/unit` cannot collect in the Builder sandbox (`No module named 'fastapi'`), so
   the qualification domain reads NOT OBSERVED rather than failing.

5. **Policy consequence requiring founder ratification: configuration is not liveness.**
   The founder asked for `Claude Opus ACTIVE / Grok NOT INVOKED`. Role bindings are
   readable configuration; per-model invocation state has **no runtime surface in HELM
   today**. The collector reports the binding and marks invocation `NOT_OBSERVABLE`.
   Deriving "ACTIVE" from a config file would be inventing liveness. Closing this gap
   requires instrumenting the dispatch gateway — named as follow-on work, not faked here.

6. **Domain verdicts are derived from collectors, not asserted.** `OBSERVED` (≥1
   advancing reading) · `STALE` (data exists, past SLA) · `UNREACHABLE` (collector exists,
   cannot see target) · `NO_COLLECTOR` (not connected — genuinely unknown). A domain
   leaves `NO_COLLECTOR` only when a real collector reports on it, exactly as the founder
   specified.

## Evidence

38 tests passing (`test_collectors.py` 21 + `test_mission_envelope.py` 17), each an
attempt to make a dead or unobservable signal render as good news:

| Attack | Test |
|---|---|
| stale `HEALTHY` renders green | `test_stale_healthy_payload_is_cached_not_observed` |
| 17-day `PASS` overrides staleness | `test_payload_claiming_pass_cannot_override_staleness` |
| timestamp-less payload treated as fresh | `test_reading_with_no_timestamp_is_unknown_not_fresh` |
| sandbox PIDs shown as HELM runtime | `test_process_collector_refuses_to_report_foreign_host` |
| missing dependency reported as FAIL | `test_unrunnable_suite_is_unknown_not_fail` |
| config binding rendered as liveness | `test_model_collector_does_not_invent_liveness` |
| collector crash silently drops a domain | `test_exploding_collector_yields_unknown_reading_not_crash` |
| stale domain counted as observed | `test_domain_with_only_stale_readings_is_stale_not_observed` |
| board hides stale count | `test_board_reports_stale_count_and_does_not_hide_it` |

TRUTH_SOURCE for this EDR's own claims: `TEST_EXECUTION` → OBSERVED.

## Current board state (2026-07-20T14:52Z)

    live domains: 1/10    stale signals: 9    unreachable: 2

Only `engineering` is live, via git. That is the honest reading of the machine right now,
and it surfaces an operational finding the narrative reporting never did: **HELM's
supervisor, council loop, QA sentinel and worker heartbeats all stopped days ago.** The
board's first act was to reveal that the runtime it was built to observe is not running.

## Scope limits — what this EDR does NOT claim

- **Six domains still have no collector**: deployment, family_ops, calendar_ops, home_ops,
  finance_ops, founder_decision. They render `NO_COLLECTOR`. No placeholder was invented.
- **`research` shows NO_COLLECTOR despite an envelope existing.** Envelopes are history;
  the domain has no *live* collector. The panels are deliberately not blended.
- **No diagnosis of why the daemons stopped.** The board reports staleness; it does not
  claim to know the cause. Restarting them is a founder action on his host.
- **Process, CPU, RAM and model-invocation telemetry remain unavailable from the Builder
  sandbox.** Delivering them requires a collector running on `michaels-macbook-pro` that
  publishes to a path both hosts share — designed for, not delivered.
- **Auditor verification has not occurred.** Per EDR-0006 this is UNKNOWN, not complete.

## Next mission (continues "Connect the Board")

1. **Founder**: decide whether the stopped daemons should be restarted — that answer
   changes whether the next collector work is worth doing.
2. Mac-side agent collector publishing PID/CPU/RAM/heartbeat to a shared path (unblocks
   the founder's PROCESS and AGENT ACTIVITY panels).
3. Instrument `dispatch_gateway.py` to emit per-model invocation events (unblocks MODELS).
4. Deployment collector (Vercel/Apple state), then family/calendar/home/finance envelope
   emission per EDR-0008 §Migration.

## Reversal

Delete `collectors.py`, `test_collectors.py`, revert `founder_live.py` to its EDR-0008
form. Nothing else imports them. Reversal cost: zero.
