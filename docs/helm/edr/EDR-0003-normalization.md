# EDR-0003 — Normalization (no architecture change)

- **Status:** PROPOSED (spec). Implementation deferred until independent verification runs (founder sequencing: 1/2/3 in parallel).
- **Author (Builder):** Claude · **Date:** 2026-07-17
- **Reviewers:** Auditor (Grok) — independent verification
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` (RATIFIED). This EDR resolves the Normalization Register + the two conformance-report FAILs. **It changes no architecture** — only duplication, routing, and naming.

## Context
`CONSTITUTION_CONFORMANCE_REPORT.md` returned **CONFORMANT-WITH-NORMALIZATION** with two FAILs that are duplication/naming, not contradictions. This EDR specifies their resolution.

## Decision — four normalization fixes

### N1 — Duplicate EDR-0001 filenames
`docs/helm/edr/` contains both `EDR-0001-executive-runtime-four-engines.md` and `EDR-0001-runtime-bridge.md`.
**Resolution:** the four-engines decision is foundational and precedes the bridge → renumber it **`EDR-0000-executive-runtime-four-engines.md`**; keep `EDR-0001-runtime-bridge.md`. Add a one-line redirect note in the renamed file. No content change.

### N2 — Duplicate `/api/v1/helm/mission` route
Both `bridge_api.py` and `helm_live_api.py` register `GET /api/v1/helm/mission`.
**Resolution:** the **bridge projection** (`_mission_view`) is canonical (versioned + OCC note). Deprecate the `helm_live_api.py` duplicate: either remove it or rename to `/api/v1/helm/mission/legacy` with a deprecation header. Add a regression test asserting a single canonical `/mission` shape (`mission_version` present).

### N3 — Terminology (Constitutional names canonical)
Adopt Constitutional names as canonical; document code aliases in one table:
`Provider Registry` ≡ `provider_router.py` + `role_bindings.json`;
`Runtime Truth Engine` ≡ `truth_engine.py` + `backend/truth/*`;
`Worker Registry` ≡ role bindings + `worker_role_health`.
**Resolution:** add an alias table to the Constitution's Normalization Register (doc-only).

### N4 — `verification_target_id` hashing
Ids forked (`ae02a1b5 → 20afc264 → …`) because EDR prose was hashed alongside code.
**Resolution:** hash **implementation only** (code + config + tests); EDRs and reports *reference* the id, never contribute to it. Freeze one canonical id per verification.

## Acceptance criteria
- `docs/helm/edr/` has no duplicate numbers.
- Exactly one canonical `/mission` route (regression test green).
- Alias table present; no code behavior change.
- Verification manifest hashes implementation only; id stable across doc edits.

## Non-goals
No engine, interface, or principle changes. Purely freeze/dedupe/resolve.

## Verification
Auditor confirms each acceptance criterion; findings → Builder. Implementation lands **after** the independent implementation audit (Phase D), per founder sequencing.
