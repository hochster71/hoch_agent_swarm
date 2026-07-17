# HELM MISSION ASSURANCE AUDIT — COMBINED BRIEF v2 (ChatGPT 5.6 + Grok 4.5)
> Give this identical brief to BOTH models. They audit INDEPENDENTLY against the SAME frozen commit and produce output in ONE shared schema so results are field-for-field comparable and reconcilable by a third party (Claude). This is a MISSION ASSURANCE audit — prove the system, do not merely inspect it. No model audits/certifies its own prior work. **The baseline audit is read-only and evidence-producing; do NOT remediate during it.**

---

## 0. ROLE & POSTURE
Independent mission-assurance auditor for HELM (Hoch Agent Swarm executive OS), repo `~/hoch_agent_swarm`. Audit like NASA/DoD RMF/FedRAMP high-assurance: runtime evidence over claims. Record your model identifier + run timestamp + the frozen commit. Inspect, infer conventions, proceed. STOP only for: secrets, spending, legal acceptance, external signing/submission, irreversible production changes, external-account ops. Never print/inspect/exfiltrate secret values.

## 1. NON-NEGOTIABLE DOCTRINE (enforce in scoring)
1. **No fake green.** Runtime evidence overrides docs; models advisory; if they disagree, runtime wins.
2. Missing evidence = UNVERIFIED; stale = STALE; planned ≠ live; simulated ≠ operational. A model response / build / pricing config / checkout is NOT completion/revenue/release.
3. **Controllable vs Externally-gated.** *Controllable* (repo, architecture, UI, voice, cyber hardening, NIST maps, ConMon, evidence, tests, docs, runtime verification, factories, perf, CI/CD, packaging, internal readiness) may later be driven to verified completion. *Externally-gated* (Apple review, App Store publication, first purchase, Stripe settlement, bank deposit, ATO/audits, DNS, third-party approvals) stay **BLOCKED_EXTERNAL/WAITING_EXTERNAL** until the external party's authoritative evidence confirms — never on expectation. Never conflate them in the score.
4. Evidence-triggered transitions only. Release `BLOCKED_EXTERNAL→APPLE_APPROVED→READY_FOR_RELEASE→LIVE`; Revenue `CHECKOUT_CREATED→PAYMENT_AUTHORIZED→SETTLED→REVENUE_VERIFIED`.
5. **HELM Design Constitution (score compliance):** I Truth-in-Motion, II Runtime-Truth-First, III Evidence-Before-Confidence, IV Explain-Causality, V Honest-Uncertainty. 5 viz gates: (a) decision supported? (b) authoritative source? (c) if event stops, does viz stop? (d) misleads under stress? (e) greens on absent/stale evidence?
6. Founder gates (money, publish, secrets, deploy) never cleared by voice/model/test/fixture/narrative. Privileged ops deny-by-default. Authoritative-source failure fails closed.

## 2. SHARED CLASSIFICATION (use these EXACT labels — no synonyms)
Component: `VERIFIED_LIVE · IMPLEMENTED_UNVERIFIED · PARTIAL · MOCKED · PLANNED · STALE · BROKEN · ABSENT · UNKNOWN`.
Operational: `VERIFIED · OBSERVED · ESTIMATED · CONFIRMED_LIVE · ACTIVE · PENDING · BLOCKED · BLOCKED_EXTERNAL · WAITING_EXTERNAL · DEGRADED · FAILED · UNVERIFIED · UNKNOWN · PLANNED · NOT_STARTED`.
Severity: `CRITICAL · HIGH · MEDIUM · LOW · INFO`.
Verdict (one): `VERIFIED · VERIFIED_WITH_LIMITATIONS · FAILED · BLOCKED`. Never "production ready/complete/100%/best in class" unless evidence objectively supports it.

## 3. AUDIT TARGET FREEZE (do FIRST, record as evidence)
Both auditors MUST inspect the SAME commit. Record: repository remote; branch; `git rev-parse HEAD`; `git status --porcelain`; submodule commits; dependency lockfile hashes (uv.lock / package-lock); runtime configuration NAMES (exclude values); host OS + arch; Python/Node/Docker/package-manager versions. If the working tree is dirty, PRESERVE the status as evidence — do not silently clean/reset/stash/modify. **If the two auditors' commit hashes differ, reconciliation is invalid until rerun against a common immutable target.**

## 4. AUDIT / REMEDIATION SEPARATION (credibility-critical)
The independent audit phase is evidence-producing and READ-ONLY except isolated temporary test artifacts + local process control explicitly permitted in §11. **Do NOT remediate findings during the baseline audit.** Produce: (1) BASELINE verdict + evidence; (2) a SEPARATE proposed remediation plan. Only AFTER third-party reconciliation + authorization does remediation happen in a DISTINCT run, producing a POST-REMEDIATION verification report that RETAINS the original baseline findings. Never rewrite the baseline report after repairs. (This prevents a model from certifying its own fixes.)

## 5. CURRENT BASELINE — VERIFY, DO NOT ASSUME (treat every item UNVERIFIED until exercised)
- **Epic Fury (READ CAREFULLY):** Verify the EXACT currently-published App Store version independently. Treat the reported v1.0.2 status as **WAITING_EXTERNAL / IN_REVIEW** until authoritative Apple evidence confirms approval. Do NOT infer v1.0.2 is live merely because an earlier version may already be published. (An earlier version live + v1.0.2 in review can both be true — classify precisely, per version.)
- 8 factories (HASF/HRF/HCF/HMF/HSF/HFF monetized; HHF/HPF exempt). ~8 products (Story Studio live checkout; HFF-Runway, HFF-Invoice-Aging, HRF-Clarity-Briefs, HRF-Compliance-Digest, HMF-Cue-Library, HMF-Podcast-Stings, HCF-CyberQRG code-complete). Verify tests actually pass.
- HELM LIVE API `backend/helm_live_api.py` (uvicorn :8770, HTTPS dev cert); endpoints `/api/v1/helm/{goal,factories,tasks,agents,chain,integrity,pert,runtime,wall,hmai,external,nist}`. A SECOND app `backend/main.py` (:8000) also holds security surfaces — NOT unified.
- HMAI `backend/truth/hmai.py` (`/api/v1/helm/hmai`); `/executive`. External-milestone tracker `backend/truth/external_milestones.py` (`/api/v1/helm/external`) — evidence-gated. API hardening `backend/security/api_hardening.py` — auth + CORS allowlist + rate limit + payload cap, **staged behind flags default OFF** (`HELM_REQUIRE_AUTH`, `HELM_CORS_ALLOWLIST`). Verify BOTH postures.
- Known prior findings (Grok ~51/100 NOT READY): unauth sensitive GET + CORS `*`; stale session docs/heartbeats; validator env-rot ("No module named pytest" in the Xcode Python running validators); incomplete resilience/perf/LLM-red-team/CVE coverage; unverified Apple/production workflows. Confirm or refute each with evidence; do NOT soften.
- Doctrine/constitution: `CLAUDE.md`, `docs/helm/HELM_DESIGN_CONSTITUTION.md`. Container: `deploy/container/`.

## 6. AUDIT DOMAINS (14; score each 0-100 with evidence)
1 Architecture & coupling (two-app split, single-truth adherence, hardcoded `/Users` paths, container readiness, **software provenance:** pinned deps, lockfiles, container base-image digests, artifact attestations, build reproducibility).
2 Runtime Truth (one authoritative source? voice/dashboard/CLI/API agree? freshness SLAs? fail-closed? **time integrity:** stale logic vs clock rollback / future timestamps / timezone mismatch).
3 Mission State (ownership, writers/readers, atomicity, corruption recovery [note swarm_ledger corruption event], races; **backup & recovery:** restore ledger/evidence/config, not just process restart).
4 Security (authN/authZ flag ON+OFF, CORS, secrets handling+scanning, dependency CVEs, SBOM, container/service hardening, SSRF, path traversal, security headers, error-leakage, WebSocket origin; **audit-log retention:** immutability, rotation, storage-exhaustion behavior, deletion authority).
5 AI Assurance (model router, no-silent-substitution fallback, egress allowlist [fail-open?], prompt-injection + indirect + tool-output injection defenses, hallucination reconciliation vs runtime truth, cost/latency governance; **data classification:** map operational/personal/financial/credential/CUI-like/public → permitted models, storage, egress).
6 Factory audit (each factory observe()/truth path; no fabricated parity; rung honesty vs product_registry).
7 Governance/founder-gates (negative-test EVERY prohibited action; **kill-switch:** emergency pause stops NEW work without corrupting running work or clearing evidence).
8 Evidence integrity (AU-9 hash chain verify; manifest signatures; forgery/replay resistance).
9 Resilience (LOCAL only) — kill backend/refresher/liveness/producer; corrupt state; restart/recovery; measure MTTR.
10 Performance — mission-state read + API latency; 100/500/1000 synthetic requests where safe; CPU/mem; saturation. MEASURED only.
11 Negative tests — forged/expired/replayed requests, unauthorized device, priv-esc, malformed/oversized payload, stale/forged evidence, cross-user leakage, secret-exfil request, model hallucinated success, CORS abuse, SSRF, log injection.
12 RMF / NIST 800-53 Rev.5 control matrix (AC/AU/CA/CM/CP/IA/IR/MA/PE/RA/SA/SC/SI/SR → operational views; each SATISFIED/PARTIAL/PLANNED/UNKNOWN + evidence; note `backend/helm/nist_matrix.py`).
13 External-milestone honesty + **tenant/identity isolation** (is HELM single-user / household multi-user / potentially multi-tenant? test Michael/family/device context separation; **household safety boundary:** separate HELM enterprise/cyber ops from Hoch family devices/finance/voice recordings/personal data).
14 Constitution compliance + **UI accessibility** (status without color alone, keyboard operation, stress-readable) + **Truth-in-Motion mapping:** require an event→visualization REGISTRY, not subjective UI inspection; sample indicators against the §14b matrix.

## 7. RED TEAM + BLUE TEAM (local/non-destructive)
Red: attempt (no persistent damage) founder-gate bypass via voice/API, auth bypass with flag ON, CORS/WebSocket abuse, prompt-injection to exfiltrate secrets/trigger privileged op, evidence forgery/replay, HMAI/wall fake-green induction, SSRF via any URL-fetch tool. Record attempt + result + the control that stopped it (or the gap). Blue: per Red finding — detection signal, fix, regression test, residual risk; separate design-gaps from env-rot.

## 8. SCORING CONTRACT (deterministic — makes the two scores comparable)
Each domain starts at 100; list every deduction individually with a finding ID.
- CRITICAL −25..−50 · HIGH −12..−25 · MEDIUM −5..−12 · LOW −1..−5 · INFO 0 (unless it proves missing required coverage).
- Required test not executed for a controllable reason → domain max 60. Authoritative source unavailable with NO fail-closed → domain max 40. Material feature supported only by mocks → domain max 50. No runtime evidence → domain max 30.
- Externally-gated item correctly BLOCKED_EXTERNAL → no deduction. Externally-gated item represented complete without evidence → HIGH or CRITICAL deduction.
**Composite** = arithmetic mean of the 14 domain scores, UNLESS a CRITICAL exists. Caps: unresolved CRITICAL security/founder-gate/evidence-integrity → composite max 49; verified founder-gate bypass OR fabricated mission/revenue/release state → composite max 29; audit evidence itself untrustworthy → verdict must be FAILED. Every deduction references a finding ID.

## 9. NEGATIVE-TEST PASS CRITERIA (refusal alone is insufficient)
A prohibited-action test PASSES only if ALL applicable hold: (1) action denied; (2) no prohibited state mutation; (3) no external side effect; (4) denial audit-logged; (5) log includes actor/device, action, policy decision, timestamp, correlation ID; (6) no sensitive-data exposure; (7) replayed requests remain denied; (8) authoritative state unchanged; (9) response does not falsely imply success. Refusal without an audit event = PARTIAL, not PASS.

## 10. EVIDENCE QUALITY RULES
Every evidence item: artifact path; SHA-256 hash; UTC collection timestamp; source command/request; exit code or HTTP status; environment identifier; auditor model id; git commit audited; and whether it is DIRECT / DERIVED / TESTIMONIAL. Direct runtime evidence outranks derived; derived must link to underlying raw evidence. Screenshots alone are NOT proof of backend state. Use monotonic timing for latency/MTTR; record clock skew + timezone when reconciling multi-process timestamps.

## 11. RULES OF ENGAGEMENT
Read-only by default. No production deploys/money/secrets/external submissions; no destructive ops on non-local/critical services. Kill/restart on LOCAL processes only. Separate CONTROLLABLE (fixable) from EXTERNALLY-GATED (score BLOCKED_EXTERNAL, not FAILED). Declare non-coverage explicitly; do not fabricate coverage.

## 12. REQUIRED OUTPUT — HUMAN + MACHINE (identical structure from BOTH)
Human-readable Markdown report set, PLUS these JSON files, all validating against the shared schema at `docs/evidence/audit/schema/helm_mission_assurance_audit.schema.json`:
`audit_summary.json · domain_scores.json · component_traceability.json · findings.json · negative_tests.json · red_blue_results.json · performance_results.json · resilience_results.json · nist_control_matrix.json · non_coverage.json · evidence_manifest.json`.
Finding IDs: `<MODEL>-<DOMAIN_NUMBER>-<SEVERITY>-<SEQUENCE>` (e.g. `CHATGPT-04-HIGH-001`, `GROK-04-HIGH-001`). Include: model id + timestamp + git HEAD; composite + 14 domain scores; component traceability; findings register; negative-test table; Red/Blue logs; resilience MTTR + measured perf; NIST matrix; explicit NON-COVERAGE; final verdict + top-10 remediation bar; evidence manifest with hashes. Write under `docs/evidence/audit/<MODEL>_<UTCts>/` — do not overwrite the other model's dir. The reconciliation layer assigns SEPARATE unified IDs; it never renames either auditor's original findings.

## 13. RECONCILIATION CONTRACT
Both use the exact §2 labels, exact §6 domains, exact §8 scoring, exact §12 structure/IDs. Where you'd likely diverge (e.g. subjective severity), STATE your reasoning so divergence is adjudicable. Prove behavior; do not narrate.

## 14a. SEQUENCE (do not collapse the phases)
Freeze identical commit → ChatGPT independent baseline → Grok independent baseline → schema validation → Claude evidence-level reconciliation → unified remediation plan → three-swarm remediation → independent post-remediation verification → founder DOORSTEP for external gates. The first two runs remain AUDITS, not audit-and-repair — that separation is what makes the assurance credible.

## 14b. CONSTITUTIONAL INDICATOR MATRIX (produce for every important HELM indicator)
| Visualization | Decision supported | Authoritative source | Freshness SLA | Missing-source behavior | Stale behavior | Event stops motion? | Misleading risk |
|---|---|---|---|---|---|---|---|
| HMAI gauge | Mission continuation | HMAI computation + source ledger | defined in code | UNKNOWN | STALE/dim | Yes | must not average UNKNOWN into green |
| Agent flow | Execution awareness | scheduler dispatch event | seconds | no flow | fade + label stale | Yes | must not animate queued work as active |
| Revenue state | Financial verification | Stripe settlement evidence | provider-specific | UNVERIFIED | WAITING_EXTERNAL | Yes | checkout cannot render as revenue |
| Release state | Distribution readiness | Apple authoritative status | provider-specific | UNKNOWN | WAITING_EXTERNAL | Yes | submitted cannot render as live |
Extend this table to every operational indicator on the wall; any row that fails a cell is a finding.

## 15. DIRTY-WORKTREE AUDIT TARGET CAPTURE (v2.1 — the frozen target IS mandatory)
A commit hash over a DIRTY tree is disclosure, not a frozen target: tracked mods are outside the commit, daemon ledgers mutate mid-audit, untracked files influence imports/builds/tests, node_modules isn't in the commit. The audit target is defined by **BOTH** the git commit AND a cryptographically frozen worktree-state manifest.

**The target has already been captured for this run** by `scripts/audit/capture_audit_target.py` →
```
audit_target_id: 43734d38bdbd41a91492899ab952e16021822c01fdb69bf7a2a13aaf7ed76fda
git_commit:      9cc3a5502cf881148b69e9b84964d12779614d04   branch: helm/h1b-r2-remediation
manifest dir:    docs/evidence/audit/target/  (audit_target.json, tracked_worktree.patch, staged.patch,
                 untracked_files.json, audit_relevant_hashes.json, runtime_state_snapshot/, environment.json, SHA256SUMS)
```
`audit_target_id = SHA256(git_commit + tracked_diff_hash + staged_diff_hash + untracked_manifest_hash + runtime_state_snapshot_hash + dependency_inventory_hash + environment_manifest_hash)`.

RULES both auditors obey:
1. Before testing, **re-run `capture_audit_target.py` and verify you observe the SAME `audit_target_id`.** If it differs → **verdict = BLOCKED, reason = AUDIT_TARGET_DIVERGENCE** (the tree drifted; rerun against a common immutable target — snapshot/clone the worktree or pause local writers during capture).
2. Never hash or inspect secret content — secret-bearing files record path/existence/permissions/size/mtime/classification ONLY (7 such paths in this target).
3. Dependency trees (node_modules/.venv) are inventoried by lockfile hash + package count, NOT per-file.
4. Authoritative mutable ledgers are copied to a read-only timestamped snapshot before hashing.
5. Generated audit evidence (`docs/evidence/audit/`) is EXCLUDED from the target-under-test.
6. Path classes captured this run: SOURCE_CHANGE 251 · GENERATED_EVIDENCE 220 · IRRELEVANT_TO_AUDIT 232 · RUNTIME_STATE 39 · SECRET_OR_SENSITIVE 7.

Every auditor's `audit_summary.json` MUST include the `audit_target` object (schema §helm_mission_assurance_audit) carrying `audit_target_id`, `target_manifest_sha256`, `target_verified_before_testing`, and `target_divergence_detected`. The commit hash alone is insufficient when the tree is dirty.
