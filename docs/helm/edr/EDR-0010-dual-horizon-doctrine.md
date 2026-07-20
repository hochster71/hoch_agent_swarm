# EDR-0010 — Dual-Horizon Doctrine and Governance Pre-Claim

> HELM-GOV | extends: `HELM_CONSTITUTION_v1.0.md`, `HELM_DESIGN_CONSTITUTION.md`, `COUNCIL_RUNTIME_CHARTER.md`, EDR-0006 Engineering Doctrine, EDR-0007 Mission Contract | doctrine: Governance-before-Capability | edr: self (EDR-0010) | why: HELM needed a way to build toward a future architecture without minting a second constitution.

- **Status:** PROPOSED — Builder-authored 2026-07-20. **Founder ratification required.**
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` (frozen; **not amended** — this is an overlay).
- **Supersedes:** the "HELM JANUS" program proposal of 2026-07-20, which is adopted in
  substance and rejected in form. See §Decision.1.
- **Related:** `docs/helm/roadmap/W1-002_PRECLAIM.md`, `tests/unit/test_governance_preclaim.py`,
  `coordination/governance/experiment_register_v1.json`.

## Context

A council proposal ("HELM JANUS — Dual-Horizon Recursive Engineering Program") proposed a
parallel program with its own charter, vision corpus, and council. Review found the
engineering substance sound and the **form** structurally wrong on two counts:

1. **Pre-claim failure.** The proposal stated its search found "folder-level references
   rather than substantive architecture documents." The repository contains
   `HELM_CONSTITUTION_v1.0.md`, `HELM_DESIGN_CONSTITUTION.md`, `COUNCIL_RUNTIME_CHARTER.md`,
   `HELM_CANONICAL_RUNTIME.md`, `CONTROL_SURFACE_MAP.md`, and ten EDRs. A governance
   program was designed without reading the governance it would sit beside — the same
   defect the pre-claim rule was written to stop, one layer up.

2. **Inverted dependency.** The proposal's first milestone was the promotion machinery
   (champion/challenger, experiment, promote). Promotion depends on evidence freshness,
   and `W1-002_PRECLAIM.md` established that 46 sites derive evidence age from filesystem
   mtime — including the freshness verifier and both burndown computations. **Two
   candidates cannot be compared when either can appear newer by having its evidence file
   touched.** Freshness sits *below* promotion:

       Evidence Integrity → Freshness → Truth → Champion Evaluation → Promotion

## Decision

1. **Adopt the Dual-Horizon Doctrine as an overlay, not a program.** There remains
   exactly one constitution, one council charter, one canonical runtime, one promotion
   system, one truth model. Two *workstreams*, one governance surface:

   | Workstream | Mission | Authority |
   |---|---|---|
   | **Champion** | make the current runtime reliable and truthful | authoritative |
   | **Horizon** | backcast the future state; build and disprove candidates | experimental; **no production authority** |

   No `docs/vision/` corpus is created. Future-state material lands as EDRs and register
   entries, governed by the chain that exists.

2. **Ratify the founder-authority boundary as constitutional.** HELM may research,
   propose, code, simulate, benchmark, test, package, stage, generate evidence, and
   recommend promotion. HELM **does not autonomously rewrite its production runtime**; it
   develops candidate successors, proves them, and submits them through governed
   promotion gates. Founder-only: spend, credentials, legally binding acts, production
   signing, external submission, money movement, residual-risk acceptance, constitutional
   change.

3. **Horizon work is DEFERRED behind W1-002a–c / REQ-ES-004.** Not because the future
   work is unimportant, but because promotion decisions made on forged freshness are
   worse than no promotion decisions. Horizon may *register experiments* immediately; it
   may not *promote* anything until evidence freshness is trustworthy.

4. **Governance pre-claim (founder rule, 2026-07-20).** *Every strategic or governance
   proposal must pass the same pre-claim verification required of software, evidence, and
   runtime claims.* A proposal must cite the authoritative artifacts it extends, or state
   explicitly that it did not verify them. Governance is evidence-backed engineering, not
   an exception to it. Enforced by `tests/unit/test_governance_preclaim.py`.

5. **Experiments are cost-gated before implementation, not after.** Every register entry
   carries engineering cost, inference cost, expected benefit, expected latency
   reduction, expected reliability gain, risk, compute budget, and approval level. If
   expected value does not exceed expected cost, the entry is `REJECTED` **before**
   implementation. This matters under a ~$200/month external-compute constraint:
   speculative multi-path coding (four candidate implementations per hard decision)
   multiplies spend and must clear the gate before it is registered.

## Evidence

Running the §4 rule against the existing chain (2026-07-20):

| Finding | Count |
|---|---|
| EDRs citing the constitution they extend | 7 / 10 |
| EDRs with **no** constitutional citation | **3** (EDR-0001 ×2, EDR-0002) |
| **Duplicate EDR IDs** | **EDR-0001 used twice** (`-executive-runtime-four-engines`, `-runtime-bridge`) |

The duplicate ID is a governance-chain defect discovered by applying the rule to itself:
two decisions share an identifier, so "EDR-0001" does not resolve to a single decision.
Remediation is a renumber, not a rewrite; it is not blocking and is logged here rather
than fixed silently.

## Scope limits

- **Nothing in this EDR grants Horizon production authority.** It is explicitly
  experimental until §3's precondition clears.
- **The 2030 end-state and five-horizon backcast are not ratified here.** They are
  substantively reasonable and remain UNRATIFIED input; the horizon structure should be
  registered as experiments, not adopted as a roadmap, until Horizon 1 is complete.
- By the JANUS proposal's own Horizon 1 list, HELM is **not** finished with Horizon 1:
  "runtime truth model" and "live observability" are the two items currently broken.
- **Auditor verification has not occurred.** Per EDR-0006 this is UNKNOWN, not complete.

## Reversal

Delete this EDR, the register, and the governance test. Nothing imports them. Cost: zero.
