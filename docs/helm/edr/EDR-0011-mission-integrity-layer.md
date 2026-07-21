# EDR-0011 — Mission Integrity Layer (Phase 1: Mission Traceability Graph)

> HELM-GOV | extends: EDR-0000 Four Engines, EDR-0006 Engineering Doctrine, EDR-0007 Mission Contract, `config/canonical_goal_contract.json` | doctrine: Governance-before-Capability · Observability-before-Governance | edr: self (EDR-0011) | why: HELM can prove controls pass; it cannot yet prove every execution still advances GOAL.

| Field | Value |
|---|---|
| Status | PROPOSED (Phase 1 implemented as observability; founder ratification + Auditor verification required before any claim of completion) |
| Date | 2026-07-21 |
| Author role | builder |
| Bound actor | Grok (Builder lane) |
| Mission id | GOAL-NS / EPIC-FURY-2026 (platform spine) |
| Correlation id | EDR-0011-MISSION-INTEGRITY-P1 |
| Parent EDR | EDR-0000, EDR-0006 |

## Context

HELM is strong at **control integrity** (validators, freshness, Proof Records, Mission Contracts/Envelopes). It is weaker at **mission integrity**: continuous proof that work still advances the founder’s GOAL rather than merely that tests are green.

Founder direction (2026-07-21): introduce a Mission Integrity Layer. Highest-priority first capability is the **Mission Traceability Graph**. Phase 1 is **observability only** — seed the graph, detect orphans, prove determinism — and **must not** drive completion percentages, prioritization, or promotion.

## Decision

1. **Adopt Mission Integrity as a first-class subsystem** that integrates across the four engines (Mission Runtime, Runtime Truth, Governance, Event Bus). It is **not** a fifth peer engine and does **not** amend the Constitution.

2. **Phase 1 ships only the Mission Traceability Graph** (seed + orphan report + reproducible `graph_hash` + standalone verifier). Later governors (Mission Hash, Drift Budget, Goal Delta, MAV enforcement, Mission Council, dashboard scoring) are **out of scope** until Phase 1 is Auditor-verified and stable.

3. **Canonical chain for Phase 1:**
   ```
   Goal → Requirement → Claim → Evidence → Graph (read-only artifact / API later)
   ```

4. **New invariant (alongside presence-detection):**
   > No execution may claim to advance GOAL unless it can trace that claim through an unbroken chain of requirements, implementation, runtime evidence, and mission intent.
   >
   > *Phase 1 does not enforce this on commits or dispatch; it measures and reports breaks.*

5. **Non-consumption rule (hard stop):** Phase 1 SHALL NOT register a new `goal_requirements` entry, SHALL NOT modify completion %, prioritization, or promotion consumers. Downstream consumption requires a later EDR amendment after A1–A9 verification.

6. **Placement:** composed extension `backend/helm_runtime/extensions/mission_traceability.py` (not frozen core `d8d5139a`). Durable projection: `coordination/governance/mission_trace_graph.json`.

## Phase 1 Acceptance Criteria (A1–A9)

These criteria **are** the definition of done for Phase 1. Independent verification (Auditor) checks them objectively.

| # | Criterion | Requirement |
|---|---|---|
| A1 | Goal→Requirement | Every Goal has at least one Requirement |
| A2 | Requirement→Claim | Every Requirement maps to at least one Claim |
| A3 | Claim→Evidence | Every Claim maps to at least one Evidence source (PRESENT, MISSING, or UNKNOWN — never silent PASS) |
| A4 | Orphans explicit | Every orphan is reported explicitly in `orphans[]` |
| A5 | Missing links | Missing links render UNKNOWN, never PASS |
| A6 | Reproducible hash | Graph hash is reproducible across identical inputs |
| **A7** | **Determinism** | Repeated execution over identical inputs **SHALL** produce an identical `graph_hash` |
| **A8** | **Read-only guarantee** | Phase 1 **SHALL NOT** modify runtime state, mission state, promotion state, completion percentages, prioritization, or governance decisions. Allowed writes: `mission_trace_graph.json` and optional verify reports only |
| **A9** | **Independent verification** | A standalone verifier **SHALL** reproduce `graph_hash` and orphan detection **without importing Mission Control** (`backend.mission_control.*` forbidden in the verifier import graph) |

### Negative proof (N1–N6)

| # | Case | Expected |
|---|---|---|
| N1 | Malformed graph input | Verifier fails closed; never PASS |
| N2 | Orphan / broken chain | Orphan reported; structural check fails |
| N3 | Duplicate node IDs | Rejected / reported; never silent merge to green |
| N4 | Hash instability | Mutating any node/edge **must** change `graph_hash` |
| N5 | Tampered graph | Verifier fails when on-disk hash ≠ recomputed hash |
| N6 | Mission Control import | Verifier has no `backend.mission_control` import |

## Alternatives considered

1. **Fifth engine “Mission Integrity Runtime”** — rejected; fragments the four-engine model (EDR-0000).
2. **Wire graph into goal_engine completion immediately** — rejected; violates observability-before-governance and risks fake green from incomplete seed.
3. **Full Mission Council + MAV enforcement in one ship** — rejected; expands scope before measurement is proven.

## Consequences

+ Continuous Goal→Requirement→Claim→Evidence visibility; orphan work becomes explicit.
+ Objective A1–A9 / N1–N6 bar for Auditor.
− Graph may surface many honest MISSING/UNKNOWN evidence links at first seed (expected, not failure of the graph).
− Later phases required before governance consumption.

## Evidence

- `backend/helm_runtime/extensions/mission_traceability.py`
- `scripts/goal/build_mission_trace_graph.py`
- `scripts/goal/verify_mission_trace.py`
- `tests/unit/test_mission_traceability.py`
- `coordination/governance/mission_trace_graph.json` (projection artifact)
- `coordination/goal/MISSION_TRACE_PHASE1_COMPLETION.md` (completion report)

## Constitution check

- [x] Runtime truth first — graph is a derived projection
- [x] No fake green — missing links UNKNOWN; no completion wiring
- [x] Founder gates untouched
- [x] Dashboard remains projection only (Phase 1 has no required UI write)
- [x] Frozen constitutional core untouched
