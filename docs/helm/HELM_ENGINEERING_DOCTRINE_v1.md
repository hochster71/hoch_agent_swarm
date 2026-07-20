# HELM ENGINEERING DOCTRINE v1.0 — canonical runtime policy

> HELM-GOV | extends: `coordination/policy/HELM_EVIDENCE_DOCTRINE.md` (peer) + N1 governance (`governance_engine.py`) | doctrine: Governance-before-Capability | edr: EDR-0006 | why: the canonical doctrine text adopted by EDR-0006; defines the Proof Record, the six properties, and Definition of Done.

### Adopted by Founder Michael Bryan Hoch (2026-07-18) via `docs/helm/edr/EDR-0006-engineering-doctrine.md`. Status: ENFORCED (with declared gaps).

## North Star
> **HELM shall optimize for governed, explainable, traceable, evidence-backed decisions before
> optimizing for additional capabilities.**

Success is no longer measured by capability. It is measured by the number of decisions HELM can
**Explain · Justify · Trace · Verify · Audit · Reproduce.**

**A feature without governance is incomplete. Governance is part of feature completion — not
documentation after completion. The runtime shall ENFORCE governance, not merely describe it.**

Two standing rules inherited from the founder and the Evidence Doctrine:
- **Unknown is preferable to unsupported certainty.**
- **Evidence before status. Governance before capability. No Fake Green.**

---

## The Constitutional Runtime (what this is, and is not)
This doctrine is enforced by the **Constitutional Runtime**, which is **not a new runtime**. It is
the governance integration layer that composes and governs HELM's *existing* runtime through **one
authoritative governance path**. The objective is **governed runtime, not more runtime** — Integrate ·
Simplify · Govern · Continuously Prove. See `docs/helm/HELM_RUNTIME_ARCHITECTURE_v1.md` for the
engineering specification and the real module behind each named component.

---

## Governing rule
> **NO MATERIAL DECISION MAY BE TREATED AS GOVERNED WITHOUT A VALID PROOF RECORD.**

This extends the Evidence Doctrine (*"no claim may advance state; only fresh machine-verifiable
evidence may"*). Evidence proves a *fact*; a Proof Record proves a *decision* — that it was
authorized, explained, traced, proven, audited, and reproducible.

## The Proof Record — the six properties as fields
Every material runtime decision carries a Proof Record so it is provable **without reconstructing
history from logs.** The single definition lives in `backend/helm_runtime/governance_manifest.py`.

| Property | Field | Sourced from (already in HELM) |
|---|---|---|
| **Authorized** | `authorized{authority,decision_id,gate}` | `governance_engine.py`, `authority_gateway.py` |
| **Explained** | `explanation` | decision rationale (council/founder record) |
| **Traced** | `trace{correlation_id,input_digests}` | `event_bus.py`, gateway digests |
| **Proven** | `proven{proof_command,exit_code,evidence_hash}` | `proof_contract.py` |
| **Audited** | `audit{record_hash,prev_hash}` | hash-chained ledgers, `evidence_chain.py` |
| **Reproduced** | `reproducibility{tested_commit,environment}` | Evidence Doctrine reproducible-PASS |
| (classification) | `evidence_class` | OBSERVED/DERIVED/CACHED/ASSERTED/UNKNOWN |
| (state) | `governance_state` | GOVERNED / NEEDS_MIGRATION / UNKNOWN |

A record missing any required property classifies `UNKNOWN` — **never** assumed complete. Only
`OBSERVED`/`DERIVED` evidence contributes to governance coverage; `ASSERTED`/`UNKNOWN` contribute zero
(prevents governance theater).

## Definition of Done (governance is completion)
A feature or decision is **complete** only when its Proof Record validates to all six properties.
This is the runtime success criterion, encoded as a `GOVERNANCE` gate in the goal/champion gates and
asserted by `tests/test_engineering_doctrine.py`. "Done" without a valid Proof Record is `UNKNOWN`,
not done.

## Single authoritative path
Every material decision resolves through **one** gate:
`governance_engine.govern_decision(proof_record)`. The write path (N1), dispatch (N6), and the
Evidence Resolver (`proof_contract.may_advance_state`) **call** it — they do not re-implement it.
Governance logic is never duplicated. (EDR-0006-R2.)

## Continuous proof
Governance is **monitored, not claimed.** N8 ConMon (`backend/security/helm_conmon.py`) re-derives
`governance_coverage` on each run and emits a POA&M when it falls below target. Acceptance criteria
are measurable and live in EDR-0006 §Acceptance criteria.

---

## Rollout (ratchet to global — evidence-triggered, never expectation-triggered)
1. **Phase 1 — Govern all NEW decisions; fail closed immediately.** New material decisions require a
   valid Proof Record to advance state. Legacy untouched.
2. **Phase 2 — Classify legacy** as VERIFIED / NEEDS_MIGRATION / UNKNOWN. Legacy is **never** promoted
   to GOVERNED without migration. Classification is an append-only side index; originals never rewritten.
3. **Phase 3 — Migrate factories incrementally.** Each factory inherits the governance gate-set and is
   proven before it counts as covered.
4. **Phase 4 — Founder approval → global fail-closed.** Only with the founder's approval and migration
   evidence in hand does enforcement extend to all decisions, legacy included.

## Declared gaps (this doctrine will not fake its own completion)
- **OBSERVED (as of adoption):** the Proof Record primitive and the single gate exist and pass their
  negative controls; NEW decisions fail-closed (Phase 1).
- **ASSERTED / not yet global:** legacy artifacts are classified but most are `NEEDS_MIGRATION`/`UNKNOWN`
  until migrated; global fail-closed is a **separate Phase 4 founder gate** and is not claimed as done.
- Until the independent Auditor confirms the acceptance criteria against fresh evidence, this doctrine
  is enforced for what Phase 1 covers and honestly declares the rest pending.

## Cross-references
- Evidence basis: `coordination/policy/HELM_EVIDENCE_DOCTRINE.md`, `backend/security/proof_contract.py`.
- Adoption + testable requirements: `docs/helm/edr/EDR-0006-engineering-doctrine.md`.
- Architecture + Proof Record schema + sequence diagrams: `docs/helm/HELM_RUNTIME_ARCHITECTURE_v1.md`.
- Substrate: `docs/helm/HELM_MISSION_RUNTIME_ARCHITECTURE.md`, `docs/helm/HELM_CONSTITUTION_v1.0.md` (frozen).
