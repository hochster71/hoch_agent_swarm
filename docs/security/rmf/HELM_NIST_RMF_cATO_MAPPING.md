# HELM Autonomous Executive Operating System — NIST SP 800-53 Rev. 5 & AI RMF Control Mapping (Sprint 9)

## 1. Executive Summary & Regulatory Scope

This document defines the machine-verifiable compliance mappings for HELM (`v1.0.0 NORMATIVE`) against:
- **NIST SP 800-53 Rev. 5** (Security and Privacy Controls for Information Systems and Organizations)
- **NIST AI RMF 1.0** (Artificial Intelligence Risk Management Framework)
- **NIST SP 800-218** (Secure Software Development Framework - SSDF v1.1)
- **NIST SP 800-137** (Information Security Continuous Monitoring - ISCM)
- **cATO Framework** (Continuous Authorization to Operate)

---

## 2. NIST SP 800-53 Rev. 5 Control Mapping Matrix

| Control ID | Control Family & Title | Implemented HELM Capability | Evidence Produced | Verification Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **`CM-2`** | Configuration Baseline | RFC 8785 canonical JSON serialization & SHA-256 baseline hashing | `golden_mission_contract_v1.json` digest (`11463524...`) | `scripts/helm/canonical_json.py` |
| **`CM-3`** | Configuration Change Control | Normative change classification (`EDITORIAL` through `BREAKING`) | `docs/governance/HELM_GOVERNANCE_SPECIFICATION_v1.md` | `tests/unit/test_helm_governance_conformance.py` |
| **`CM-7`** | Least Functionality | Fail-closed preflight promotion engine; rejection of unverified inputs | `WITHHELD_UNVERIFIED_PROVENANCE` code | `backend/helm/kernel/decision_engine.py` |
| **`SI-2`** | Flaw Remediation | Parser hardening; NaN, Infinity, non-string key rejection | Security Qualification Report (`CHECK-01`, `CHECK-02`) | `tests/security/test_helm_security_qualification.py` |
| **`SI-7`** | Software & Information Integrity | Domain-tagged SHA-256 lifecycle transition hash chain (`HELM-CONFORMANCE-TRANSITION-V1\n`) | `docs/helm/conformance_report.json` hash continuity | `scripts/helm/verify_transition_history.py` |
| **`AU-2`** | Event Logging | Append-only tamper-evident governance ledger logging | `coordination/security/conmon_ledger.jsonl` | `scripts/helm/l6_operational_telemetry_daemon.py` |
| **`AU-10`** | Non-Repudiation | Provenance dominance rule; explicit cryptographic attribution | Signed decision envelopes | `coordination/proofs/helm_l5_cross_language_qualification_report.json` |
| **`AU-12`** | Audit Record Generation | Automated generation of self-authenticating evidence packages | `coordination/proofs/helm_r6_security_qualification_report.json` | `scripts/helm/generate_security_qualification_report.py` |
| **`SC-8`** | Transmission Confidentiality & Integrity | Cross-language differential byte identity (Python / Rust / Swift) | 509/509 test vector zero-divergence proof | `scripts/helm/l5_cross_language_qualifier.py` |
| **`SC-13`** | Cryptographic Protection | Standard SHA-256 hashing & RFC 8785 UTF-16 lexicographical key sorting | Zero-dependency cryptographic core | `scripts/helm/canonical_json.py` |
| **`SC-28`** | Protection of Information at Rest | Tamper-evident transition hash verification | `verify_transition_history.py` pass status | `scripts/helm/verify_transition_history.py` |

---

## 3. NIST AI RMF 1.0 Mapping Matrix

| AI RMF Function | Sub-category ID | Implemented HELM Risk Control | Automated Verification Evidence |
| :--- | :--- | :--- | :--- |
| **`GOVERN`** | **Govern 1.1** | Legal & regulatory policy baseline codified in frozen specification | `HELM_RELEASE_DECISION_RECORD.md` change control rules |
| **`GOVERN`** | **Govern 1.2** | Human-in-the-loop founder authority binding and decision gates | `coordination/founder/authority_binding_ledger.jsonl` |
| **`MAP`** | **Map 1.1** | Context and deployment constraints modeled in JSON schema contracts | `schemas/helm/golden_mission_contract_v1.schema.json` |
| **`MAP`** | **Map 2.1** | Autonomous swarm boundary risk categorization | STRIDE Threat Model (`docs/security/HELM_THREAT_MODEL_STRIDE.md`) |
| **`MEASURE`** | **Measure 1.1** | Deterministic metrics; latency p50/p95/p99, ops/sec throughput | `coordination/proofs/helm_r7_performance_qualification_report.json` |
| **`MEASURE`** | **Measure 2.2** | Property-based metamorphic fuzzing & mutation testing | `tests/fuzz/test_helm_fuzzer.py` (8/8 PASS) |
| **`MANAGE`** | **Manage 1.1** | Fail-closed release withholding upon SLO violation or P0 finding | `REJECTED_SLO_VIOLATION` & `REJECTED_OPEN_P0` |
| **`MANAGE`** | **Manage 2.3** | Real-time continuous error budget frozen state enforcement | `FROZEN_ERROR_BUDGET` decision code |

---

## 4. Continuous Authorization to Operate (cATO) Evidence Architecture

The cATO Evidence Package (`coordination/proofs/helm_cato_evidence_bundle.json`) binds:
1. **Source Attestation**: Parent commit SHA & clean-tree verification (`PARENT_COMMIT_ATTESTATION_V1`).
2. **Security Qualification**: 7 Tests mapped to 6 Checks (`CHECK-01`..`CHECK-06`).
3. **Performance Qualification**: 7 Workload Baselines & 8 Closure Tests (`PERF-001`..`PERF-008`).
4. **Governance Traceability**: `GOV-001`..`GOV-006` mapped to specification and unit tests.
5. **OSCAL Artifacts**: Machine-readable Component Definition, SSP Fragments, Assessment Results, and POA&M.
