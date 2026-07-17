# RMF / Control Matrix — HELM OMEGA ASSURANCE AUDIT v1.0

**Rule:** No control marked SATISFIED without direct evidence observed this audit or a named prior artifact whose integrity is still trustworthy.

Legend: **S** Satisfied · **P** Partial · **M** Missing · **NA** N/A · **U** Unverified

---

## NIST SP 800-53 Rev. 5 (sampled; NOT full catalog)

| Control | Title | Status | Evidence | Residual |
|---|---|---|---|---|
| AC-3 | Access Enforcement | **P** | ScopedStateEvaluator; founder write token; **GET unauth** | Read path |
| AC-6 | Least Privilege | **P** | Spend caps; capability gates tests PASS | Broad agent tools |
| AU-2 | Event Logging | **P** | Many jsonl ledgers | Completeness unknown |
| AU-9 | Protection of Audit Info | **P** | Hash chains present; full recompute not done | Algorithm trust |
| AU-10 | Non-repudiation | **P** | Founder decision chain claims | Token secrecy |
| CA-7 | Continuous Monitoring | **P** | conmon + seals; stale packages | Freshness gaps |
| CM-3 | Config Change Control | **M/P** | Hooks exist; **dirty tree contradicts clean claim** | Reproducibility |
| CP-10 | Recovery | **P** | Historical SIGKILL fencing proof cited | Not re-run |
| IA-2 | Identification & Auth | **P** | Founder token; product auth tests exist; HELM GET open | Read auth |
| RA-5 | Vuln scanning | **P** | Static verifiers claimed (49); CVE scan not run | Dependencies |
| SC-7 | Boundary protection | **P** | Egress gateway claims; LAN residuals | Network |
| SI-4 | System monitoring | **P** | Numeric fallback findings historical PARTIAL | Fallbacks |
| SR-3 | Supply chain | **P** | SBOM scripts; tool attestation PARTIAL historically | SLSA U |

**Full 800-53 catalog:** **NOT ASSESSED** → any claim of complete coverage is **INVALID**.

Posture file 13/13 “implemented” → **REJECTED as enterprise RMF satisfaction**.

---

## NIST AI RMF

| Function | Status | Notes |
|---|---|---|
| Govern | **P** | Doorstep, doctrine, authority policy |
| Map | **P** | Factories, goals, risks partially mapped |
| Measure | **P** | Validators, seals; incomplete TEVV |
| Manage | **P** | Quarantine, supersession, fail-closed |

---

## NIST SSDF (800-218) — abbreviated

| Practice | Status | Evidence |
|---|---|---|
| Secure development process | **P** | tests, hooks, gitleaks config |
| Produce well-secured software | **P** | product tests; not all factories |
| Respond to vulnerabilities | **U** | process not proven this audit |
| Provenance | **P** | supply scripts; not verified live SLSA |

---

## OWASP ASVS (level claim)

No ASVS level certification evidence found. **U / NOT CLAIMED.**

---

## OWASP LLM Top 10

See Security Report §5 — majority **U/P**, none fully **S**.

---

## SLSA Assessment

| Level idea | Status |
|---|---|
| Source version control | **P** (git; dirty tree) |
| Build service | **P** (GHA present) |
| Provenance generation scripts | **P** (package.json supply:*) |
| Provenance verification enforced on deploy | **U** |
| Hardened build multi-party | **U / likely M** |

**SLSA level achieved (this audit): UNVERIFIED — scripts present ≠ level attestation.**

---

## Control Satisfaction Summary

| Status | Count (sampled rows above) |
|---|---:|
| Satisfied (S) | **0** (strict: none fully closed end-to-end this audit) |
| Partial (P) | Majority |
| Missing (M) | CM-3 clean claim; full catalog |
| Unverified (U) | CVEs, SLSA enforce, ASVS, many LLM items |

Strict interpretation deliberately avoids fake green.
