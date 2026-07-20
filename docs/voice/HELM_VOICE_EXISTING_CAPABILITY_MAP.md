# HELM Voice Existing Capability Map

This document inventories the existing architecture, files, security boundaries, and authoritative data sources in the HELM repository to map how the voice subsystem will integrate without duplicating logic.

---

## 🗺️ Component Location & Architecture

### 1. Existing Voice Integration
- **Directory**: `backend/voice/`
- **Current router**: [router.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/router.py) registers endpoints for:
  - GET/POST `/api/v1/helm/voice/command` — Executing voice commands.
  - GET `/api/v1/helm/voice/brief` — Executive briefing builder.
  - GET `/api/v1/helm/voice/commands` — Public commands dictionary.
  - GET `/api/v1/helm/voice/policy` — Spoken policy config.
- **Current commands**: [commands.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/commands.py) registers voice command patterns (`brief me`, `morning brief`, `highest priority`, etc.) and sets security modes: `READ_ONLY`, `STAGE_ONLY`, and `DOORSTEP`.
- **Current briefing generator**: [briefing.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/briefing.py) compiles runtime truth details.

### 2. Authoritative Status & Data Sources
- **Overall Mission Status**: Derived by [mission_state.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/mission_control/mission_state.py) and stored at [mission_state.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/goal/mission_state.json).
- **Runtime Health**: [active_runtime_source.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/council/active_runtime_source.json) and [health.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/jspace/health.json).
- **Online Agents**: [role_bindings.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/governance/role_bindings.json).
- **Open Blockers**: [goal_state.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/goal/goal_state.json).
- **Operator Hold**: [ag_operator_hold.json](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data/ag_operator_hold.json) (written by [ag_operator_hold.py](file:///Users/michaelhoch/hoch_agent_swarm/scripts/ag_operator_hold.py) and evaluated by [operator_hold.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/runtime_truth/operator_hold.py)).
- **HAF Decisions & Findings**: [decisions.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/audit_factory/decisions.json) and [findings.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/audit_factory/findings.json).
- **Production Authority**: [HAF_v0_1_milestone_decision.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/audit_factory/decisions/HAF_v0_1_milestone_decision.json).
- **Factory Readiness**: [factory_registry.json](file:///Users/michaelhoch/hoch_agent_swarm/coordination/council/factory_registry.json).

---

## 🔒 Security Boundaries & Invariants

- **Zero-Trust read-auth middleware**: Implemented in [read_auth.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/security/zero_trust/read_auth.py) and [api_hardening.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/security/api_hardening.py). All incoming voice request routes will inherit this middleware.
- **Founder-only gates**: Governed by [founder_gate.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/council/founder_gate.py). Voice commands must never execute actions marked `FOUNDER_ONLY` (e.g. key rotations, financial transactions); these require manual out-of-band founder action.
- **Network Ingress**: External device hooks (Alexa webhook, Siri intents) will bind to the `/api/v1/voice/` subpath via a public HTTPS tunnel, while admin APIs remain strictly internal.

---

## 🛠️ Proposed File Changes

### 1. New Voice Subsystem Kernel (`backend/voice/`)
- [NEW] [models.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/models.py) — Pydantic models for Voice request envelopes and responses.
- [NEW] [intent_registry.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/intent_registry.py) — Allowed intents register with slots, constraints, and handlers.
- [NEW] [intent_parser.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/intent_parser.py) — Converts spoken transcript expressions to registered intents.
- [NEW] [authorization.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/authorization.py) — Pre-command security decision checks.
- [NEW] [confirmation.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/confirmation.py) — Token/challenge manager for writes (hold enable/disable, run conmon).
- [NEW] [session_store.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/session_store.py) — Replay protection nonces and confirmation challenges cache.
- [NEW] [response_renderer.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/response_renderer.py) — Spoken output composition and data redaction.
- [MODIFY] [router.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/router.py) — Expose new web voice, Siri, and Alexa webhook endpoints.

### 2. Adapters (`backend/voice/adapters/`)
- [NEW] [alexa.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/adapters/alexa.py) — Custom Skill adapter containing request signature and timestamp validation.
- [NEW] [siri.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/adapters/siri.py) — Siri adapter for App Intents integration.
- [NEW] [web_voice.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/voice/adapters/web_voice.py) — Web Console Push-to-talk backend.

### 3. Tests & Utilities
- [NEW] [test_voice_gateway.py](file:///Users/michaelhoch/hoch_agent_swarm/tests/voice/test_voice_gateway.py) — 25 negative tests as specified by the requirements.
- [NEW] [run_helm_voice_mutation_tests.py](file:///Users/michaelhoch/hoch_agent_swarm/scripts/voice/run_helm_voice_mutation_tests.py) — Mutation test suite with 12 mutation vectors.
- [NEW] [verify_voice_audit_chain.py](file:///Users/michaelhoch/hoch_agent_swarm/scripts/voice/verify_voice_audit_chain.py) — Blockchain/tamper-evident audit chain verifier.

### 4. Apple Siri Companion (`integrations/apple/HELMVoice/`)
- [NEW] SwiftUI target structures with native App Intents (GetHELMStatusIntent, RunHAFConMonIntent, etc.) and App Shortcuts mappings.
