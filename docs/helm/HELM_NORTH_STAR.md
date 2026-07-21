# HELM — North Star

> ## Status: NORMATIVE DESIGN TARGET
>
> This document describes the **intended** architecture of HELM.
> It is **not evidence** that the architecture has been implemented.
> Implementation status is established only by the governance register,
> execution evidence, and runtime verification artifacts.

```
Document Type:              Architecture Doctrine
Normative Authority:        Founder
Evidence Authority:         Governance Register + Runtime Evidence
Normative Revision:         1
Evidence Snapshot:          Register rev 28
Last Evidence Regeneration: 2026-07-21 (Traversal 2)
```

**Two independent revision streams.** The Normative Revision advances only when the founder
changes sections 1–2. The Evidence Snapshot advances whenever section 3 is regenerated. The
architecture may sit unchanged for months while the evidence section updates weekly; the
document must make that difference visible rather than implying a single version history.

**Authored by:** Michael Hoch (Founder)
**Date:** 2026-07-20
**Recorded contemporaneously** at the point of authorship, per the provenance discipline
established in the PROC-001 review. This document was not reconstructed from memory
afterward.

> **Sections 1 and 2 are NORMATIVE — the design target.**
> **Section 3 is EVIDENTIARY — what has actually been demonstrated.**
> The separation is deliberate. Nothing in sections 1–2 may be read as a claim about
> current capability.

---

## 1. Purpose — NORMATIVE

> HELM exists to autonomously transform intent into verified, governed, evidence-backed
> execution by orchestrating specialized factories, while ensuring that every reported
> state reflects reality rather than assumption.

Stated as a goal:

> HELM is the executive operating system that autonomously converts approved missions into
> verified outcomes by coordinating specialized factories, while preserving runtime truth,
> governance, and founder authority.

**The user should not manage agents. The user should give HELM a mission.**

### Foundational principles

The four are ordered. Each depends on the one above it.

**1. No fake green.** Never report success without supporting evidence. A criterion is DONE
only on authoritative evidence; PARTIAL and PENDING are reported honestly.

**2. Delegation requires attribution.**

> An autonomous system cannot responsibly delegate work it cannot later attribute, audit,
> and verify.

Before factories can execute autonomously, HELM must know **who acted, what they did, why
they were authorized, and what evidence supports the resulting state.** Attribution is not
a governance nicety layered on top of delegation — it is the precondition for it.
Delegation without attribution is not delegation; it is work happening.

**3. Observation is immutable; inference is disputable.** An observation, once recorded, is
never edited. The conclusion drawn from it is a hypothesis that may be refined or
overturned. The evidence does not move when the conclusion does.

**4. Challenge before authority.** No governance-affecting conclusion becomes authoritative
until it has survived structured challenge — with a genuinely independent reasoner where
the decision warrants it (ARCH-001, Level 2).

**Why the order holds.** These are a dependency chain, not a ranking. Each supplies a
prerequisite for the next:

```
No Fake Green                        claims require evidence
        │
        ▼
Delegation Requires Attribution      evidence must be attributable
        │
        ▼
Observation is Immutable;            attributable evidence stays stable
Inference is Disputable              while conclusions improve
        │
        ▼
Challenge Before Authority           conclusions become authoritative
                                     only if they survive challenge
```

Remove any one and the one below becomes unenforceable. Evidence that cannot be attributed
cannot be challenged meaningfully; evidence that can be silently rewritten makes any
challenge unfalsifiable.

This is also why the governance work is not separate from HELM's mission: it establishes
the conditions under which HELM can truthfully claim to operate autonomously.

### Division of responsibility

```
HELM coordinates.
Factories execute.
Council prioritizes.
Founder approves only where governance, credentials, spending,
  signatures, or legal authority require it.
```

HELM does not replace the factories. It governs them.

---

## 2. Execution Model — TARGET ARCHITECTURE

```
Mission
    │
    ▼
Understand Intent
    │
    ▼
Research & Plan
    │
    ▼
Delegate to Factories
    │
    ├── Factory OPERATIONAL
    │         │
    │         ▼
    │   Build / Verify / Package
    │         │
    │         ▼
    │   Govern & Audit
    │         │
    │         ▼
    │   Founder Gates
    │         │
    │         ▼
    │      Deliver
    │
    └── Factory NOT_OPERATIONAL
              │
              ▼
      Classify Blocker
              │
              ▼
     Re-plan / Route to HASF
              │
              └──────────────► Delegate to Factories
```

### Why the failure branch is load-bearing

> Happy paths don't require an executive operating system; they require a scheduler.
> An executive system earns its name by responding correctly when reality contradicts
> the plan.

A loop without a rejection edge will either stall silently or fabricate progress at the
missing step. This branch is not an error-handling detail — it is where orchestration
becomes real, and it is where the council earns its seat. Prioritisation only matters when
something fails and capacity must be reallocated; a council over a happy path is a status
meeting.

### Traversal history

The failure branch is no longer only a design pattern. It has been exercised once:

```
Traversal 1 — 2026-07-20

Mission
    ↓
Delegate to HRF
    ↓
NOT_OPERATIONAL
    ↓
Classify Blocker
    ↓
Route remediation to HASF
```

The correct behaviour was to stop, classify, and route — not to continue to
Build/Verify/Package with a factory that could not execute.

| Traversal | Date | Result | Notes |
|---|---|---|---|
| 1 | 2026-07-20 | Negative | HRF returned `NOT_OPERATIONAL`; blocker classified; remediation routed to HASF. |
| 2 | 2026-07-21 | Positive | `OPERATIONAL_PROVEN`. All 4 declared components executed; offline validator passed. $0.001438. |
| 3 | — | — | Recorded after the next governed execution. |

Traversal 2 closed the blocker Traversal 1 classified — by building the missing runtime
(HRF-RUNTIME-001), not by revising the finding. The loop's remediation edge has now been
walked end to end. Evidence: `coordination/evidence/hrf_traversals/traversal_002.json`.

**Append only.** A negative traversal is never removed once a positive one is recorded.
This log makes the orchestration model falsifiable over time: if later traversals succeed,
the document shows the progression rather than replacing the history that produced it. A
log that only accumulates successes would be a marketing artifact.

### Factory disciplines

| Factory | Discipline |
|---|---|
| HASF | build software — *and builds the other factories* |
| HRF | governed research |
| HCF | cybersecurity, RMF, ConMon, evidence |
| HFF | finance and monetization |
| HMF | music |
| HSF | stories and content |
| HHF | health |
| HPF | personal productivity |

---

## 3. Current Evidence — EVIDENTIARY, as of 2026-07-21

### Demonstrated

- Runtime truth doctrine established
- Governance register through rev 28
- Evidence-first methodology (challenge → re-verify → record)
- `presence ≠ capability` control family identified across four independent controls
- Executable governance lifecycle (`governance_states.py`, state derived not declared)
- Failure branch exercised in practice (Traversal 1 halted correctly)
- **Remediation branch closed** — Traversal 2 `OPERATIONAL_PROVEN` after HRF-RUNTIME-001
- **Governed HRF execution path** — intake, 3 roles, offline validator, budget,
  `SANDBOX_STRICT`, provenance; 20 tests asserting it cannot report unobserved success
- **Independent verification implemented, not just documented** — the Evidence Auditor
  runs on a different model (grok) than Researcher and Synthesis Writer (llama3.2), and
  the fact-check validator is offline and deterministic (ARCH-001 Level 2 in the runtime)
- Canonical repository history established and published (`ebad74ec`)

### Not Yet Demonstrated

- HRF **reliability** — capability shown once; behaviour under repeated execution, load,
  adversarial input, and model outage is UNKNOWN
- HRF correctness for mission types other than the one exercised
- Validated promotion controls (0 of 5)
- End-to-end autonomous delegation
- Complete actor attribution
- Multi-factory execution

### Measured state

```
Mission completion              90.0% (9/10)
Agent-controllable              UNKNOWN
Promotion-control validation     0.0% (0/5)
Promotion                       HOLD
HRF capability                  OPERATIONAL_PROVEN (1 traversal; reliability UNKNOWN)
HRF registry readiness          DEGRADED — deliberately untouched by Traversal 2
Council participation           NOT AUTHORIZED
Working factories               1 of 8 verified (HASF) + HRF path proven once
```

**Registry state was not derived from this run.** `readiness_basis` still reads
`on_disk=True`. Producing execution evidence and updating registry-derived readiness are
separate operations; collapsing them would reintroduce exactly the proxy-for-property
defect GOV-017 recorded.

### The gap, stated plainly

Section 1 describes a system that delegates autonomously. Section 3 describes one that
cannot yet identify who is acting inside it. Both are true. The second is the constraint
on the first — which is precisely what the "delegation requires attribution" principle
predicts, and why the governance work was not a detour from this North Star but a
prerequisite of it.

---

## Amendment protocol

The normative/evidentiary separation is meaningful only if the two halves are governed by
different rules. They are:

**Sections 1–2 — Normative. Founder-controlled.**
Changes require explicit founder authorship, because these sections define intended
architecture and doctrine. Advancing them increments **Normative Revision**.

**Section 3 — Evidentiary. Evidence-derived.**
Content is regenerated from authoritative execution artifacts and governance records.
Manual edits are prohibited except to correct the evidence-generation process itself.
Regenerating it updates **Evidence Snapshot** and **Last Evidence Regeneration**.

> **Section 3 must never be edited to narrow the gap it reports.**

That single clause is what keeps this an evidence artifact rather than a narrative one. The
easiest way to make any status document look better is to quietly revise the part that
reports the shortfall; prohibiting it means the only way to close the gap is to close the
gap.

A credible North Star holds two things true at once: **the destination is clear, and the
current position is honestly stated.** Section 3 exists to protect the second.
