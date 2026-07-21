# HELM Doctrine — Evidence Mechanisms vs Enforcement Mechanisms

**Status:** PROPOSED (unratified — requires an EDR)
**Authored:** 2026-07-20, from the PROC-001 review cycle
**Origin:** three commits landed during active review leases; the last opened a lease under
another session's asserted identity. No repository-local control stopped any of them.

---

## The distinction

A governance artifact stored in the repository can **record** that something happened. It
cannot **prevent** it. These are different guarantees and must never be conflated.

### Repository-local controls — EVIDENCE

`commit_lease.json` · `review_lease.json` · `review_drift_gate.sh` ·
`promotion_candidate_cas.sh` · `FREEZE.json` · `open_claims_register.json`

Provide:

- **Detection** — drift is observed and classified
- **Evidence** — what was pinned, when, against which bytes
- **Coordination** — actors sharing a convention can serialize work

Do **not** provide:

- **Enforcement** — every one of these files is writable by the actor it constrains

A lease asserting `commit_authority: EXCLUSIVE` is a claim, not a control. During this cycle
that exact claim was made and then violated three times, and a lease was opened under a
session identity that did not create it. The `owner_session` field does not merely fail to
prove ownership — it *permits false attribution*, because it is self-declared and
unauthenticated.

### GitHub branch protection — ENFORCEMENT

Provides:

- **Enforcement** — unauthorized updates to the protected ref are refused by the hosting
  platform, not by a file the actor can edit

Enforcement is not absolute. It is **relocated** to a different authority. Anyone who can
authenticate with sufficient repository permission can still alter or remove protection.
That is expected: administrative authority ultimately rests with repository administrators.
The gain is that the boundary now sits in an authenticated authorization system rather than
in mutable repository content.

---

## Two orthogonal rules

They constrain different things and neither substitutes for the other.

| Rule | Governs |
|---|---|
| Epistemic states | **What may be concluded** from the evidence in hand |
| Control lifecycle | **How far a conclusion may advance** along Specified → Validated |

### Epistemic states

| State | Evidence basis | Permissible conclusion |
|---|---|---|
| Observed Present | positive observation | Present |
| Observed Absent | negative observation | Absent |
| **Unobserved** | no observation | **Unknown** |

`Not observed` ≠ `observed not to exist`. Use UNOBSERVED unless an examination actually
occurred and returned a negative result. This is easy to lose in wording even when it is
understood: this repository's own actor inventory recorded `isolation: NONE OBSERVED` for a
property never examined, which reads as a negative finding. Corrected to `UNOBSERVED`.

### Bidirectional inference guard

Applies wherever a boundary is inferred from an adjacent one. Both directions are invalid:

```
shared OS account        does NOT establish   shared key custody
distinct execution ctx   does NOT establish   isolated key custody
```

Sandboxing is not custody separation, and a shared account is not shared custody — Secure
Enclave, Keychain ACLs, and separate security principals can partition key access *within*
one account. A shared account is **necessary but not sufficient**. Each boundary requires
its own observation.

---

## Rules

1. **Never describe a repository-local artifact as enforcing anything.** Use
   `enforcement: DETECT_ONLY` and `mechanical_exclusivity: ABSENT` where applicable.
2. **A control that constrains an actor must not be writable by that actor.** If it is, it is
   evidence, not enforcement — label it so.
3. **Identity fields are unauthenticated unless derived from a verified principal.** Git
   author/committer reflects local git config and cannot distinguish actors. Do not claim a
   session or agent identity that is not derived from an authenticated principal, a signed
   attestation, or a protected automation identity.
4. **Adding more repository-local controls inside an untrusted control plane increases
   evidence volume without increasing assurance.** When the writer boundary is the defect,
   fix the boundary.
5. **Separate the lanes.** Development branches may move freely. The promotion lane is
   protected. Freezing all development to protect a review is the wrong trade.

---

## A second axis: technical controls vs epistemic controls

The evidence/enforcement split above concerns *mechanisms*. A separate axis concerns
*conclusions*. Both were exercised in this cycle, and confusing them hides real defects.

### Technical controls — constrain or detect system behaviour

Branch protection · compare-and-swap · drift detection · immutable commit pinning ·
snapshot hashing.

They answer: **"Can the system prevent or detect this class of change?"**

### Epistemic controls — constrain what reviewers may conclude

- Verify a capability before assuming it.
- Resolve full object identity before rebinding anything.
- Re-read the committed bytes before accepting *or rejecting* a finding.
- Distinguish observation from inference.
- Leave state `UNKNOWN` when evidence is insufficient.

They answer: **"What do we actually know?"**

A technical control cannot repair an epistemic failure, and vice versa. Of the four failure
modes below, only the first is partly technical; the rest are review-process failures that
would survive any amount of additional tooling. `MUTUAL_DEFERENCE_WITHOUT_BYTE_RECHECK` in
particular was not a software bug — no script was wrong. Two careful parties each deferred
to the other's conservatism and a false finding nearly became the record. Naming it is the
control.

---

## Failure modes named during this cycle

| Class | Description |
|---|---|
| `UNVERIFIED_COUNTERPARTY_CAPABILITY_ASSUMPTION` | Designing a protocol around a capability the counterparty environment was never asked to confirm. Occurred three times: worktree outside the mount, reviewer without a mount, reviewer without network. |
| `UNVERIFIABLE_SESSION_ATTRIBUTION` | An identity field that is self-declared and therefore forgeable. |
| `MUTUAL_DEFERENCE_WITHOUT_BYTE_RECHECK` | Both parties defer to the other's conservatism; a false claim enters the record because neither returned to the committed bytes. |
| `DETECTOR_DERIVED_FROM_IMPLEMENTATION` | A check specified against one known fix rather than against the defect class, so a different valid fix reads as unremediated. |

---

## Controls have a lifecycle

Classify every control against five states. Do not treat "present" as binary.

```
Specified → Configured → Enforced → Sustained → Validated
```

- **Specified** — described in a design artifact
- **Configured** — settings actually applied
- **Enforced** — the system refuses violations, not merely records them
- **Sustained** — continuously in force since the last audit
- **Validated** — an adversarial attempt was made and failed

The last state is not a formality. It is the only one that demonstrates the trust boundary
holds under a condition it was built to resist.

### Assurance ladder

Each layer adds assurance; only the final one demonstrates the intended behaviour.

| Control | Assurance | Demonstrates |
|---|---|---|
| Distinct git identity | Low | Cooperative observability — forgeable by any process in the domain |
| Commit signing | Medium | Integrity, and possession of *a* key |
| Isolated key custody | High | Resistance to actor impersonation |
| Negative impersonation test | Validation | That the boundary actually holds |

This is why configuration alone cannot close GOV-007. Configuration reaches `Configured`.
Closure requires `Validated`.

This repository reached the first state reliably, the second occasionally, and the third not
at all. Three independent instances, found in a single review:

| Control | Reached | Current |
|---|---|---|
| RC23 branch protection | Designed (runbook, 2026-06-28) | Not confirmed applied |
| Commit signing | Designed (specified in that runbook) | Not configured — 0 verifiable signatures in 1200 commits |
| Per-agent git identity | Designed **and Enabled** (3 commits, 2026-07-17) | Lapsed within 3 days |

The diagnosis this changes: the problem was not absent architecture. Every control needed
had already been designed, and one had been practised. What is missing is an operational
process that keeps controls enabled across time.

### The asymmetry that makes this hard to audit

`Designed` and `Enabled` are **point-in-time observable** — read the doc, read the config.
`Sustained` is **not**. It is a property of an interval, and no single observation can
establish it. A control that is enabled at the moment of audit and disabled the following
week passes every point-in-time check ever run against it.

Therefore: an audit that asks "does this control exist?" cannot detect the failure mode
found here. It must ask "has this control been continuously enforced since the last audit?"
— which requires either continuous monitoring or an immutable record of the control's state
over time. Auditing sustainment with a snapshot is the same category error as establishing
content identity with a freshness window.

**Snapshots certify state. Histories certify behaviour.**

| Property | Snapshot-verifiable? |
|---|---|
| Specified / Configured / Enabled | Yes |
| Sustained / Continuously enforced / Validated | No — interval properties |

### Verdict rule

Any property defined over an interval cannot be established by evidence collected at a
single instant. When only snapshot evidence exists, the strongest defensible conclusion is
a snapshot conclusion. A sustainment claim without interval evidence is **UNKNOWN — not
true, not false.**

This is the same rule the mission runtime already applies to telemetry: unknown propagates
until evidence collapses it. What this review adds is that the rule governs *governance
controls themselves*, not only the data they oversee. An auditor asserting "continuously
enforced" from a single reading commits the identical error as a collector reporting
HEALTHY from a stale heartbeat.

### What this makes the external anchor for

An external anchor is not merely immutable storage. It is the mechanism that converts
interval claims into verifiable evidence, by recording state transitions **as they occur**.
Without it, no amount of later documentation can establish sustainment — only that
sustainment was believed.

---

## Verification classes (do not mix)

- **PROMOTION VERIFICATION** — byte identity against a pinned, immutable SHA.
- **RUNTIME HEALTH** — freshness window against a live source.

A freshness window supports monitoring. It can never establish that two reviewers evaluated
the same content.

## Review invalidation classes (do not merge)

- **Candidate-byte invalidation** — the reviewed bytes moved. Findings do **not** carry over.
- **Promotion-binding invalidation** — the world moved around a still-valid review. Findings
  **do** carry over; git commit objects are immutable. Rebind before promoting.
- **Environment unavailable** — a required oracle could not be consulted. No byte drift is
  proven; this is not a review failure and must not be recorded as one.
