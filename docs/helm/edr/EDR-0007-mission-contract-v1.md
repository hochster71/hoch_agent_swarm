# EDR-0007 — HELM Mission Contract v1 (the third layer of the prompt stack)

> HELM-GOV | extends: EDR-0006 Engineering Doctrine, Evidence Doctrine (`proof_contract.py`) | doctrine: Governance-before-Capability | edr: self (EDR-0007) | why: HELM had permanent role doctrines and replaceable provider bindings, but no common execution contract for the missions issued against them.

- **Status:** PROPOSED (policy) — Builder-authored 2026-07-18. **Founder ratification required.** Runtime enforcement is additive and currently opt-in (see §Migration). Independent Auditor verification required before any claim of *completion*.
- **Author (Builder):** Claude · **Date:** 2026-07-18
- **Reviewers:** Auditor (Grok) — independent verification required. Founder — ratification of the two policy consequences in §Decision.4.
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` (frozen; **not amended**). Adds an overlay contract; introduces no new runtime and no new truth vocabulary.
- **Related:** `docs/helm/mission/MISSION_TEMPLATE_v1.md` (the contract), `coordination/governance/mission_schema_v1.json` (machine schema), `backend/helm_runtime/mission_contract.py` (enforcement), `backend/security/proof_contract.py` (the ratified truth classification this projects onto), `coordination/governance/role_overlays/` (layer 2), `coordination/governance/role_bindings.json` (layer 3).

## Context

Founder proposal (2026-07-18): restructure HELM's prompts into a "prompt operating
system" — permanent per-role doctrine plus a short runtime mission prompt — rather than
one large system prompt or dozens of unrelated prompts.

Survey of the repository found that **the core principle was already ratified and live**.
`role_bindings.json` states: *"Roles are durable. Provider/model bindings are replaceable…
do not rename the architecture after models,"* and `BUILDER_CLAUDE.md` exists only as a
deprecation stub pointing at `ROLE_BUILDER.md` — evidence that naming doctrines after
models was tried and rejected. Layers 1 (role doctrine) and 3 (provider binding) exist.

**Layer 2 did not.** Missions were seeded ad hoc in mutually incompatible shapes
(`coordination/council/seeded_missions.json` carries `mission_id/factory/name/task_id/
validator_ctx`; `coordination/goal/executive_mission.json` is a 25-key control object;
`coordination/soak/soak_missions.jsonl` is another shape again). Consequences:

- no declared place to say what an agent may write to, or which tools it may use;
- no declared stop conditions, so founder gates were discovered at runtime rather than
  named up front;
- no field carrying the **provenance** of a mission's evidence, so a status could be
  reported without stating what kind of thing produced it.

The founder's revised proposal (12 doctrines → 5 doctrines + deterministic services +
mission overlays) is adopted. This EDR covers **only the overlay contract**. It
deliberately does not add doctrines, does not migrate existing mission sources, and
does not alter the seeding or soak paths.

## Decision

1. **Adopt the Mission Contract v1** as the single execution contract for all HELM
   missions: `docs/helm/mission/MISSION_TEMPLATE_v1.md`, machine-readable at
   `coordination/governance/mission_schema_v1.json`, enforced by
   `backend/helm_runtime/mission_contract.py`.

2. **`SCOPE` and `TOOLS_ALLOWED` are allowlists.** What is not named is denied. An
   empty allowlist is a validation error, never a wildcard. This is what allows one
   Builder doctrine to serve architecture, UI, and runtime work — the specialization
   lives in the mission's scope, not in a new permanent doctrine. It is the mechanism
   by which the governance surface stays at five doctrines while factories multiply.

3. **`TRUTH_SOURCE` is a projection onto the ratified truth classification, not a second
   vocabulary.** `proof_contract.py` already defines OBSERVED / DERIVED / CACHED /
   ASSERTED / UNKNOWN with `ADVANCING = {OBSERVED, DERIVED}`. `TRUTH_SOURCE` names the
   *mechanism* that will produce evidence and maps onto exactly one ratified class:

   | TRUTH_SOURCE | → | advances state |
   |---|---|---|
   | `LIVE_RUNTIME` | OBSERVED | yes |
   | `TEST_EXECUTION` | OBSERVED | yes |
   | `DETERMINISTIC_SCRIPT` | DERIVED | yes |
   | `STATIC_ANALYSIS` | ASSERTED | no |
   | `HUMAN_INPUT` | ASSERTED | no |
   | `UNKNOWN` | UNKNOWN | no |

   `mission_contract.py` imports `Truth` and `ADVANCING` from `proof_contract` rather
   than redeclaring them; a test asserts identity (`mc.Truth is pc.Truth`) so the two
   cannot silently diverge.

4. **Two policy consequences requiring explicit founder ratification.** Both follow
   from the mapping above and are stated here so they are decided, not discovered:

   - **A clean linter or type-check cannot advance a critical node.** `STATIC_ANALYSIS`
     reads source; it is not evidence that the system behaved. This is NO-FAKE-GREEN
     applied to the gap between *code that looks right* and *code that ran*.
   - **Founder attestation cannot advance a critical node either.** `HUMAN_INPUT` maps
     to ASSERTED. Founder authority governs **gates** (spend, keys, release, submission,
     money); it does not manufacture evidence. The rule that stops a model's claim from
     advancing state stops a human's claim by the same mechanism. *Note: the existing
     `app_store_distribution_source: FOUNDER_ATTESTED` field on EPIC_FURY_2026 is exactly
     this class of claim and would be ASSERTED under this contract.*

5. **Declaring a founder gate never authorizes it.** Any mission naming a
   `FOUNDER_GATE` must carry a matching founder-gate stop condition; the validator
   rejects the mission otherwise.

6. **Validation fails closed.** An unparseable, incomplete, or self-contradictory
   mission raises `MissionContractError` and is BLOCKED. No field defaults, no partial
   acceptance. Violations are collected and reported together.


## Amendment 1 — EXECUTION_CONTEXT (2026-07-18, founder-proposed)

Founder proposed an immutable execution fingerprint (`run_id`, `commit_sha`,
`runtime_version`, `doctrine_version`, `mission_schema_version`). **Adopted with one
change:** the field is `correlation_id`, not `run_id`.

`backend/helm_runtime/transaction.py` already mints a `correlation_id` (uuid4) per
mission commit. Introducing `run_id` alongside it would fork the identifier vocabulary
— the same failure mode this EDR avoided for `TRUTH_SOURCE`. `validate_execution_context()`
rejects a `run_id` key explicitly, with a test asserting the rejection.

`transaction_id` and `mission_version` are excluded by design: they are minted at
*write* time, whereas EXECUTION_CONTEXT is captured at *issue* time. Different
lifecycles, kept apart.

**Honesty rule:** any field that cannot be determined is `UNKNOWN` — never guessed or
back-filled. Verified by a test that captures outside a git repository and asserts
`commit_sha == UNKNOWN`.

**Reproducibility reports, it does not block.** An UNKNOWN commit or dirty tree means
evidence is not reproducible from the repository alone. `reproducibility(ctx)` returns
that judgement for the Auditor. It is deliberately non-blocking: the working tree is
routinely dirty during development, and a blocking rule would halt every mission.

### Finding of record — the running certification soak is not reproducible

Captured live against this repository at 2026-07-19T01:07Z:

```json
{"commit_sha": "77102558…", "dirty": true, "reproducible": false,
 "reasons": ["working tree has uncommitted changes"]}
```

The active 6-hour certification run `CERT-6H-20260719T004809Z` (started
2026-07-19T00:48:09Z) is executing against a working tree with uncommitted
modifications, and **HEAD moved during the run** — commits `4972dd64` and `77102558`
both landed after the soak started. Neither modified any code path the soak executes
(the first is a new product directory; the second adds `mission_contract.py`, which
nothing imports yet), so the run's *behavior* is unaffected. But its evidence cannot
be pinned to a single commit, so the certification evidence is **ASSERTED-grade for
reproducibility purposes** even where the missions themselves are OBSERVED.

Recommendation for the next certification run: capture EXECUTION_CONTEXT at soak start
and pin it into `run_meta.json`, and freeze commits for the duration. Not retrofitted
to the running soak — interrupting a certification to improve its metadata would
destroy the evidence it exists to produce.

## What this EDR does NOT do

- It does **not** add any permanent role doctrine. `ROLE_SECURITY_RMF.md` remains
  unwritten until a security mission requires it (founder roadmap item 3).
- It does **not** migrate `seeded_missions.json`, `executive_mission.json`, or
  `soak_missions.jsonl` (roadmap item 4). A non-raising `conformance()` survey is
  provided so the gap can be measured before anything is changed.
- It does **not** touch the dispatch, scheduler, soak, or certification paths.
- It creates no new runtime. Enforcement is a library, called where a mission is issued.

## Acceptance criteria

1. `mission_contract.validate()` rejects each of: a missing required field, an unknown
   `TRUTH_SOURCE`, an unknown founder gate, a founder gate without a stop condition,
   `EDR_REQUIRED=YES` without an EDR output, an empty allowlist, and a non-sanctioned
   `RETURN`. **[met — `tests/test_mission_contract.py`, 22 passed]**
2. `Truth`/`ADVANCING` are imported from `proof_contract`, asserted by identity test.
   **[met]**
3. `may_return_done()` refuses DONE for STATIC_ANALYSIS, HUMAN_INPUT and UNKNOWN.
   **[met]**
4. `SCOPE` prefix matching does not leak into sibling directories
   (`products/hff-recurring` must not permit `products/hff-recurring-charges/…`).
   **[met]**
5. The JSON schema and the Python enforcement agree on every enum and on the full
   projection table. **[met — asserted by test]**
6. `EXECUTION_CONTEXT` reuses `correlation_id`, rejects a forked `run_id`, records
   UNKNOWN rather than inventing, and reports (never blocks) reproducibility.
   **[met — 12 further tests]**
7. Independent Auditor verification of 1–6. **[NOT MET — required before completion]**
8. Founder ratification of §Decision.4. **[NOT MET — required]**

## Migration

- **Phase 1 (this EDR, additive):** contract, schema, validator, tests, EDR. Nothing
  in the existing mission path calls the validator yet. Zero blast radius.
- **Phase 2 (proposed):** run `conformance()` across all existing mission sources and
  publish the gap report. Measurement only.
- **Phase 3 (proposed):** new missions are issued through the contract. Existing
  sources gain an adapter rather than being rewritten in place.
- **Phase 4 (proposed):** the governance engine refuses a DONE whose recorded truth
  class is outside `ADVANCING`. Requires Auditor sign-off; this is the phase with real
  blast radius and it is deliberately last.

## Reversibility

Phase 1 is four new files and one new test file. Reverting is deleting them; no
existing behavior depends on them.
