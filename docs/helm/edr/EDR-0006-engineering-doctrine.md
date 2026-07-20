# EDR-0006 — HELM Engineering Doctrine v1.0 (Governance is part of feature completion)

> HELM-GOV | extends: N1 write-path governance (`governance_engine.py`), Evidence Doctrine (`proof_contract.py`) | doctrine: Governance-before-Capability | edr: self (EDR-0006) | why: the governing record that adopts the Engineering Doctrine and defines its testable requirements — authored before any enforcement code references it (Founder Directive #10).

- **Status:** ACCEPTED (policy) — **Founder-ratified 2026-07-18**. Adoption record for HELM Engineering Doctrine v1.0. Runtime enforcement implemented in phases (see §Migration). Independent Auditor verification of the acceptance criteria still required before any claim of *completion*.
- **Author (Builder):** Claude · **Date:** 2026-07-18
- **Reviewers:** Auditor (Grok) — independent verification required before any claim of completion.
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` (frozen; **not amended** — Founder Directive #12). Governs operational engineering conduct; adds a governance-integration layer, **not** a new runtime.
- **Related:** `coordination/policy/HELM_EVIDENCE_DOCTRINE.md` (peer, extended), `docs/helm/HELM_ENGINEERING_DOCTRINE_v1.md` (the doctrine), `docs/helm/HELM_RUNTIME_ARCHITECTURE_v1.md` (the spec), `docs/helm/HELM_MISSION_RUNTIME_ARCHITECTURE.md` (four-engine substrate).

## Context

Founder decision (2026-07-18, APPROVED): adopt the **HELM Engineering Doctrine v1.0**. Its
North Star — *HELM optimizes for governed, explainable, traceable, evidence-backed, auditable,
reproducible decisions before optimizing for additional capability.* Its rule — **"A feature
without governance is incomplete. Governance is part of feature completion. The runtime shall
ENFORCE governance, not merely describe it."**

HELM already contains most of the required substrate: the four-engine runtime
(`backend/helm_runtime/`), the N1–N8 PERT subsystems, the Evidence Doctrine enforced by
`backend/security/proof_contract.py` (`may_advance_state`), hash-chained ledgers, `correlation_id`,
input/output digests, and the OBSERVED/DERIVED/CACHED/ASSERTED/UNKNOWN truth classification. What
is missing is a **single authoritative governance path** that binds every *material runtime
decision* to a machine-checkable **Proof Record**, so a decision is provable without reconstructing
history from logs.

Founder architectural direction (integrated): the **Constitutional Runtime is not a new runtime** —
it is the governance integration layer that composes and governs the existing runtime through one
authoritative path. The objective is **governed runtime, not more runtime**: Integrate · Simplify ·
Govern · Continuously Prove — *not replace*.

## Decision

Adopt the Engineering Doctrine as **ENFORCED runtime policy** (peer to the Evidence Doctrine),
implemented as a governance integration layer over the existing runtime. The following **numbered,
testable requirements** define the implementation. Each is verified by
`tests/test_engineering_doctrine.py` and/or continuous proof (N8 ConMon).

- **EDR-0006-R1 — Proof Record primitive.** A single shared schema+validator
  (`backend/helm_runtime/governance_manifest.py`) defines the Proof Record: `authorized`,
  `explanation`, `trace`, `proven`, `audit`, `reproducibility`, `evidence_class`,
  `governance_state`. It is the *only* definition of the shape (prevents duplication — Directive #1/#5).
- **EDR-0006-R2 — Single authoritative gate.** `governance_engine.govern_decision(proof_record)` is
  the *one* function that validates a decision's Proof Record and classifies it
  `GOVERNED | NEEDS_MIGRATION | UNKNOWN`. No subsystem may implement a parallel governance gate.
- **EDR-0006-R3 — Evidence Resolver delegates, never duplicates.**
  `proof_contract.may_advance_state(...)` delegates its governance decision to `govern_decision`;
  the Evidence Doctrine's existing controls (PROOF-CONTRACT-001, FRESH-EVIDENCE-001, etc.) remain the
  evidence basis.
- **EDR-0006-R4 — N6 dispatch routes through the gate.** `scripts/council/gateway.py` and
  `backend/dispatch/council_router.py` emit a Proof Record via `govern_decision` on every **new**
  material decision. Missing fields ⇒ `UNKNOWN` (not GOVERNED); the daemon does not crash.
- **EDR-0006-R5 — Replayable proof.** Every material event carries its Proof Record in the existing
  `Event.evidence[]` (`backend/helm_runtime/event_bus.py`), so the append-only event log *is* the
  governance replay.
- **EDR-0006-R6 — Fail-closed for NEW decisions (Phase 1).** From Phase 1, a new material decision
  without a valid Proof Record **cannot advance state**. Legacy artifacts are untouched until
  classified/migrated (§Migration).
- **EDR-0006-R7 — Continuous proof.** N8 ConMon (`backend/security/helm_conmon.py`) re-derives
  `governance_coverage` each run and emits a POA&M when below target — governance is *monitored*, not
  asserted.
- **EDR-0006-R8 — Governance is completion.** A feature/decision is "complete" only when its Proof
  Record validates to the six properties (Authorized · Explained · Traced · Proven · Audited ·
  Reproduced) **without reconstruction from logs**. Encoded as a `GOVERNANCE` gate in the goal/champion
  gates (Phase 4).
- **EDR-0006-R9 — Repository traceability.** Every new/modified file carries a `HELM-GOV` marker
  naming: why it exists · which subsystem it extends · which Doctrine principle it satisfies · which
  EDR-0006 requirement it implements (Directive #9).
- **EDR-0006-R10 — Extend before create.** No new runtime component is added unless it documents why
  existing capability is insufficient, why extension cannot satisfy the requirement, and how it
  reduces overall complexity (Directive #2/#5). The only new runtime module is R1's shared schema,
  justified because it *removes* duplication across R2/R3/R4.

## Consequences
- **Positive:** one authoritative governance path; decisions provable inline; governance surfaced as a
  live metric; factories inherit governance by declaration; no parallel stack; Constitution untouched.
- **Work implied:** the Proof Record primitive (R1), gate wiring (R2–R5), continuous proof (R7),
  legacy classification + factory migration (Phases 2–3), and the global fail-closed flip (Phase 4).
- **Interim posture:** until Phase 4, enforcement is **new-decisions-only**; legacy is classified,
  never silently promoted. Declared honestly in the doctrine's *Declared Gaps* (No Fake Green).

## Migration (Founder Directive #7, four phases)
1. **Phase 1** — Govern all NEW runtime decisions; fail closed immediately (R1–R7).
2. **Phase 2** — Classify legacy artifacts VERIFIED / NEEDS_MIGRATION / UNKNOWN; legacy never becomes
   GOVERNED without migration (append-only side index; originals never rewritten).
3. **Phase 3** — Migrate factories incrementally (R-inheritance); each factory proven before covered.
4. **Phase 4** — Founder approval → global fail-closed enforcement + `GOVERNANCE` completion gate (R8).

## Acceptance criteria (measurable — Founder Directive #10)
- **AC-1:** 100% of NEW material decisions emitted after Phase 1 carry a schema-valid Proof Record
  (asserted by `tests/test_engineering_doctrine.py`; fail-closed proven by 6 negative controls, one
  per property).
- **AC-2:** Exactly one governance gate exists — a test asserts no second `govern_*`/authorize path
  classifies decisions (R2). Grep-based structural test.
- **AC-3:** 0 legacy artifacts classified `GOVERNED` without a migration record (Phase 2 invariant).
- **AC-4:** `governance_coverage` is re-derived by N8 ConMon each run and its trend is monotonic
  non-decreasing across runs (Phase 2+).
- **AC-5:** No historical ledger file is modified by classification/migration (`git status` clean on
  `*.jsonl` originals).
- **AC-6:** Constitution v1.0 file is byte-unchanged by this EDR (frozen — Directive #12).

## Verification
Auditor (independent) confirms, against fresh evidence paths — not assertions: (a) the single-gate
invariant (AC-2); (b) fail-closed behavior for new decisions (AC-1) via the negative controls; (c)
legacy is classified, not promoted (AC-3); (d) continuous proof runs and trends (AC-4); (e) no
originals rewritten and Constitution frozen (AC-5, AC-6). Until the Auditor confirms, this EDR is
PROPOSED and no completion is claimed. **Unknown remains preferable to unsupported certainty.**
