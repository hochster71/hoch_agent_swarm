# Governed commit plan — 2026-07-19 audit/remediation session

**Problem:** the working tree holds ~232 pre-existing changes PLUS this session's remediation.
One broad commit would destroy reviewability and rollback. This plan isolates the session's
work into five coherent, individually revertable units. **Execute in order** (each unit's
tests ran green in this session; re-run per unit at commit time). Pre-existing unrelated
changes are NOT included here — they need their own curation pass.

**Constitutional attestation (applies to every unit):** none of the 17 frozen files
(manifest d8d5139a) is modified by any unit. Units 2–5 verify this via
`tests/helm_runtime/test_extensions.py::test_frozen_constitutional_reader_and_binding_file_unchanged`.
The five frozen files RESTORED during A7 remediation return the tree to HEAD state for those
paths — they will show as unmodified and need no commit.

**Signing:** if commits are signed, verify with `git log --show-signature` before claiming
it. Do not describe a commit as signed otherwise.

---
## Unit 1 — Dependency optionalization + A3 evidence
Files: `pyproject.toml`, `uv.lock`, `docs/helm/LEGACY_CREWAI_FACTORY_RUNBOOK.md`,
`coordination/evidence/sbom_cve_20260719/**`, `coordination/goal/findings/CHROMADB_RISK.json`
Tests: full default-lane suite (`pytest tests/ -q`); `uv lock` reproducibility; default export excludes crewai/json-repair/chromadb
Evidence: `default_audit.json` (0 findings/90 pkgs), `uv.lock.pre_optionalization`
Holds: json-repair + chromadb OPEN in legacy lane; runtime confirmation pending
Suggested message: `deps(a3): optionalize crewai factory lane; default runtime 90 pkgs / 0 CVE findings; pillow 12.3.0; segmented legacy findings`

## Unit 2 — A7 remediation: frozen-core restore + composed extensions
Files: `backend/helm_runtime/extensions/{__init__,constitutional_gate,model_routing}.py`,
`coordination/model_routing/role_bindings.json`, `coordination/governance/extensions/edr_0006_policy.json`,
rewired: `backend/helm_runtime/{governed_emit,knowledge_engine}.py`, `backend/dispatch/council_router.py`,
`backend/security/{proof_contract,helm_conmon}.py`, `scripts/{verify_engineering_doctrine_ac,fire_doctrine_auditor}.py`,
evidence: `coordination/evidence/a7_drift_20260719/**`
Tests: doctrine 18/18; evidence-scope 40/40; manifest re-hash 17/17
Holds: Grok composed-runtime review pending; GOVERNED_COMMIT_INLINE_PROOF partial
Suggested message: `fix(a7): restore frozen core d8d5139a; extract EDR-0006 gate + model routing to composed extensions; preserve drift evidence`

## Unit 3 — Reader migration + structural authorization tests + defect fix
Files: `backend/voice/command_router.py`, `backend/audit_factory/service.py`,
`tests/helm_runtime/test_extensions.py`, `tests/test_engineering_doctrine.py`,
`coordination/goal/findings/{ROUTING-REGISTRY-DUAL-READ,VOICE-AGENT-ROLE-ENUMERATION}.json`
Tests: 117/117 incl. authorized-reader exception + rejection-telemetry cases
Holds: final CLOSED_WITH_CONSTITUTIONAL_EXCEPTION awaits lane rerun
Suggested message: `fix(routing): migrate mutable readers to governed resolver; fix voice role-enumeration schema bug; enforce single-frozen-reader exception structurally`

## Unit 4 — Goal/audit engine hardening
Files: `scripts/goal/goal_engine.py` (interpreter probe + failure-class taxonomy),
`scripts/helm_goal_runner.py` (verdict guard `_effective_status`), `scripts/helm_audit_runner.py` (`_py()` probe),
`scripts/founder/asc_credentials_gate.py`, `scripts/goal/run_dependency_runtime_confirmation.sh`
Tests: py_compile all; goal-engine honest recompute 85.0% verified clean-room
Holds: engine re-run on Mac pending
Suggested message: `fix(goal-engine): interpreter probing, 9-code failure taxonomy, verdict guard revoking fake DONE; add founder ASC gate + dep runtime confirmation`

## Unit 5 — Truth-state + adjudication records
Files: `coordination/goal/{helm_pert,build_to_goal_status,audit_adjudication_20260719,helm_truth_snapshot_20260719}.json`,
`coordination/goal/findings/GOVERNED_COMMIT_INLINE_PROOF.json`, `coordination/products/product_registry.json` (revenue_class),
`coordination/evidence/external/stripe_settlement.json`, `docs/helm/AUDIT_REMEDIATION_LEDGER.md`, this file
Tests: JSON validity; PERT recompute 85.0%
Holds: audit lane RECONCILIATION_PENDING; N3 HOLD; production authority HOLD
Suggested message: `truth(goal): revoke GOAL_REACHED; adjudicate A1-A7; segmented A3; FOUNDER_TEST_REVENUE label; consolidated snapshot`

---
After all five: push the exact reviewed commits, then run the Grok composed-runtime review
**against those commit SHAs** so the independent verdict binds to immutable provenance.
