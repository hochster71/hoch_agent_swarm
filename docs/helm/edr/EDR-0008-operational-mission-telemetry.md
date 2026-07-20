# EDR-0008 — Operational Mission Telemetry (the execution record)

> HELM-GOV | extends: EDR-0007 Mission Contract v1, EDR-0006 Engineering Doctrine | doctrine: Governance-before-Capability | edr: self (EDR-0008) | why: HELM had a contract saying what a mission *may* do, and no record of what it *did*.

- **Status:** PROPOSED — Builder-authored 2026-07-20. **Founder ratification required.** Runtime is additive and opt-in; no existing path is modified. Independent Auditor verification required before any claim of *completion*.
- **Author (Builder):** Claude · **Date:** 2026-07-20
- **Reviewers:** Auditor — independent verification required. Founder — ratification of §Decision.3 and §Decision.4.
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` (frozen; **not amended**). Introduces no new truth vocabulary — borrows `proof_contract.Truth` via `mission_contract`.
- **Related:** `backend/helm_runtime/mission_envelope.py`, `scripts/founder_live.py`, `tests/unit/test_mission_envelope.py`, `coordination/missions/envelopes/`, `backend/helm_runtime/event_bus.py`.

## Context

Founder observation, 2026-07-20:

> "HELM is already performing useful background work across family operations, home
> operations, calendar synchronization, reminders, research, and engineering
> intelligence — but you only learn about it afterward through a long narrative. That
> is not adequate Founder visibility."

The 2026-07-20 scheduled runs demonstrated real truth discipline in prose: Alison's
calendar was marked unverified rather than empty, failed research sources were
disclosed, no unnecessary reminder mutations were made. **The discipline was in the
narrative, not in the system.** A narrative can be summarized; a summary can be
flattened to green; and numbers with no artifact behind them can ride along inside it.

That last risk is not hypothetical. The founder's own proposed dashboard mockup
contained `41 tasks · 0 duplicates · 0 stale completions` and
`Michael Mac calendar query timed out; Google fallback used`. A repository-wide grep
found **no artifact anywhere producing those figures**. They entered a founder-facing
board through narrative summarization alone. The failure mode reproduced itself inside
the mockup of its own fix. This EDR exists because prose discipline does not survive
compression, and only a machine-checked record does.

### What existed, and the precise gap

EDR-0007 established the Mission Contract: a **pre-execution** allowlist (SCOPE,
TOOLS_ALLOWED, FOUNDER_GATES, STOP_CONDITIONS, TRUTH_SOURCE). `event_bus.py` provides a
domain-agnostic append-only event log. Neither is the missing piece.

The gap is the **post-execution record** — actions taken, sources read and how well they
are known, mutations made, things that stayed unknown, errors, and evidence. Without it:

- a mission's status is whatever the agent last said in chat;
- read-only inspections and no-op decisions leave no trace, so "nothing changed" is
  indistinguishable from "nothing ran";
- a domain HELM is silently not covering looks identical to a domain that is healthy;
- engineering telemetry (git, tests, deploys) exists while family, calendar, home, and
  finance operations have none — so the founder board could only ever show a fraction
  of what HELM does.

## Decision

1. **Adopt the Mission Envelope v1** (`backend/helm_runtime/mission_envelope.py`) as the
   execution record for **all** HELM missions across **all ten operational domains** —
   engineering, qualification, deployment, factory, family_ops, calendar_ops, home_ops,
   finance_ops, research, founder_decision. Engineering is one domain among ten, not the
   board itself.

2. **Status is derived, never declared.** The envelope exposes no status setter; the
   constructor rejects a caller-supplied `status`; and the founder renderer **re-derives**
   status from recorded facts, ignoring any stored status field. An agent — or a
   tampered file — cannot present a mixed-truth run as green. Derivation:

   | Recorded facts | Derived status |
   |---|---|
   | not closed | `RUNNING` |
   | hard error, nothing produced | `FAILED` |
   | any error | `COMPLETED_DEGRADED` |
   | any unknown, or any non-ADVANCING source | `COMPLETED_PARTIAL` |
   | outputs produced but sources unproven | `COMPLETED_PENDING_EVIDENCE` |
   | all sources ADVANCING **and** evidenced | `COMPLETED_VERIFIED` |

   There is deliberately no plain `COMPLETED`. Every terminal state names its quality.

3. **Policy consequence requiring founder ratification: a read-only inspection that
   produces no artifact cannot be VERIFIED.** The 2026-07-20 cleaning-list run inspected
   five lists and correctly changed nothing — but left nothing re-readable, so it derives
   `COMPLETED_PENDING_EVIDENCE`, not green. This is NO-FAKE-GREEN applied to no-ops. The
   remedy is cheap (write an inspection manifest), and the alternative — trusting an
   unevidenced "I checked, it was fine" — is exactly what this EDR removes.

4. **Policy consequence requiring founder ratification: absence is rendered, not
   omitted.** A domain with no envelope appears in an `UNATTESTED DOMAINS` panel reading
   *"NO TELEMETRY — status genuinely unknown."* A quiet domain must be visibly quiet.
   Consequence: on adoption day the board shows nine of ten domains unattested. That is
   the honest starting position and it should not be softened.

5. **The renderer reads envelopes and nothing else.** `scripts/founder_live.py` has no
   access to chat, narrative, or agent summary. Work that emits no envelope cannot appear
   as work. Every scalar on the board traces to an envelope field; untraceable numbers are
   structurally unable to reach the founder.

## Evidence

| Claim | Mechanism | Path |
|---|---|---|
| Status cannot be declared | 17 adversarial unit tests, all passing | `tests/unit/test_mission_envelope.py` |
| Mixed-truth run is not green | `test_unknown_source_cannot_be_green_even_with_output` | same |
| Forged status ignored by board | `test_renderer_rederives_and_ignores_tampered_status` | same |
| Silence is visible | `test_unattested_domain_is_shown_not_omitted` | same |
| Green remains reachable | `test_clean_run_with_full_evidence_is_verified` | same |
| Real backfill emits DEGRADED | executed run, envelope on disk | `coordination/missions/envelopes/TECH-SCOUT-20260720.json` |

Test result 2026-07-20: **17 passed**. TRUTH_SOURCE for this EDR's own claims:
`TEST_EXECUTION` → OBSERVED.

## Scope limits — what this EDR does NOT claim

- **Only one envelope exists.** `TECH-SCOUT-20260720` is backfilled because this Builder
  session executed it and verified both artifacts by re-reading them from disk.
- **The family-ops, calendar-ops and home-ops runs of 2026-07-20 have NO envelope and
  will not be given one retroactively.** This Builder did not execute them and cannot
  re-read their intermediate state. Manufacturing envelopes from another session's prose
  would reproduce precisely the defect being corrected. Those domains render UNATTESTED
  until their own runs emit envelopes.
- **No existing scheduled task has been modified.** Instrumenting them is the next
  mission and requires touching agent code — a founder gate.
- **This is not yet a live UI.** It is a terminal board plus a `--json` feed. Wiring it
  into the dashboard is a publish act and remains a founder gate.
- **Auditor verification has not occurred.** Per EDR-0006 this work is UNKNOWN, not
  complete, until independently verified.

## Migration

Additive and opt-in. Nothing imports `mission_envelope` yet except the backfill script
and the renderer.

1. **Founder ratifies** §Decision.3 and §Decision.4 (or amends them).
2. **Auditor verifies** the invariant tests independently.
3. Instrument scheduled tasks one domain at a time, starting with `family_ops` — it has
   the richest mixed truth (successful sources, a repeated timeout, a fallback, a
   read-only inspection, a no-op decision) and is therefore the best negative test case.
4. Wire the `--json` feed into the dashboard (founder gate: publish act).

## Reversal

Delete `coordination/missions/envelopes/`, `mission_envelope.py`, `founder_live.py`, and
this EDR. No other module imports them. Reversal cost: zero.
