# EDR-0001 — HELM Runtime Bridge v1 (worker interoperability substrate)

- **Status:** PROPOSED (built on branch `helm-runtime-bridge-v1`; not merged to main during audit freeze)
- **Author (Builder):** Claude
- **Date:** 2026-07-17
- **Reviewers:** Auditor (Grok) — independent verification required before merge
- **Supersedes:** none
- **Related:** `docs/helm/HELM_MISSION_RUNTIME_ARCHITECTURE.md`, `HELM_DESIGN_CONSTITUTION.md`, `field_ownership.json`, `role_bindings.json`

## Context

Claude, ChatGPT, and Grok run in separate execution environments with no shared
runtime or direct channel. Coordination today happens only by a human passing
artifacts between models. The mission — *HELM becomes the operating system and
the three frontier models become interoperable workers* — requires the bridge to
live inside `hoch_agent_swarm`, not inside any model. Founder directive
(2026-07-17): "Claude (Builder) should implement the runtime, not more prompts."

## Decision

Add the missing **bridge** layer on top of the existing substrate
(`transaction.py`, `event_bus.py`, `governance_engine.py`, `truth_engine.py`,
`mission_runtime.py`). No model talks to another model; every model talks to
HELM through one governed door.

New modules under `backend/helm_runtime/`:

| Module | Responsibility |
|---|---|
| `mission_store.py` | Versioned read + **optimistic-concurrency** compare-and-swap. Stale `mission_version` → `CONFLICT`, never a silent clobber. |
| `provider_router.py` | **Worker-as-plugin.** Resolves role → provider/model from `role_bindings.json`. Reports credential **presence only** — never a secret value. Replacing a model is a one-line binding change. |
| `role_router.py` | The **single inbound door**: `route_proposal(role, patch, expected_parent_version=…)`. Validates the role is a real actor (rejects `truth`/`runtime` — platform, not actors), always enforces compare-and-swap, hands to the transaction engine. |
| `bridge_api.py` | FastAPI surface: `GET/PATCH /api/v1/helm/mission`, `GET /api/v1/helm/events`, `/providers`, `/bridge`. PATCH is version-pinned (HTTP 409 on stale); founder-gate fields require an explicit founder authorization header. |

Minimal additive change to `transaction.py`: an `expected_parent_version`
parameter that refuses the commit inside the same critical section as the write.

## Transaction lifecycle (unchanged, now concurrency-safe)

`BEGIN → PROPOSAL → VALIDATE → AUTHORIZE → [OCC compare-and-swap] → COMMIT →
PUBLISH_EVENT → RECOMPUTE_TRUTH → END`, or a terminal `CONFLICT` / `FAILED` /
`ROLE_REJECTED` with both versions and the failing phase.

## Consequences

- **Positive:** Workers become stateless and replaceable — the Mission Runtime
  remembers, not the models. Concurrency is safe by construction. Model-agnostic:
  GPT-6 / a future Claude / another frontier model swaps at the binding, not the
  architecture. Every write emits an event on the nervous system.
- **Negative / not-yet-built:** Cross-provider *invocation* (HELM actively
  calling OpenAI/Anthropic/xAI to dispatch work) is out of scope here — this
  layer is the shared state + governed write path + provider abstraction. Actual
  dispatch requires each provider's API/CLI wired to the router (follow-on EDR).
  The dark executive "mission bridge" UI is also follow-on.

## Governance / freeze compliance

Built on an **isolated branch**; `main` stays at the frozen commit `3fe8a9e7`
and the audit bundle `audit_target_id 44405b52…` is untouched. Both auditors
bind to the frozen bundle, so this branch is definitionally out of baseline
scope. Merge is gated on: (1) dual baseline audits complete, (2) reconciliation,
(3) founder authorization, (4) Auditor (Grok) independent verification of
transaction integrity, event ordering, concurrency, replay, authorization, and
negative tests — the Auditor verifies this; it does not author it.

## Evidence

- `tests/helm_runtime/test_bridge.py` — 11 passing (OCC land + stale-reject,
  role rejection, auto-pin, auditor-cannot-write-builder-field, founder-gate
  denials, no-secret-leak, worker health, event emission).
- Regression: `test_helm_runtime_transactions.py`, `test_executive_mission.py`
  still pass (11 + others) — no substrate regression.
