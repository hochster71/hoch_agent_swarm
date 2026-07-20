# HELM Final 15% — Gap Analysis
**2026-07-19 · Mission Commander (Claude Builder) · evidence-based; code existing is NOT proof; UNKNOWN stays UNKNOWN**

Position: 85.0% (honest, post-revocation). This document maps the remaining 15% as evidenced gaps, not features.
Evidence tiers used: **VERIFIED** (executed this session / fresh validator), **EVIDENCED** (artifact exists, not re-executed), **UNKNOWN** (no current evidence — held as UNKNOWN, never assumed), **BLOCKED** (external/founder gate).

Legend per subsystem: Eng = engineering complete · Run = runtime complete · Ops = operationally complete · IV = independently verified · Prod = production ready · FG = founder gate required · Risk/Pri · CP = on critical path to GOAL.

---

## 1. Executive Runtime (mission control, runtime truth, lifecycle)
| Facet | State | Evidence |
|---|---|---|
| Eng | YES | frozen core 17/17 vs d8d5139a (on-device re-hash); SI 284/284; bridge/dispatch/txn suites 40/40 |
| Run | YES-EVIDENCED | launchd `com.hoch.agent.swarm.runtime.plist` + `helm-runtime.out/err.log` present; API restart hardening committed (0b2c346b) |
| Ops | PARTIAL | goal engine ran under wrong interpreter until this session's fix; **fixed engine not yet re-run on Mac** |
| IV | **NO — HOLD** | Grok verdict VERIFIED_WITH_LIMITATIONS covers frozen core only; composed runtime (extensions) unreviewed |
| Prod | NO (HOLD) | production_authority HOLD until SHA-bound Grok VERIFIED |
| Risk/Pri | HIGH / **CRITICAL** · CP: YES | Gap ID: **G1** (goal-engine recompute), **G2** (Grok composed review) |

## 2. Coordination Bus (events, ordering, races, replay, duplicates)
Eng YES-VERIFIED (frozen event_bus + append-only log; proof transport composed; conflict fail-closed tested). Ops PARTIAL: **commit/proof atomicity is a recorded PARTIAL requirement** (GOVERNED_COMMIT_INLINE_PROOF — orphaned-commit reconciliation absent); one order-dependent test flake observed once (`test_commit_emits_event`, shared-ledger leakage) — **race evidence, not closed**. Duplicate suppression / replay: event replay IS the ledger by design, but no replay-under-duplication test exists → UNKNOWN. IV: NO. Risk MEDIUM / Pri HIGH · CP: via N3. Gaps: **G3** (flake root-cause + test isolation), **G4** (proof-atomicity reconciliation job or outbox — architecture decision, defer-with-justification allowed), **G5** (replay/duplication test).

## 3. Council (voting, quorum, aggregation, promotion)
Eng YES-VERIFIED (H1B 28/28: quorum can't come from mock/dry-run; single-consume authorization; GOV-003 subset 7/7). Run EVIDENCED (dispatch ledger: 6 council tasks, 0 founder transport; H1D relay COMPLETED with grok+ollama). Ops PARTIAL: **Grok auditor lane returns verdicts without terminal lines → everything reads FINDING** (harness patched, unproven live). IV: pending lane re-run. Risk MEDIUM / Pri **CRITICAL** · CP: YES. Gap: **G6** (A1–A7 harness re-run with terminal-verdict enforcement; add a reprompt-on-missing-verdict guard if first run still stalls).

## 4. Agent Runtime (dispatch, leases, locks, retry, cancellation)
Eng YES-VERIFIED (dispatch 10/10 — dispatch loop is sole spawn point; spend gate 15/15; egress 0 ungated). Run EVIDENCED (36 lease files in coordination/leases; lease/fencing tests exist: HAF-LEASE checks, `test_collector_write_lock`, e2e device-service-lease). Deadlock recovery / cancellation / checkpointing: tests not identified this session → **UNKNOWN**. Risk MEDIUM / Pri MEDIUM · CP: NO. Gap: **G7** (enumerate + execute lease/deadlock/cancel/checkpoint test evidence; if absent, write the missing negative tests).

## 5. Factory-Verse (HASF · HRF · HMF · HSF · HCF · HFF · HHF · HPF)
Registry is already honest (`coordination/council/factory_registry.json`, readiness-reconciled):
**HASF READY** (production — champion lane, proven by Epic Fury path) · **HMF/HRF/HCF/HFF DEGRADED** (functional-prototype) · **HSF/HHF/HPF NOT_READY** (prototype/dormant; hsf/ contains story-engine.js + v2 HTML — prototype). Classification per the mission prompt: 1 Production, 4 Functional-degraded, 3 Prototype/Dormant, 0 Missing.
**Doctrine call: do NOT drive 7 factories to production in the final 15% — that is feature creep.** The GOAL requires the champion path (HASF) proven, which it is. Disposition: HASF = maintain VERIFIED; the other 7 = explicitly **DEFERRED_WITH_JUSTIFICATION** (post-GOAL roadmap), each keeping its honest registry state. Risk LOW / Pri LOW · CP: NO. Gap: **G8** (write the deferral record so "degraded" is a decision, not drift).

## 6. HELM Voice
Eng SUBSTANTIAL (29 modules: intent parser/registry, authorization, cost gate, rate limiter, redaction, sanitizer, confirmation, audit + security events, TTS). Run EVIDENCED (`helm_live_voice.err.log` exists — service has run; voice registration log present). Tests: **thin** — `tests/voice/test_voice_gateway.py` only; one real defect found+fixed this session (VOICE-AGENT-ROLE-ENUMERATION: broken schema read shipped silently — proof the lane lacks behavioral coverage). Latency/speech pipeline: UNKNOWN. IV: NO. Risk MEDIUM / Pri MEDIUM · CP: NO. Gap: **G9** (intent-level behavioral test sweep over the command router — every intent asserts real data, not fallbacks; the role-enumeration bug class), **G10** (voice safety/authorization negative tests evidence run).

## 7. RMF / Security / ConMon / Governance
ConMon FRESH + honest (assessed 2026-07-19T02:56Z: **10/13 controls implemented, 3 not** — posture 76.9%). Egress/spend/governance VERIFIED (A4/A5/A6 PASS from live probes + re-executed tests). Secret sweep VERIFIED (0/175). SBOM: default runtime CLEAN (0 findings/90 pkgs, lock-level); venv confirmation PENDING; 2 segmented legacy advisories. Immutable logs/provenance: proof-record chain implemented; **conflict fail-closed tested**. IV: pending lane. Risk LOW-MEDIUM / Pri HIGH · CP: YES (A-lane). Gaps: **G11** (close or formally accept the 3 unimplemented NIST controls — enumerate them, disposition each), **G12** (venv confirmation run = existing script).

## 8. Runtime Truth (no-fake-green, staleness, hashes)
STRONGEST DOMAIN post-session: validators fail-closed with 9-code taxonomy; GOAL evaluator structurally rejects non-clean verdicts; no-fake-green + tautology + freshness guards PASS; frozen-hash guard runs in the test suite. IV: the truth engine itself is in the frozen core (covered by prior verdict) but the new taxonomy/guards are composed-layer → Grok scope. Risk LOW / Pri done-except-IV · CP: via G2. No new gap beyond G2/G6.

## 9. Founder Gates (money, signing, credentials, store, release)
| Gate | Enforced? | Evidence |
|---|---|---|
| Money movement | **VERIFIED** | A4 live probe: metered dispatch BLOCKED (FOUNDER_GATE_REQUIRED_METERED_API); spend caps live |
| Release/promotion | **VERIFIED** | REQ-TO-002 fail-closed on live ASC read; SHIPPED requires READY_FOR_SALE observation |
| Signing | EVIDENCED | founder release-approval artifact present (REQ-CP-SIGNING); no counter-evidence |
| Credential provisioning | ENFORCED-BY-DESIGN | asc_credentials_gate.py: hidden prompt, live validation, never echoed — **not yet exercised** |
| Store submission | BLOCKED_EXTERNAL | correct fail-closed hold |
| Authorization single-consume | **VERIFIED** | H1B 28/28 incl. replay-impossible |
Risk LOW / Pri — · CP: ASC is sequence-last by directive. Gap: **G13** (ASC gate exercised once = founder action, sequence step 12).

## 10. Build Pipeline / Remote Ops (CI, packaging, doorstep, rollback)
Intake→doorstep VERIFIED (7/7 stages, 0 copy/paste). Packaging/release docs EVIDENCED (5/5 + checklist). **Remote lane is the weakest CP item: worktree uncommitted (~232 pre-existing + session changes), remote predates session, CI-against-SHA never run for this work, Grok can't bind.** Rollback: recovered_sources snapshots exist for every session mutation; git-level rollback UNPROVEN. Risk HIGH / Pri **CRITICAL** · CP: YES. Gaps: **G14** (five governed commits per manifests → push → CI on SHAs — sequence steps 4–8), **G15** (pre-existing 232-change curation pass — separate from session units).

## 11. Documentation
Strong and current where it matters: constitution, 7 EDRs, doctrine, runbooks incl. **DR runbook (has-v2-disaster-recovery-runbook.md), failover runbook, 24-7 operations runbook**, secret rotation, session handoff, this session's runbooks/plans. Gaps: no single operator "start-to-verified" onboarding doc; runbooks not validated by execution (see §13). Risk LOW / Pri LOW · CP: NO. Gap: **G16** (one operator runbook index page; validate-by-doing folds into G17).

## 12. Observability / Performance
Logging EVIDENCED (structured event ledger + service logs + sidecar). Dashboards: /command + mission state (runtime-truth backed — VERIFIED fresh this morning). Metrics/tracing/alerting: **no dedicated alerting path identified → UNKNOWN**; failure visibility relies on fail-closed states surfacing in truth projections (acceptable by doctrine, but silent-death of the launchd runtime would only appear as staleness). Performance/stress/burn-in: soak_runner.py + burn-in provers exist (EVIDENCED, dates unverified); no current latency/memory evidence → UNKNOWN. Risk MEDIUM / Pri MEDIUM · CP: NO. Gaps: **G17** (staleness→alert hook: one watchdog that flags goal_state older than SLA — smallest honest alerting), **G18** (one recorded soak/burn-in run with dated evidence, reusing existing runners).

## 13. Disaster Recovery
Runbooks EXIST (DR, failover, restart via launchd/systemd units). **Validation evidence: none current → UNKNOWN.** run_restart_recovery_proof.py exists (scripts/council) — a recovery proof harness is already built but no fresh artifact found. Partial-write safety: torn-read test exists (test_au9_torn_read_safety). Risk MEDIUM / Pri MEDIUM · CP: NO. Gap: **G19** (execute run_restart_recovery_proof + one kill-and-recover drill, date-stamped evidence; corruption/power-loss stays DEFERRED_WITH_JUSTIFICATION if drill passes).

---

## Consolidated gap register (the entire remaining 15%)
| ID | Gap | Pri | CP | Owner | FG |
|---|---|---|---|---|---|
| G0 | Reconciliation chain steps 1–3 (runtime confirmation, result validation, A-lane harness) | CRITICAL | YES | agent(Mac) | no |
| G1 | Goal-engine recompute w/ fixed interpreter | CRITICAL | YES | agent(Mac) | no |
| G2 | Grok composed-runtime review, SHA-bound, clean VERIFIED → N3 | CRITICAL | YES | agent(Mac) | no |
| G6 | A1–A7 lane re-run w/ terminal-verdict guard | CRITICAL | YES | agent(Mac) | no |
| G14 | Governed commits → push → remote CI on SHAs | CRITICAL | YES | agent(Mac) | no |
| G12 | Venv dependency confirmation (existing script) | HIGH | YES | agent(Mac) | no |
| G11 | 3 unimplemented NIST controls: close or accept | HIGH | no | agent+founder | partial |
| G3 | Event-bus test flake root-cause + isolation | HIGH | no | agent | no |
| G15 | Curate the ~232 pre-existing worktree changes | HIGH | no | agent+founder | review |
| G9 | Voice intent behavioral sweep | MEDIUM | no | agent | no |
| G4 | Proof-atomicity: reconciliation job OR defer w/ justification | MEDIUM | no | agent | decision |
| G7 | Lease/deadlock/cancel/checkpoint evidence run | MEDIUM | no | agent | no |
| G19 | DR drill: restart-recovery proof executed + dated | MEDIUM | no | agent(Mac) | no |
| G17 | Staleness watchdog → alert | MEDIUM | no | agent | no |
| G18 | One dated soak/burn-in evidence run | MEDIUM | no | agent(Mac) | no |
| G5 | Replay/duplication test | LOW | no | agent | no |
| G10 | Voice safety negative-test evidence | LOW | no | agent | no |
| G8 | Factory-verse deferral records (7 factories) | LOW | no | agent | ratify |
| G16 | Operator runbook index | LOW | no | agent | no |
| G13 | ASC gate exercised (sequence-LAST) | GATE | YES | **founder** | YES |
| G20 | Apple release click if approved | GATE | YES | **founder** | YES |

**Explicitly NOT in the 15% (feature creep, refused):** driving the 7 non-champion factories to production; new dashboards; new agents; crewai lane revival; any new architecture. Debt reduction already executed this session: 106 packages removed, dual implementations collapsed (gate → one extension; routing → one resolver), stale artifacts quarantined.

**Closure standard:** every gap closes only through the Completion Matrix in the execution plan (Engineering / Functional / Regression / Runtime / Evidence / Operations / Security / Founder / Production — each satisfied or N/A-with-reason; UNKNOWN blocks).
**Document status:** repository-local working plan until governed SHAs are pushed and independently corroborated.

Companion: `HELM_FINAL_EXECUTION_PLAN.md` (burn-down PERT, four workstreams).
