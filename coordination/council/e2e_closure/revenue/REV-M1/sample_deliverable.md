# AI Agent Governance Assessment — Sample Deliverable

**Subject system:** HELM / Hoch Agent Swarm — an 8-lane autonomous agent factory
**Assessed:** 2026-07-14 · **Framework:** NIST SP 800-53 Rev. 5 · ConMon per SP 800-137
**Architecture views:** DoDAF 2.02 (OV-1, SV-1, StdV-1)

---

## Why this sample is our own system

Most vendors show you a redacted case study about an anonymous client. We won't, because you can't
verify it — and neither can you verify the vendor's willingness to report a failure.

**This is the assessment we ran on ourselves.** Every finding below is real, every number is
computed from an executed check, and the two open findings are ours. If we were willing to bury a
HIGH finding in our own audit-log integrity to make a sales document look cleaner, you should not
let us anywhere near your ATO package.

Hold us to exactly this standard.

---

## 1. Posture

**11 of 13 controls IMPLEMENTED — 84.6%. Two open findings, one HIGH.**

```
[███████████████████░░░]  84.6%
```

Posture is computed **only** from executed checks. A control with no evidence is recorded
`NOT_IMPLEMENTED` — never assumed, never inferred, never defaulted to pass.

---

## 2. Open findings

### AU-9 — Audit information is not tamper-protected · **HIGH** · OPEN

The evidence plane — execution ledgers, lease ledgers, verification ledgers — is append-only *by
convention*, not by enforcement. A process with filesystem access can rewrite history.

For a system whose entire claim is evidentiary integrity, **this is the sharpest gap in the
architecture, and it is ours.**

**Remediation:** hash-chain each record to its predecessor; seal each execution package with a
digest bound to a commit; verify the chain on read and fail closed on a break.

### SR-3 — No supply-chain control on model/tool provenance · MEDIUM · OPEN

Model endpoints and CLI tools are invoked without provenance attestation. A substituted model or
tool binary would not be detected.

---

## 3. The defect class this assessment exists to catch

All four were found in HELM itself. This is what you are paying us to find in yours.

| Defect | Why it matters |
|---|---|
| **A ledger that could not record failure.** `release_lease()` returned False; the scheduler discarded the result and wrote `RELEASED` anyway. | Every "0 leaked leases" metric came from an instrument **structurally incapable of reporting a leak** — 256 acquired / 236 released in the ledger while 14 lock files sat on disk marked ACTIVE. A green metric from a blind instrument is worse than no metric. |
| **Dashboards that could not be wrong.** 40 of 58 UI surfaces contained **zero API calls**; one had 101 hardcoded "COMPLETE / 100% / OPERATIONAL" strings. | Not stale — **structurally incapable of reporting failure.** They would have shown green with the machine on fire. |
| **An observer that cleared its own alarms.** An auto-quarantine, self-authorized by a 5-minute burn-in, moved operational artifacts and then reported `state_mutated: false`. | Governance that can silently mutate what it observes is not governance. Now fail-closed: mutation requires an approved policy ID. |
| **False-reds.** Partial progress painted FAILED; `$0` revenue painted FAILED; a 3-second probe declaring a healthy 8.6-second endpoint dead. | A false alarm is **not** the safe failure mode. It burns trust and hides the real defects underneath it. |

**Common root cause in every case: the measurement was narrower than the claim.**

---

## 4. Control boundaries (DoDAF OV-1)

Five zones. Every arrow crossing a boundary is a **privilege transition**.

| Zone | Control | Enforcement |
|---|---|---|
| **FOUNDER AUTHORITY** | AC-6 | credentials · signing · money · release approval — **never delegated to an agent** |
| **GOVERNED CORE** | SC-7 | mission → decision corpus (RATIFIED only) → lease manager (`O_EXCL` + monotonic fencing token) → **single dispatch chokepoint** → spend meter |
| **FACTORY TIER** | AC-3 | 8 production lanes; work enters **only** through the chokepoint holding a valid lease |
| **EVIDENCE PLANE** | AU-2 / **AU-9 GAP** | append-only ledgers · independent read-only observer · sealer independent of the runner |
| **EXTERNAL BOUNDARY** | **SR-3 GAP** | payment rail · app store · customer |

**No agent can reach the External Boundary.** Money movement, credential entry, signing and
release submission terminate at the Founder zone and cannot be delegated — architecturally, not
by policy.

---

## 5. Control matrix

| Control | Family | Status | Evidence |
|---|---|---|---|
| AC-3 | Access Control | IMPLEMENTED | Scoped evaluator: blocks bind to capability, not the whole lane |
| AC-6 | Access Control | IMPLEMENTED | Spend authority gated pre-dispatch |
| AU-2 | Audit | IMPLEMENTED | Append-only execution ledgers |
| **AU-9** | **Audit** | **NOT_IMPLEMENTED** | **HIGH — ledgers not tamper-protected** |
| CA-7 | Assessment | IMPLEMENTED | Continuous monitoring (SP 800-137) |
| CM-3 | Config Mgmt | IMPLEMENTED | Change control; commit-bound runtime identity |
| CP-10 | Contingency | IMPLEMENTED | Recovery + reconstitution under fault injection |
| IA-2 | Identification | IMPLEMENTED | Webhook HMAC; authority binding |
| RA-5 | Risk | IMPLEMENTED | Vulnerability monitoring |
| SA-11 | Acquisition | IMPLEMENTED | Independent sealer; negative-control tests |
| SC-7 | Sys & Comms | IMPLEMENTED | Single dispatch chokepoint; no bypass path |
| SI-4 | Integrity | IMPLEMENTED | Runtime observation, fail-closed |
| **SR-3** | **Supply Chain** | **NOT_IMPLEMENTED** | No model/tool provenance attestation |

---

## 6. What you receive

**Rapid Assessment — $2,500 · 5 days**
Privilege-boundary map · executive gap summary

**Full Technical Assessment — $5,000 · 10 days**
Privilege-boundary map · AI threat model (OWASP LLM mapping) · NIST 800-53 gap ledger with
control-to-evidence traceability · DoDAF OV-1 / SV-1 / StdV-1 views · executive summary

---

## 7. The standard we hold ourselves to

> **No fake green. No unevidenced completion. Missing evidence is UNKNOWN — never PASS.**

An assessment that cannot return a failing verdict is not an assessment.

If your system is sound we will say so, and you will be able to prove it. If it is not, you will
hear it from us before you hear it from an auditor, an adversary, or a headline.

We found our own HIGH finding and put it on page one of our sales document. **That posture is what
you are buying.**

---

*A synthetic worked example (fictional client, illustrative findings) is available at
`sample_deliverable_TEMPLATE.md`. It is clearly labelled as synthetic and is not evidence of any
engagement.*
