# EDR-0002 — Provider Dispatch Gateway

- **Status (separated — a passing suite is not a verification claim):**

```yaml
implementation:            IMPLEMENTED      # skeleton; no live dispatch, no creds
tests:                     PASSED           # 22 helm_runtime / 33 with substrate
integration:               PASSED           # router builds; 9 routes; imports clean
independent_verification:  PENDING          # NO Grok bridge verdict artifact on file
executive_readiness:       NOT_YET_DETERMINED
verified_by:               null
evidence:                  Awaiting Grok artifact → docs/evidence/audit/bridge_verification/GROK_VERDICT_<UTC>/
verification_target_id:    20afc2643600a785e69234931335c5934f17cab54787f93dc09bea0804aba3b4
```

  Founder directive (2026-07-17): *design-acceptance ≠ implementation-verification.*
  Do not restore a "VERIFIED_WITH_LIMITATIONS" status until Grok emits a
  bridge-specific verdict against the target id above; only then set
  `independent_verification: VERIFIED_WITH_LIMITATIONS`, `verified_by: Grok`, and
  the evidence path.
- **Author (Builder):** Claude
- **Date:** 2026-07-17
- **Reviewers:** Auditor (Grok) — independent verification required before merge/enablement
- **Related:** EDR-0001 (Runtime Bridge), `HELM_DESIGN_CONSTITUTION.md` (Principle V, no-fake-green)

## Context

The Runtime Bridge (EDR-0001) gives HELM a shared mission object, OCC transaction
model, role router, provider router (binding resolution), event bus, and PATCH
API. The next milestone is letting HELM actually invoke frontier models — but the
**Provider Router must not call providers directly**. Retries, timeouts, rate
limiting, streaming, cancellation, budgeting, metrics, circuit breakers, auth, and
provider normalization would otherwise leak into the runtime.

Founder guidance (2026-07-17): do not scaffold live dispatch yet; insert a
provider-independent **Dispatch Gateway** between Mission Runtime and providers,
implement it *without binding credentials*, add adapters behind it, and only then
enable real dispatch through founder-controlled configuration.

## Decision

Introduce a Dispatch Gateway that owns all cross-provider communication concerns
behind one interface. Each provider is a plugin implementing `ProviderAdapter`:

```python
class ProviderAdapter:
    def invoke(request) -> result
    def stream(request) -> iterator
    def cancel(handle) -> status
    def health() -> {provider, configured, status, reason}
    def capabilities() -> [str]
```

Adapters: `OpenAIAdapter`, `AnthropicAdapter`, `XAIAdapter`, `LocalAdapter`.

Routing is **capability-based, not brand-based** (`capability_registry.json`):
a task declares a capability → registry maps to a role → provider_router resolves
the current model binding → gateway selects the adapter. Swapping a provider is a
binding change; routing logic never moves.

### Separation of concerns (final shape)

```
Mission Runtime governs     → OCC transactions, proposals, versioning
Runtime Truth computes      → derived projections, never owned
Dispatch Gateway communicates → retries/timeout/rate-limit/stream/cancel/budget
Provider Adapters translate → provider-specific request/response normalization
Workers execute             → the bound frontier models
Executive projections observe → Mission Health, event timeline
```

Workers never touch Runtime Truth. Results return as **proposals** back through
the role router (OCC), not as direct state writes.

## This EDR's scope (skeleton — implemented now)

- `dispatch_gateway.py`: `ProviderAdapter` ABC, four registered adapters,
  `DispatchGateway` with `worker_status()` / `health()` / `mission_health()` /
  `dispatch()`.
- `capability_registry.json` + `capability_registry.py`: capability→role routing.
- **Fail-closed:** `invoke/stream/cancel` raise `DispatchNotEnabledError`. No
  provider SDK imported, no network, no secret read. `credential_present()`
  reports env-var presence only.
- Honest projection `{configured, available, blocked}` and a Mission Health
  object for the dark UI (`dispatch: READY`, `workers: 0/N`, `founder_gate:
  PENDING`, `reason: Provider credentials unavailable`).

## Out of scope (later, founder-gated)

- Live adapter bodies (real API/CLI calls) for each provider.
- Actual retry/circuit-breaker/streaming implementations (interfaces defined; behaviour is follow-on).
- Binding credentials — supplied only through founder-controlled configuration.
- Worker Dispatch loop (Task Queue → Gateway → worker → Result → Proposal).

## No-fake-green compliance

The system can honestly report **"dispatch architecturally ready, 0 workers
configured, blocked: [openai, anthropic, xai, local]"** while never faking a
dispatch. Enabling a provider requires (1) founder-supplied credential, (2) a real
adapter body, (3) Auditor verification — three explicit, evidence-gated steps.

## Evidence

### Builder regression (not Auditor verification)

- `tests/helm_runtime/test_dispatch_gateway.py` — adapters blocked without
  creds; `invoke` fails closed; credential presence flips *status only* (not
  dispatch); capability routing; `mission_health` / worker-role health shape.
- Passing pytest is **implementation evidence**, not an independent verification claim.

### Independent verification (required path)

- **Required:** `docs/evidence/audit/bridge_verification/GROK_VERDICT_<UTC>/`  
  bound to `verification_target_id` `20afc2643600a785e69234931335c5934f17cab54787f93dc09bea0804aba3b4`.
- **Present:** no such package.  
  Any informal notes under gitignored `docs/evidence/audit/GROK_BRIDGE_*` are
  **not** accepted as formal Grok verification (wrong path, not target-bound).
- Brief for the Auditor: `docs/evidence/audit/bridge_verification/GROK_VERIFICATION_BRIEF.md`
