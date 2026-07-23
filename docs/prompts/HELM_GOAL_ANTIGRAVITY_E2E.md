# HELM GOAL — Antigravity IDE End-to-End Qualification Runner

## Mission

Drive HELM from its current repository state to the strongest evidence-supported release disposition achievable under the sealed HELM Governance Specification v1.0.0.

Do not ask the operator for routine implementation choices, file locations, test commands, formatting decisions, dependency repairs, non-destructive refactors, or ordinary remediation sequencing. Inspect the repository, choose the safest deterministic approach, execute it, verify it, and continue.

Do not claim `APPROVED`, `GO`, qualification completion, parity, independence, or evidence closure unless authenticated execution evidence demonstrates the claim. When a requirement cannot be completed because of an external dependency, unavailable runtime, signer, credential, independent reviewer, or elapsed burn-in window, preserve the fail-closed disposition and produce an exact doorstep package for that external gate.

## Governing Model

Use the sealed HELM v1.0.0 authorization model:

- `S` = sealed specification conformance state.
- `Mi = Verify(Ei, P, T, V)` for milestones M1 through M7.
- `Q = M1 AND M2 AND M3 AND M4 AND M5 AND M6 AND M7`.
- `Authorized = S AND Q`.
- `R` = ordered set of unmet qualification predicates.
- `Disposition = f(Authorized, R)`.
- `APPROVED` is valid if and only if `Authorized = TRUE` and `R` is empty.

Treat documentation, plans, dashboards, generated prose, agent confidence, and prior status claims as non-authoritative until supported by authenticated evidence.

## Non-Negotiable Execution Rules

1. Work only inside the repository root unless an existing repository script explicitly requires a temporary directory.
2. Preserve HELM Governance Specification v1.0.0 immutability. Do not silently change normative semantics.
3. Use existing repository commands, lockfiles, scripts, schemas, tests, and evidence formats before inventing replacements.
4. Keep the decision engine as the single authoritative path. Remove or quarantine bypasses, optimistic defaults, fake-green paths, cached approvals, and UI-only authorization logic.
5. Use staged, minimal, reviewable changes. Do not perform destructive history rewrites.
6. Never print, commit, or embed secrets, tokens, private keys, or environment-variable values.
7. Founder-only actions remain founder-only: key provisioning, production signing, spending, submission, deployment, moving money, or external account changes.
8. If a command fails, diagnose the root cause, remediate when safe, rerun the narrow failing test, then rerun the governing suite.
9. Maintain an append-only execution transcript and evidence manifest.
10. Stop only when either:
   - the decision engine computes `APPROVED`; or
   - all internally executable work is complete and the remaining set `R` consists exclusively of explicit external gates with doorstep packages.

## Phase 0 — Repository and Authority Discovery

1. Record branch, commit SHA, dirty state, toolchain versions, operating system, architecture, and UTC timestamp.
2. Locate and inspect:
   - HELM v1.0.0 normative specification and precedence rules.
   - `backend/helm/kernel/decision_engine.py`.
   - canonical JSON profile and artifact-specific canonicalization rules.
   - evidence and qualification schemas.
   - trusted signer and trust-anchor policy.
   - decision ledger and dual-mode ledger verifier.
   - Python, Rust, and Swift verifier implementations.
   - qualification corpus and conformance tests.
   - M1–M7 evidence locations and status records.
   - AG/Antigravity execution hooks, CrewAI runner, CI workflows, dashboards, and release/deployment gates.
3. Build a machine-readable inventory mapping each normative stage to code, tests, scripts, and artifacts.
4. Identify every path capable of creating or displaying a release disposition.

Required output:

- `artifacts/helm_goal/repository_inventory.json`
- `artifacts/helm_goal/authority_path_map.json`
- `artifacts/helm_goal/execution_transcript.md`

## Phase 1 — Baseline Verification

Run the repository-defined installation, lint, schema, unit, integration, conformance, replay, and qualification commands. Prefer documented commands and existing scripts. At minimum, execute all HELM-specific tests and verify the current decision record and ledger.

Record for every command:

- exact command;
- start and end timestamp;
- exit code;
- stdout/stderr log path;
- source revision;
- relevant environment/toolchain versions;
- resulting artifacts and digests.

Do not treat skipped tests as passes. Classify skips as either normatively allowed or an unmet predicate.

Required output:

- `artifacts/helm_goal/baseline_results.json`
- `artifacts/helm_goal/logs/`

## Phase 2 — Specification and Non-Bypassability Audit

Execute the master HELM assurance catalog against the repository. Cover at least:

- specification completeness, consistency, precedence, and undefined behavior;
- single authoritative decision path;
- authorization/disposition separation;
- fail-closed behavior;
- no-fake-green enforcement;
- policy and specification version binding;
- canonicalization and namespace enforcement;
- trust-anchor, signer lifecycle, threshold, and custody-domain checks;
- decision-record and ledger integrity;
- replay determinism and divergence classification;
- evidence traceability, immutability, freshness, independence, and epistemic classification;
- runtime determinism across ordering, locale, time, filesystem, concurrency, and dependency inputs;
- supply-chain, build, release-artifact identity, CI/CD, deployment, rollback, and revocation gates;
- AI/LLM/agent, prompt-injection, tool-output, council, and founder-gate assurance.

For each category, produce one of:

- `PASS` with exact evidence;
- `FAIL` with reproducible defect;
- `BLOCKED_EXTERNAL` with named external dependency;
- `NOT_APPLICABLE` with normative justification.

Required output:

- `artifacts/helm_goal/assurance_matrix.json`
- `artifacts/helm_goal/assurance_matrix.md`

## Phase 3 — Remediation Loop

For each internally remediable `FAIL`:

1. Create a precise defect record with severity, threatened claim, affected invariant, reproduction, and acceptance criteria.
2. Implement the smallest safe correction.
3. Add or strengthen executable regression tests.
4. Run the narrow test.
5. Run the relevant subsystem suite.
6. Run the complete HELM suite.
7. Regenerate affected evidence and records.
8. Recompute the disposition through the authoritative decision engine.

Continue until no internally remediable failures remain.

Never weaken a test, schema, threshold, policy rule, evidence requirement, or fail-closed behavior merely to obtain green status.

Required output:

- `artifacts/helm_goal/defect_register.json`
- `artifacts/helm_goal/remediation_log.md`

## Phase 4 — Seven-Milestone Qualification

Evaluate and execute the milestones in the enforced DAG:

1. M1 — Restore and snapshot the Rust qualification environment.
2. M2 — Execute full Python/Rust/Swift qualification-corpus parity.
3. M3 — Generate authenticated self-describing qualification reports.
4. M4 — Replay and attribute the complete decision ledger.
5. M5 — Produce immutable signed evidence packages.
6. M6 — Execute independent clean-room qualification when an independent runtime/operator is available; otherwise create the complete doorstep package and mark `BLOCKED_EXTERNAL`.
7. M7 — Complete external review and operational burn-in according to the sealed completion criteria; never substitute an assumed duration. If elapsed time or external review remains incomplete, create the exact continuation and attestation package and mark `BLOCKED_EXTERNAL`.

For every milestone record:

- predicate definition;
- required inputs;
- commands;
- toolchain/runtime identity;
- test-vector counts;
- pass/fail/skip counts;
- output artifacts;
- canonical digests;
- signatures and custody domains;
- current Boolean result;
- blocking conditions.

Required output:

- `artifacts/helm_goal/milestone_matrix.json`
- `artifacts/helm_goal/milestone_matrix.md`

## Phase 5 — Negative and Adversarial Qualification

Run isolated tests for at least:

1. missing evidence;
2. malformed evidence;
3. provenance omission or substitution;
4. digest mismatch;
5. invalid, expired, revoked, duplicated, or unauthorized signer;
6. insufficient distinct custody domains;
7. incomplete M6 or M7 evidence;
8. canonicalization failure;
9. policy/specification/profile/procedure/trust-anchor mismatch;
10. Python/Rust/Swift disagreement;
11. decision-record mutation;
12. broken ledger chain;
13. stale-record replay;
14. repository, coordination-bus, CI, and dashboard tampering;
15. prompt injection and generated-evidence substitution;
16. deployment attempt without a fresh matching `APPROVED` record.

Confirm no negative case produces `APPROVED` or an equivalent authoritative green signal.

Required output:

- `artifacts/helm_goal/negative_test_results.json`
- `artifacts/helm_goal/threat_model_results.md`

## Phase 6 — Evidence Packaging and Replay

1. Generate self-describing evidence manifests.
2. Canonicalize and hash each artifact under the correct artifact-specific profile.
3. Verify trust-anchor version and digest binding.
4. Verify signature thresholds and distinct custody domains.
5. Append new records; never rewrite historical records.
6. Run integrity replay from genesis.
7. Run semantic replay under original versions.
8. Confirm clean-environment reproducibility where locally possible.
9. Create external verification instructions for M6/M7 or signer-dependent work.

Required output:

- `artifacts/helm_goal/evidence_manifest.json`
- `artifacts/helm_goal/replay_report.json`
- `artifacts/helm_goal/external_doorstep_package.md`

## Phase 7 — Final Computed Disposition

Invoke the single authoritative decision engine using only authenticated current inputs.

Produce:

- `S`;
- `M1` through `M7`;
- `Q`;
- `Authorized`;
- ordered set `R`;
- operational disposition;
- reason codes;
- verifier consensus state;
- canonical decision-record identifier and hash;
- exact source revision;
- exact evidence-manifest digest.

Required output:

- `artifacts/helm_goal/final_authorization.json`
- `artifacts/helm_goal/final_authorization.md`

The first line of the Markdown report must be exactly one of:

- `AUTHORIZED: YES`
- `AUTHORIZED: NO`

If `AUTHORIZED: NO`, immediately list every unmet predicate and classify it as `INTERNAL_REMEDIATION` or `BLOCKED_EXTERNAL`.

## Phase 8 — External Gate Doorstep Packages

For each remaining external gate, create a directly executable package containing:

- objective;
- required actor and independence constraints;
- exact inputs and digests;
- exact command sequence;
- acceptance criteria;
- expected outputs;
- report schema;
- signing requirements;
- custody-domain requirements;
- verification procedure;
- ingestion location;
- decision-engine rerun command.

Do not ask the operator routine questions. Ask only when a founder-only action, unavailable credential, production signature, independent third-party action, elapsed observation period, or irreversible external operation is strictly required.

## Definition of Done

HELM GOAL is achieved only when one of these terminal states is reached:

### Terminal State A — Authorized

- all required tests pass;
- all M1–M7 predicates are true;
- verifier consensus is complete;
- all evidence is authenticated and current;
- the decision ledger verifies in integrity and semantic modes;
- `R` is empty;
- the authoritative decision engine computes `Authorized = TRUE` and `Disposition = APPROVED`.

### Terminal State B — Internally Complete, Externally Withheld

- every internally executable audit, remediation, test, replay, and evidence-generation action is complete;
- no known internally remediable failure remains;
- every remaining item in `R` is an explicit external gate;
- each external gate has a complete doorstep package;
- the authoritative decision engine remains fail-closed.

Never relabel Terminal State B as GO or APPROVED.
