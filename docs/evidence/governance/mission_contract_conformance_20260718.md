# Mission Contract v1 — conformance survey (measurement only)

Generated 2026-07-18 by `backend/helm_runtime.mission_contract.conformance()`.
**Nothing was migrated.** This measures the gap for EDR-0007 Phase 2 / founder roadmap item 4.

## Strict conformance

| source | conforms | required fields present |
|---|---|---|
| `coordination/council/seeded_missions.json` | no | 0 / 15 |
| `coordination/soak/soak_missions.jsonl` | no | 0 / 15 |
| `coordination/goal/executive_mission.json` | no | 0 / 15 |

Strictly zero, because no existing source uses the contract's field names or casing.

## Semantic gap (does an equivalent concept exist under any key?)

| source | concept present | genuinely absent |
|---|---|---|
| `seeded_missions.json` | 3/15 — MISSION_ID, TITLE, SCOPE | OWNER, ROLE, OBJECTIVE, SUCCESS_CRITERIA, EXPECTED_OUTPUTS, TOOLS_ALLOWED, EDR_REQUIRED, FOUNDER_GATES, STOP_CONDITIONS, EVIDENCE_REQUIRED, TRUTH_SOURCE, RETURN |
| `soak_missions.jsonl` | 3/15 — MISSION_ID, EVIDENCE_REQUIRED, RETURN | TITLE, OWNER, ROLE, OBJECTIVE, SUCCESS_CRITERIA, EXPECTED_OUTPUTS, SCOPE, TOOLS_ALLOWED, EDR_REQUIRED, FOUNDER_GATES, STOP_CONDITIONS, TRUTH_SOURCE |
| `executive_mission.json` | 7/15 — MISSION_ID, TITLE, ROLE, OBJECTIVE, FOUNDER_GATES, EVIDENCE_REQUIRED, RETURN | OWNER, SUCCESS_CRITERIA, EXPECTED_OUTPUTS, SCOPE, TOOLS_ALLOWED, EDR_REQUIRED, STOP_CONDITIONS, TRUTH_SOURCE |

## Findings

1. **`TRUTH_SOURCE` is absent from all three.** No existing mission records the
   provenance of its own evidence. This is the field with no incumbent equivalent
   anywhere, and the strongest argument for the contract.
2. **`SCOPE` and `TOOLS_ALLOWED` are absent from the two paths that actually run
   agents** (seeded + soak). Agents are currently dispatched without a declared
   write boundary or tool allowlist; the boundary exists only in doctrine prose.
3. **`STOP_CONDITIONS` is absent everywhere.** `executive_mission.json` has
   `external_gates`, which names founder gates but does not bind them to a stop.
4. **`executive_mission.json` is the closest incumbent (7/15)** and is the sensible
   first adapter target. The two agent-dispatch paths are further away.

## Recommended sequencing (unchanged from EDR-0007 §Migration)

Adapters, not rewrites. `executive_mission.json` first because it is closest and is a
control object rather than a hot path; `soak_missions.jsonl` last because it feeds
certification runs and carries the most blast radius.
