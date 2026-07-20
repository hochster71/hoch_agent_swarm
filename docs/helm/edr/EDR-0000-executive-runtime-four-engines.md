# EDR-0000: Four-engine Executive Runtime + model-agnostic roles

*Note: Renamed from EDR-0001 to EDR-0000 per EDR-0003 §13-15 to resolve filename collision.*

| Field | Value |
|---|---|
| Status | ACCEPTED |
| Date | 2026-07-17 |
| Author role | builder |
| Bound actor | Claude |
| Mission id | EPIC-FURY-2026 |
| Correlation id | EDR-0000-FOUR-ENGINES |
| Parent EDR | none |

## Context
HELM drifted toward peer model conversations and a fuzzy “Runtime/Truth actor.” Truth is derived; Runtime is platform. A single “Runtime” blob mixed coordination, truth, governance, and events.

## Decision
1. Platform = HELM Executive Runtime with **four engines**: Mission Runtime, Runtime Truth Engine, Governance Engine, Event Bus.  
2. Actors only: Founder, Orchestrator, Builder, Auditor.  
3. Versioned Executive Mission + transaction semantics for material writes.  
4. Model-agnostic `ROLE_*.md` + `role_bindings.json`.  
5. Dashboard/voice are projections of computed truth—not sources.

## Alternatives considered
1. Keep model-named overlays only — rejected (brittle to GPT-6/Claude-N).  
2. Keep “Truth” as a seat on a council — rejected (implies ownership of truth).  
3. Chat-mediated multi-agent only — rejected (parallel truths).

## Consequences
+ Clear ownership; replayable mission history; OS-like substrate.  
− More structure to implement and test.  
Follow-up: API PATCH with transactions; dashboard panel on Executive Mission.

## Evidence
- `docs/helm/HELM_MISSION_RUNTIME_ARCHITECTURE.md`  
- `backend/helm_runtime/*`  
- `coordination/governance/role_bindings.json`  

## Constitution check
- [x] Runtime truth first  
- [x] No fake green  
- [x] Founder gates untouched  
- [x] Dashboard remains projection only  
