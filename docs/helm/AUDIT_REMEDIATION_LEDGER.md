# HELM audit remediation ledger — Kimi 3.0 scan / Grok 4.5 review

**Source:** Kimi Agent 3.0 MAX builder tech-debt scan, re-calibrated and dispositioned by
Grok 4.5 (2026-07-17). **Framing (accepted):** high-signal *builder debt backlog*, NOT mission
assurance. Do **not** use it to claim "security verified" or "EDR-0002 Grok-verified." Each surface
stays UNVERIFIED until its own evidence re-proves it. This ledger tracks the batch; nothing here is
marked green without a check.

## Independent validation (Builder/Claude, against the code)
- **#2 dual control surfaces — CONFIRMED.** `backend/main.py` = 721 KB vs `helm_live_api.py` = 82 KB.
  Real twin-surface drift.
- **#3 EDR-0002 verification PENDING — CONFIRMED.** Tracked Grok verdicts under
  `docs/evidence/audit/bridge_verification/` are bound to the **frozen N3 target `d8d5139a…`** and
  self-labeled *"EVIDENCE-REVIEW… NOT independent re-execution."* The EDR-0002 target `20afc264…`
  appears only in target-declaration files — no clean `OVERALL: VERIFIED` covers it. (Minor: the
  audit's "only gitignored notes" wording is stale — tracked verdict dirs exist — but none verify
  `20afc264`, so the substance holds.)

## Remediation batch (Grok's order)
| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Lock `approval_gate` | **ALREADY LOCKED (verified)** | `backend/approval_gate.py`: `execution_allowed_after_approval` always False; FAIL_CLOSED cannot be approved (L113-114); APPROVED requires a verified founder signature (L123-131). Fail-closed confirmed by read. |
| 2 | Gate modelops-eval fabricator | **DONE (verified)** | `backend/modelops_manager.py`: seeded `eval_score`s stamped `eval_source=SEED_UNVERIFIED, eval_verified=False`; `load_models()` default-deny normalizes pre-existing registries; new `get_models_public()` renders `eval_display=UNVERIFIED` and `health_public()=UNVERIFIED` until a real eval sets `eval_verified`. Test: 7/7 seeds render UNVERIFIED, 0 fake-green. |
| 3 | Gate mesh telemetry (`model_mesh.py`) | **DONE (verified)** | Fabricated `latency_ms 120.4/65.1`, `tokens_per_sec`, `vram_gb` replaced with `provenance:UNMEASURED` + null metrics. Reachability (real port scan) retained; perf now renders UNVERIFIED, never a made-up number. Syntax verified. |
| 4 | Fix health predicates | **DONE (this pass, verified)** | Swept: `conmon_manager` already uses **live** boundary assessors (TLS/auth/port) — evidence-based, kept. `runtime_truth/collector.py` fails-closed on exception. `cybergov_manager` scorecard now stamped `evidence_provenance:STATIC_BASELINE`, `assessor_type:DOCUMENTED_SELF_ASSESSMENT`, `authorization_status:NOT_AUTHORIZED`, pointing to conmon as the live layer — scopes severity by surface per Grok #4. No remaining green-without-observation predicate found. |
| 5a | Disambiguate dual **aggregators** (`build_executive_brief` ×2) | **DONE (verified)** | Two functions shared the name across surfaces. Now: `helm_executive_brief.build_executive_brief` banner-marked CANONICAL + alias `build_unified_executive_brief`; `voice/briefing.build_executive_brief` banner-marked VOICE-scoped + alias `build_voice_brief`. Old names kept as back-compat — every existing import verified still resolving, aggregators remain distinct. Non-breaking. |
| 5b | Consolidate dual **control surfaces** (`main.py` FastAPI vs `helm_live_api.py` FastAPI) | **MAPPED (verify-first done)** | `docs/helm/CONTROL_SURFACE_MAP.md`: actually THREE apps on distinct ports (main :8000 / 576 routes, helm_live_api :8770→:8443 / 68, pert_server :8765). **Only route collision = `/favicon.ico`** — not duplicate planes. `main`-split already underway (`backend/routers/`). Safe path documented: continue extraction, declare ownership, do NOT merge. Router extractions remain incremental guarded passes. No behavior changed. |
| — | EDR-0002 formal verdict for `20afc264…` | **PREMISE CORRECTED + status recorded** | `docs/evidence/audit/EDR-0002_VERIFICATION_STATUS.md`: `20afc264` was **deliberately superseded** by frozen impl-only target `d8d5139a` (which has a Grok evidence-review PASS covering the Dispatch Gateway). EDR-0002 is **evidence-review-verified via the frozen target**; **independent re-execution** is what genuinely remains PENDING. Do not claim "EDR-0002 Grok-verified" without that qualifier. |
| — | EDR-0002 formal Grok package for `20afc264…` | **PENDING** | Produce a tracked verdict bound to the EDR-0002 target (not the N3 frozen target) before any "EDR-0002 verified" claim. |

## Dropped (per Grok disposition)
- Kimi #5 (urllib) and the specific #7 example — not actioned.

## Doctrine
Gate/relabel fabricators on every executive surface; re-prove each surface with its own evidence;
never self-certify from Kimi grades. Controllable items driven to done + tested; externally- or
evidence-gated items (EDR-0002 formal verdict) stay explicitly PENDING.

## 2026-07-19 launch-audit batch (Builder/Claude, accepted council review)
| # | Item | Status | Evidence |
|---|------|--------|----------|
| 6 | Goal-engine interpreter false-red (Xcode python3, no pytest → GOV-002/003/004 + ES-002 read FAILED) | **FIXED (verified)** | Suites pass clean-room: 28/28, 7/7, 15/15, 10/10. `goal_engine.py` `_validator_python()` probe; original at `recovered_sources/audit_20260719/`. |
| 7 | Failure-class taxonomy (audit directive) | **DONE** | `goal_engine.py` now stamps `failure_class` ∈ CONTROL_FAILED / DEPENDENCY_MISSING / EXECUTION_ERROR on every non-satisfied validator; all classes remain fail-closed. |
| 8 | `GOAL_REACHED 100%` fake green | **REVOKED** | N3_VERIFY → PARTIAL (verdict VERIFIED_WITH_LIMITATIONS recorded), GOAL_HELM → PENDING; honest 85.0%. Evaluator hardened: `helm_goal_runner.py` `_effective_status` — DONE + non-clean verdict ⇒ PARTIAL, structurally. |
| 9 | Audit-lane stall root causes | **FIXED (re-run pending)** | `helm_audit_runner.py` bare-`python3` → `_py()` probe; Grok FINDING-by-default on missing terminal line documented. A1–A7 adjudicated from re-executed evidence: 4 PASS / 2 FAIL / 1 HOLD → `coordination/goal/audit_adjudication_20260719.json`. |
| 10 | **Frozen-target drift** (A7) | **FAIL — FOUNDER DECISION** | 5/17 files of d8d5139a carry uncommitted in-place EDR-0006 edits (+ builder rebound to claude-sonnet-5). Ratify+re-freeze+re-verify, or revert to composed modules. N3 stays PARTIAL until resolved. |
| 11 | Revenue mislabeling risk | **DONE** | `product_registry.json` + `stripe_settlement.json`: `revenue_class=FOUNDER_TEST_REVENUE` (founder self-purchase; live-verified pending, settles ~07-21, auto re-check scheduled). |
| 12 | A3 SBOM has no CVE grading | **GRADED — FINDINGS OPEN** | pip-audit vs uv.lock: 13 findings / 4 pkgs (pillow→12.3.0, mcp→1.28.1, json-repair→0.60.1, chromadb no fix); npm 0/100. Evidence: `coordination/evidence/sbom_cve_20260719/`. Next: bump deps, re-audit in the Mac venv. |
| 13 | A7 retest + evidence continuity | **PASS (retested)** | `coordination/evidence/a7_drift_20260719/retest_result.json` — original FAIL preserved; 17/17 on-device; discovery→disposition→remediation→retest chain intact. |
| 14 | ROUTING-REGISTRY-DUAL-READ | **OPEN (contained)** | Formal MEDIUM finding; 8 direct readers enumerated; structural test prohibits NEW direct reads; `binding_status()` telemetry warns on disagreement. Closure = migrate readers, shrink allowlist. |
| 15 | GOVERNED_COMMIT_INLINE_PROOF | **PARTIAL (recorded)** | Requirement record with compensating control (payload proof transport) + residual atomicity risk teed for the independent reviewer. |
| 16 | Extension adversarial matrix | **DONE (verified)** | `tests/helm_runtime/test_extensions.py`: 19 cases — gate/manifest absence, malformed + CONFLICTING proof encodings (fail closed, tested down to ConMon coverage), registry absent/malformed/under-attributed/inactive, dual-read containment, binding telemetry. 114 total tests green. |
