# HELM Final Execution Plan — burn-down to 100%
**2026-07-19 · companion to HELM_FINAL_15_PERCENT_GAP_ANALYSIS.md · NO new capabilities until every CRITICAL item is completed, deferred-with-justification, or founder-blocked.**

Rule of the phase: **finish, don't expand.** Any proposed work not tracing to a gap ID below is rejected by default.
Estimates are 3-point PERT expected values in focused hours; "auto" = fully scriptable, "assist" = agent-driven with human trigger, "manual" = human required.
**Estimates are planning guidance, NOT evidence** — an operational proof that fails (e.g. a concurrency defect surfaced by soak) legitimately grows the plan; the plan then updates, never the evidence standard.
**Status of this document: repository-local working plan** until the governed SHAs are pushed and independently corroborated — the claim taxonomy applies to the plan itself.

## Completion Matrix — no gap closes without every applicable dimension satisfied

| Dimension | Question |
|---|---|
| Engineering | Is the implementation complete? |
| Functional | Does it behave correctly? |
| Regression | Are automated tests present? |
| Runtime | Has it executed successfully under live conditions? |
| Evidence | Are artifacts immutable and traceable? |
| Operations | Can it recover from failure? |
| Security | Does it satisfy required controls? |
| Founder | Does it require founder approval (and is it granted)? |
| Production | Is there independent evidence supporting promotion? |

A gap's closure record must state each applicable dimension's evidence or mark it N/A with reason. A dimension marked UNKNOWN blocks closure — fail-closed, same as everywhere else.

## Four workstreams (every task below maps to exactly one)

**WS1 — Evidence Closure** (critical path): remote provenance (T3), CI-on-SHA (T3), SHA-bound verification (T4), goal recomputation + doorstep validation (T5), runtime confirmation (T1), lane recompute (T2).
**WS2 — Operational Proof:** soak (T16), restart/recovery drill (T14), concurrency + lease validation (T13), staleness watchdog (T15), replay/duplication (T17).
**WS3 — Quality Closure:** voice behavioral coverage (T11, T18), flake elimination (T9), regression stabilization (standing), NIST control disposition (T8), proof-atomicity decision (T12).
**WS4 — Production Readiness:** worktree curation (T10), founder decisions (T6 ASC, T7 release, NIST acceptances, factory deferrals T19), operator docs (T20), final GOAL computation (T5 output consumed).

WS1 gates everything: no WS4 promotion claim may cite WS2/WS3 results that predate the pushed SHAs they must bind to.

---

## WAVE 1 — CRITICAL PATH (sequence-ordered; blocks GOAL; no parallel shortcuts past a failed gate)

### T1. Dependency runtime confirmation  [G0/G12]
Purpose: bind the segmented-clean A3 claim to the actual executing environment.
Deps: none. Evidence: `runtime/confirmation_result.json` + pip_audit.json + freeze + drift. Validation: `result == PASS_WITH_SEGMENTED_LEGACY_FINDINGS`, failures []. Acceptance: A3 → PASS_WITH_SEGMENTED_LEGACY_FINDINGS, runtime_environment_confirmed=true. Effort: 0.5h (O.3/M.5/P1). Owner: agent(Mac). Automation: **auto** (`scripts/goal/run_dependency_runtime_confirmation.sh`). FG: no.

### T2. A1–A7 harness re-run  [G6]
Purpose: independent lane recomputed by the fixed harness — no manual overrides.
Deps: T1. Evidence: fresh `audit_status.json` + governed AUDIT_RESULT events. Validation: verdicts carry terminal lines; A1/A7 recomputed not overridden. Acceptance: lane state ≠ RECONCILIATION_PENDING; expected 6 PASS / 1 FINDING(A3-legacy-lane). Contingency: if Grok still omits terminal lines, add one reprompt-guard to `_verify` (bounded change, traces to G6). Effort: 1.5h. Owner: agent(Mac). Automation: **auto** (`helm_audit_runner.py --auto`). FG: no.

### T3. Governed commits → push → remote CI  [G14]
Purpose: immutable provenance; unblock SHA-bound review.
Deps: T2 (commit units include its evidence). Evidence: 5 manifests populated (parent_sha, commit_sha, tree_verified; signature_verified only if signing performed) + remote SHAs + CI run URLs. Validation: staged-paths ≡ manifest per unit; buildable at each boundary; `git log --show-signature` for any signed claim. Acceptance: remote exposes exact reviewed bytes; CI green on those SHAs. Effort: 3h (mixed-tree care). Owner: agent(Mac)+founder review. Automation: **assist**. FG: review.

### T4. Grok composed-runtime verification, SHA-bound  [G2]
Purpose: the only artifact that can satisfy N3.
Deps: T3. Scope (fixed by council): restored core + extension boundary + gate + proof transport + dual-decode + routing registry + rewired sites + adversarial failure matrix. Evidence: verdict artifact bound to commit SHAs. Validation: terminal `OVERALL:` line. Acceptance: **clean VERIFIED** → N3 DONE(verdict=VERIFIED); VERIFIED_WITH_LIMITATIONS → N3 stays PARTIAL, findings become new gap IDs. Effort: 2h + review latency. Owner: agent(Mac)/Grok. Automation: **assist** (`helm_fire_verification`). FG: no.

### T5. Goal-engine recompute + truth snapshot regeneration  [G1]
Purpose: authoritative percentage from validators, not from this plan.
Deps: T2, T4. Evidence: fresh goal_state.json / mission_state.json / build_to_goal_status.json + new dated truth snapshot + doorstep package. Validation: no DEPENDENCY_MISSING failure classes remain; GOV layer reflects real states. Acceptance: percent computed, published, matches evidence. Effort: 0.5h. Owner: agent(Mac). Automation: **auto**. FG: no.

### T6. ASC credential observation — SEQUENCE LAST  [G13]
Purpose: first-ever live Apple truth. Deps: T1–T5 complete (internal reconciliation done, per directive). Evidence: `asc_epic_fury.json` (live appStoreState) + refreshed champion gates. Acceptance: TESTFLIGHT/APP_STORE_CONNECT/REQ-TO-002 read live state; RELEASE machine advances per evidence. Effort: 10 founder-minutes. Owner: **FOUNDER** (`scripts/founder/asc_credentials_gate.py`). Automation: manual-gated. FG: **YES**.

### T7. Apple release action  [G20]
Only if T6 shows an approved releasable state. Owner: **FOUNDER**. FG: **YES** (irreversible). External timing: Apple.

*(Ambient: Stripe settlement auto-recheck fires 2026-07-21T14:00Z — observational, no owner action.)*

## WAVE 2 — HIGH (start in parallel with Wave 1 where deps allow; must close before "100%" may be claimed)

### T8. NIST 3-control closure  [G11]
Enumerate the 3 not-implemented controls from `helm_control_posture.json`; for each: implement (if hours-scale), or founder-accepted POA&M entry with risk statement. Evidence: posture recompute showing 13/13 implemented-or-accepted. Effort: 4h. Owner: agent + founder acceptance. Automation: assist. FG: acceptance only.

### T9. Event-bus flake root-cause  [G3]
Reproduce `test_commit_emits_event` order-dependence (shared EVENTS_PATH leakage suspected); fix via per-test ledger isolation fixture. Evidence: 50× repeated full-suite run, 0 flakes, logged. Effort: 2h. Owner: agent. Automation: auto. FG: no.

### T10. Worktree curation (pre-existing ~232 changes)  [G15]
Classify every pre-existing change: commit-worthy / quarantine / discard-with-founder-ack. Same manifest discipline as session units. Evidence: curation manifest + resulting clean `git status`. Acceptance: working tree ≡ committed state + intentional ignores. Effort: 6h (largest single debt item). Owner: agent + founder review. Automation: assist. FG: review.

## WAVE 3 — MEDIUM (operational hardening; each is one evidence run, not a build)

- **T11 Voice behavioral sweep [G9]:** parametrized test over every intent in `intent_registry` asserting real-data responses (kills the role-enumeration bug class). Evidence: new `tests/voice/test_intents_behavioral.py` green. 3h · agent · auto.
- **T12 Proof-atomicity decision [G4]:** implement the orphan-detecting reconciliation job (scan MISSION_TRANSACTION_COMMITTED without matching proof-hash in evidence chain → integrity finding) **or** founder-ratified deferral. 3h · agent · decision-gated.
- **T13 Lease/concurrency evidence [G7]:** run existing concurrency/lease/fencing provers (`prove_concurrency_controls`, HAF-LEASE, torn-read); write missing cancel/deadlock negatives only if absent. Evidence: dated results bundle. 3h · agent(Mac) · auto.
- **T14 DR drill [G19]:** execute `run_restart_recovery_proof.py` + one live kill-and-recover of the launchd runtime; date-stamped evidence. Corruption/power-loss scenarios → DEFERRED_WITH_JUSTIFICATION if drill passes. 2h · agent(Mac)+observer.
- **T15 Staleness watchdog [G17]:** single cron/launchd check — goal_state age > SLA ⇒ alert event + notification. Smallest honest alerting; no dashboard build. 1.5h · agent · auto.
- **T16 Soak evidence [G18]:** one dated run of the existing `soak_runner` with results ledgered. 2h wall-clock mostly unattended · agent(Mac).

## WAVE 4 — LOW (closure hygiene; do in gaps, refuse to expand)

- **T17 Replay/duplication test [G5]** — 1h. **T18 Voice safety negatives [G10]** — 1.5h. **T19 Factory deferral records [G8]:** one JSON per non-champion factory (state, justification, revival criteria, founder sign) — 1h + ratify. **T20 Operator runbook index [G16]** — 1h.

---

## PERT summary
Critical path: **T1 → T2 → T3 → T4 → T5 → T6 → (T7 external)** · expected agent effort ≈ **7.5h** + founder ≈ 10min + external review latency.
Total remaining effort, all waves: ≈ **35 agent-hours** + 2 founder gates + 3 founder decisions (NIST acceptances, atomicity deferral, factory deferrals, curation review).
GOAL flips when: T1–T5 complete with passing evidence **and** the goal engine — not this document — computes it. This plan asserts no percentage.

## Promotion decision artifact
`coordination/goal/HELM_PROMOTION_EVIDENCE_MANIFEST.json` is the SINGLE authoritative input to any promotion decision. Every field is a concrete artifact reference (id/hash/path) or null; any null or candidate-commit-stale field forces HOLD. It is currently a TEMPLATE (v2, machine-verifiable: every field carries value + verified + source + bound_to_candidate metadata) with overall_decision=HOLD; T3–T5 outputs populate it. **The ONLY component that may emit GO is `scripts/goal/verify_promotion_manifest.py`** — it evaluates the promotion invariant deterministically (complete AND verified AND bound-to-candidate AND no UNKNOWN AND no STALE AND founder gates resolved, else HOLD; verifier crash = HOLD), and writes GO only into a NEW dated decision copy, never the input. Nothing else — no report, no summary, not this plan — may be cited for promotion.

## Standing rules of the phase
1. New-capability requests are **refused** with a pointer to this plan until every CRITICAL item is complete/deferred/founder-blocked.
2. Every completion claim names its artifact; the claim taxonomy (file/commit/push/verified) applies to all of it.
3. Deferrals are records, not omissions (G8 pattern).
4. Manual status overrides remain prohibited; arbiters are the scripts, the harness, the goal engine, and Grok.
