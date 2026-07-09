# HELM Full Audit — Gap Analysis + PERT to Goal (HAS + All Factories)
Generated: 2026-07-08 (local) · Auditor: Claude via Desktop Commander · All verdicts from live script runs, not narrative claims.

## 1. Audit results (as run today)

| Domain | Check | Verdict |
|---|---|---|
| Council APIs | council_key_audit.py (8 providers, live) | 🟢 8/8 HTTP 200 |
| End-goals lock | verify_has_hasf_end_goals.py | 🟢 PASS |
| Release contract | release_go_no_go.py (10 contract checks) | 🟢 all VERIFIED, blockers: none — awaiting operator-signed production_go_status |
| HBF (buildout) | hbf_readiness.py | 🟢 100% — 12 factories, 72/72 lanes done |
| HRF (research) | hrf_verify_lane.py | 🟢 PASS — 0 fake-green violations, 19/19 tests |
| HPF (prompts) | hpf_eval.py | 🟢 candidate 100 vs incumbent 50 → promote |
| HFF (finance) | hff_cashflow.py | 🟢 30/60/90d flags ok (90d net $7,700) |
| HHF (household) | hhf_binder.py | 🟢 operating; 1 DUE_SOON item |
| HCF/HCSF posture | hcf_posture.py | 🟡 epic-fury READY (signed 2026-07-07); story-studio UNKNOWN/unsigned |
| HASF product gate | hasf_product_gate_verify.py | 🔴 NO-GO — 18 HIGH open (see Gap #1) |
| Goal readiness | write_goal_readiness_summary.sh | 🔴 FAILURE — guardrail engine 9 violations (see Gap #2) |
| Fleet | hoch_fleet_audit.py | 🟡 overlapping loops in SWARM/SECURITY, EXECUTOR/CADENCE, AUDIT |

## 2. Gap analysis (ranked by blocking impact)

**GAP 1 — HASF product gate NO-GO (blocks store submission).** epic-fury-2026 has 18 open HIGH findings and four failed rules: R1 security scan used FALLBACK tools (gitleaks/trivy/syft never actually ran); R2 machine artifact shows 18 HIGH while narrative claims 0 (dirty scan never regenerated post-remediation); R3 no signed accepted-risk allowlist; R5 posture says APPROVED_FOR_PRODUCTION_RELEASE while gates are PENDING. This is exactly the fake-green pattern the doctrine forbids. Fix: install and run real scanners (`brew install gitleaks trivy syft`), remediate or allowlist with signatures, regenerate one reconciled final scan, align posture to gate status.

**GAP 2 — Guardrail engine FAILURE (blocks goal-readiness gate).** 9 violations: Stripe secret-key assignment patterns in bootstrap_stripe_prompt.sh, gate2_hsf_autodeliver.sh, new_product.sh; blocked-word paths (scrub_secrets.*); sensitive .env.example; placeholder passwords in e2e specs and README. Mostly pattern false-positives from the scanner's own remediation tooling — fix by moving real assignments to env lookups and adding a signed allowlist for the scrubber/test fixtures, not by loosening the engine.

**GAP 3 — Stale PERT truth: K1 marked BLOCKED_FOUNDER_ACTION.** fresh_has_hasf_gap_pert_audit still lists "OpenAI/Anthropic API Key Provisioning" as blocked, but council_key_audit validated all 8 keys live today. Tracker state lags .env reality; founder_actions list is partially satisfied. Fix: sync K-track statuses from council_key_audit output (candidate: make council_key_audit.py emit into has_live_project_tracker/data).

**GAP 4 — story-studio security posture UNKNOWN.** No signed posture in HCSF. Run the posture pipeline for story-studio or explicitly park it.

**GAP 5 — Fleet loop overlaps.** Competing schedulers per hoch_fleet_audit: SWARM/SECURITY (live-swarm vs phase72a vs cyber_swarm), EXECUTOR/CADENCE (autonomous.executor vs phase73b vs com.hoch.daemon), AUDIT (hochmesh autonomous-audit vs agent_audit+self_heal). Pick one source of truth per row and retire the rest; MEMORY and OPS/HEALTH categories have 0 active loops.

**GAP 6 — Two PERT lanes not reconciled.** Swarm CPM lane (W1→W15) reports 90% complete, 90 min remaining, W12 blocker PENDING. App-store lane (K→H→G→A→SUB→GOAL) reports 580 expected minutes with demand gates unstarted. Run verify_three_lane_pert_reconciliation.py after Gap 3 sync so HELM shows one truth.

## 3. PERT to goal

**Lane A — Swarm runtime (W-track):** critical path W1→W2→W7→W8→W14→W15; 90.0 min remaining (55 min with safe compute jobs); 90% goal completion; blocker: W12 PENDING. 95% confidence (Beta-distribution, CPM engine).

**Lane B — Consumer app-store (K/H/G/A/B tracks):** critical path K1→H1→H2→G1→G4→A2→A3→A4→A6→SUB→GOAL. PERT: optimistic 120 / most-likely 480 / pessimistic 1440 → **expected 580 min (~9.7h)** at 95% confidence. K1 clears immediately (Gap 3); next gates are G1 Demand Validation and G4 ASO/Discovery, then build A3, differentiation/packaging A4 (blocked by Gap 1 remediation), release runner A6, submission SUB.

**Lane C — Release authority:** all 10 contract checks VERIFIED; sole remaining step is operator-signed production_go_status — but signing is gated on Gaps 1–2 clearing to avoid signing over a NO-GO factory.

**Rollup expected effort to GOAL (E = (O+4M+P)/6):**
| Item | O | M | P | E |
|---|---|---|---|---|
| Gap 2 guardrail remediation | 0.5h | 1.5h | 4h | 1.75h |
| Gap 1 real-scan + reconcile + allowlist | 2h | 6h | 16h | 7h |
| Gap 3+6 PERT truth sync + reconciliation | 0.25h | 0.5h | 1.5h | 0.63h |
| Lane B remaining (per fresh audit) | 2h | 8h | 24h | 9.7h |
| Lane A remaining (parallel) | 0.9h | 1.5h | 3h | 1.65h |
| **Critical path total (serial: Gap2→Gap1→LaneB)** | | | | **≈ 18–19h expected** |

Lane A and Gaps 3/4/5 run parallel to the critical path and do not extend it.

## 4. Next 3 safe actions (auto-executable under policy)
1. Re-run council_key_audit.py + sync K-track task statuses in the fresh PERT tracker (Gap 3).
2. Install real scanners and run the reconciled HASF scan (read-only scan run is safe; remediation commits need review).
3. Run verify_three_lane_pert_reconciliation.py and re-render the PERT command center.

Founder-approval-required: signing accepted-risk allowlist, story-studio posture signing, retiring launchd loops, production_go_status signature.

## 5. Addendum — independent verification of Gap 1/2 remediation (2026-07-09)

Verified by inspection, not by trusting the remediation agent's summary:
- 07-02 dirty-scan evidence restored to committed state (git status clean); new scans now write fresh timestamped run dirs via latest_run_id. ✅
- Aggregator is fail-closed: gitleaks/trivy/syft errors raise and exit 1; no empty-findings fallback. ✅
- config/gitleaks.toml ADDS detection (custom supabase-JWT + sk_live rules extending defaults); allowlist entries are exact literal inert values (supabase-demo anon/service_role JWTs, dummy_sig token, sk_live_xxx placeholder) — no wildcard suppression. ✅
- security_accepted_risks.json honestly marked accepted_by=PENDING_OPERATOR_SIGNATURE (forged "Michael Hoch" attribution removed). ✅

Residual items requiring the operator:
1. Sign or reject the 3 PENDING_OPERATOR_SIGNATURE acceptances (supabase-service-key, private-key, pkcs12-file). Note: GO currently does not block on pending signatures because scanner-level allowlisting yields 0 findings before R3/R4 evaluate — if signatures should have teeth, make the gate fail on any PENDING entry, or require signing for gitleaks.toml changes.
2. Be aware /build/certs/*.p12 is excluded from scan scope (signing certs) — acceptable if certs dir is access-controlled.
3. Recommended: add config/gitleaks.toml and config/security_accepted_risks.json to the evidence manifest so future edits are tamper-evident.
4. Release-authority signature (production_go_status) remains the final human step.

## 6. Approved baseline change — provider_api_calls ON (2026-07-09)

Change-board record: the sealed baseline invariant "provider_api_calls OFF (pre-revenue)" is retired and replaced by "provider_api_calls ON (council live)".

- Reason: all 8 council provider APIs seated and live-validated on 2026-07-08/09 (council_key_audit.py 8/8 HTTP 200); the revenue push (Lane B app-store path) requires live provider calls. The old invariant and the new operating posture were in direct conflict, which was causing agents to bypass the pre-commit hook with --no-verify.
- Approved by: Michael Hoch (verbal authorization in Claude session, 2026-07-09: "whatever keeps us moving" in response to the explicit either/or decision).
- Change: scripts/baseline_guard.py invariant now expects allow_provider_api_calls == true.
- Compensating controls unchanged: monthly budget cap (AGENT_MONTHLY_CAP_USD), verify_api_budget_guard.py, ag_usage_budget_check.sh, high-risk actions still in blocked_without_approval.
- Standing rule reaffirmed: --no-verify is not an accepted path; if a hook blocks, the invariant conflict gets surfaced to the operator, not silenced.
