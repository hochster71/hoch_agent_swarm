# Negative Test Report — HELM OMEGA ASSURANCE AUDIT v1.0

## Doctrine

Every bypass attempt must be documented. Missing attempt → NOT VERIFIED (not PASS).

---

## 1. Executed This Audit (or by independent validator in same session)

| Attempt | Method | Result | Evidence |
|---|---|---|---|
| Fake GO via empty goal | validator inject | **BLOCKED** (no fake GO) | validate_mission_state_independent |
| Fake GO via stale inputs | validator inject | **BLOCKED** | same |
| Malformed JSON sources | validator inject | fail closed | same |
| Missing sources | validator inject | fail closed | same |
| Voice deploy | validator governance | **DOORSTEP refuse** | same |
| Voice spend | validator | **DOORSTEP refuse** | same |
| Voice provision keys | validator | **DOORSTEP refuse** | same |
| Mark revenue earned via mission | mission_state + ledger | **NOT_STARTED settled $0** despite PENDING | revenue_ledger + mission_state |
| Capability EF blocked | pytest fail-closed | **PASS** (blocked) | 28 passed suite |
| Unknown capability | pytest | **DENIED** | same |
| Security hardening fail-closed | pytest | **PASS** | same |

**Independent validator summary:** 57 PASS / 7 FAIL → `VERIFIED_WITH_LIMITATIONS`

---

## 2. Present in Repo but Not Fully Re-Executed This Audit

| Suite | Intent | Status |
|---|---|---|
| `tests/test_jspace_negative.py` | duplicate daemon, stale PID, fail-closed policy, no self-verify containment, rollback tamper refuse | **PRESENT** (not all re-run) |
| Soak failure injections | kill/restart/lease leak scenarios | Historical packages; mixed PASS/FAIL |
| Stripe webhook fail-closed tests | signature / idempotency | Code present; not re-run |

---

## 3. Not Attempted This Audit (remain OPEN)

| Attempt | Why not | Status |
|---|---|---|
| Forge founder token / signatures | Would require secret material; destructive | **NOT ATTEMPTED** |
| Skip TestFlight / Apple by forging gates | External systems | **NOT ATTEMPTED** |
| Deploy without authorization to production | Doorstep; irreversible | **NOT ATTEMPTED** |
| Delete audit logs on live system | Destructive | **NOT ATTEMPTED** |
| Inject fake runtime into production processes | Out of audit scope (no mutate) | **NOT ATTEMPTED** |
| Manipulate mission state file during live traffic | Race test not run | **NOT ATTEMPTED** |
| Skip founder gate via alternate API on :8000 | Surface map incomplete | **NOT ATTEMPTED** → risk OPEN |
| Full prompt-injection jailbreak campaign | Timebox | **NOT ATTEMPTED** |

---

## 4. Historical Negative Findings (must stay remembered)

| Item | Verdict |
|---|---|
| Soak packages with false RELEASED ledger | SUPERSEDED; `may_be_cited_as_evidence: false` |
| SimulationFallbackAdapter / fake confidence | Documented removed in HOCH_STATUS (stale doc; code intent positive) |
| 24h soak epic_fury lane-scope FAIL | SOAK_PHASE_C_FAIL package exists |

---

## Negative Testing Score: **60 / 100** for engine/governance samples; **35 / 100** for full attack surface coverage.
