# HELM EVIDENCE DOCTRINE — canonical runtime policy
### Ratified by founder Michael Bryan Hoch. Status: ENFORCED (with declared gaps).

## Governing rule
> **NO CLAIM MAY ADVANCE STATE.**
> **ONLY FRESH, MACHINE-VERIFIABLE EVIDENCE MAY ADVANCE STATE.**

A model statement is not evidence. A machine-observed result is evidence. This is the
behavioral layer HELM was missing, and it is now code, not prose.

---

## Enforcement controls (executable)

| Control | Meaning | Enforced by |
|---|---|---|
| **PROOF-CONTRACT-001** | A task cannot become READY without goal · mechanism · proof_command · binary acceptance · constraints · failure_behavior | `backend/security/proof_contract.py::ProofContract.validate` |
| **NO-SUBSTITUTION-001** | A missing required mechanism yields a **typed blocker** (BLOCKED/FAILED), never an unapproved workaround | same — `failure_behavior` rejected if it permits substitute/workaround/infer |
| **FRESH-EVIDENCE-001** | A PASS expires when its evidence exceeds its freshness window; stale OBSERVED → CACHED → cannot advance | `Evidence.effective_class` + `may_advance_state` |
| **NEGATIVE-CONTROL-001** | A high-assurance validator must prove it can **reject a broken state** | `negative_control_passed` required before advance |

**Proven, not asserted:** 10/10 negative controls pass — incomplete contract rejected,
substitution rejected, ASSERTED/UNKNOWN/stale-CACHED all blocked, missing negative-control
blocked, missing tested_commit blocked, and only fresh+complete+OBSERVED advances. The
redactor's own negative control caught a crash-bug in the redactor before it shipped —
which is the doctrine catching itself.

---

## Proof contract (required for READY)
```json
{
  "goal": "Observable end state",
  "mechanism": "Permitted implementation path",
  "proof_command": "Machine-executable verification",
  "expected_result": "Binary success condition",
  "constraints": ["Forbidden actions", "Security boundaries"],
  "failure_behavior": "Return BLOCKED or FAILED; do not substitute",
  "freshness_window_seconds": 300
}
```

## Truth classification (only OBSERVED / valid DERIVED may advance a critical node)
| Class | Meaning |
|---|---|
| **OBSERVED** | Produced by a current command, API call, or runtime event |
| **DERIVED** | Mechanically computed from OBSERVED evidence |
| **CACHED** | Previously OBSERVED but outside the active freshness window |
| **ASSERTED** | Supplied by a model, operator, or static file without independent proof |
| **UNKNOWN** | No reliable evidence exists |

## Reproducible PASS — every field required
proof command · exit code · raw output (restricted) · **sanitized** rendering ·
timestamp · tested commit · environment · **evidence hash** · **negative control executed**

## Freshness windows (FRESH-EVIDENCE-001, examples)
| Evidence | Window |
|---|---|
| API health proof | 5 min |
| daemon heartbeat | 90 s |
| dependency scan | 24 h |
| App Store review status | 1 h |
| release artifact hash | immutable |

---

## Evidence handling — DO NOT paste raw output (founder correction, adopted)
"Paste the raw output" leaks secrets into chat, terminal history, model context, logs,
screenshots and committed evidence. Instead:
```
command > raw-proof.log 2>&1
python scripts/evidence/redact_evidence.py raw-proof.log > proof.sanitized.log
```
Preserve: **raw** → local restricted storage (chmod 600, never committed) · **sanitized**
→ HELM package · **sha256(raw)** → HELM package.

## Credential handling — do NOT test-by-reuse (founder correction, adopted)
A discovered credential must **not** be exercised to "prove revoked" — deliberately using
a compromised credential is a second security event. Required chain:
```
credential discovered
  → classify exposure
  → identify owner + environment
  → revoke / rotate through the AUTHORIZED mechanism
  → verify old-credential rejection ONLY where safe
  → verify replacement via a minimal, scoped call
  → record incident + remediation evidence
```
A security audit is **not** unlimited file access. Scanning shell history, home
directories, or unrelated repos requires **explicit authorized scope**.

---

## Canonical prompt ending (append to every HELM task)
> Execute the work and prove the observable end state with a live machine check. Capture
> the command, exit code, sanitized output, timestamp, environment and tested commit. Run
> a negative control showing the check fails when the condition is broken. If any required
> step cannot be completed, return a typed blocker — do not infer success, fabricate
> evidence, or substitute an unapproved workaround.

## Session closeout format (every agent session ends with this)
```
GOAL:
TESTED COMMIT:
ENVIRONMENT:
CHANGES MADE:
PROOF COMMANDS: 1. 2. 3.
RAW RESULTS: exit codes · sanitized output · timestamps
NEGATIVE CONTROLS: test · expected failure · observed failure
OBSERVED:
DERIVED:
CACHED:
ASSERTED:
UNKNOWN:
SECURITY EXCEPTIONS:
MANUAL INTERVENTIONS:
UNPROVEN CLAIMS:
NEXT EXECUTABLE ACTION:
FINAL DECISION:
```

---

## Declared gaps (this doctrine will not fake its own completion)
- **OBSERVED**: `proof_contract.py` + `redact_evidence.py` exist and pass their negative
  controls (this commit).
- **ASSERTED / not yet wired**: the live scheduler (`persistent_scheduler.py`) and PERT
  binding do not yet *call* `may_advance_state()` as a hard gate on node advancement. Until
  they do, this doctrine is enforced for any task that opts in, not globally. That
  integration is the next executable action, and it is not claimed as done.
