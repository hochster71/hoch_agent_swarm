# HERMES — HELM Execution & Routing Model Exchange Service

**Status: OPERATIONAL (evidence below).** Built 2026-07-18 as a **composition layer** over the
existing HELM runtime. HERMES is not a model and not a second orchestrator: it discovers,
registers, selects and evaluates AI **workers**, so HELM dispatches by **capability**, never by vendor.

```
dispatch(capability="code_generation")     ← what callers say
        │
        ├─ capability_registry.py   (FROZEN, EXISTING)  capability → role
        ├─ hermes/capability_map.py (NEW)               role + manifests → WORKER
        └─ guarded_council.guarded_dispatch (EXISTING)  → CouncilDispatchGateway
                                                          allowlist · cost cap · egress guard · ledger
```

## What was REUSED (not rebuilt)
| Existing system | Role in HERMES | Why reused |
|---|---|---|
| `backend/helm_runtime/capability_registry.py` (**frozen**) | capability → role | A capability registry **already existed**. HERMES consults it and never modifies it or its JSON. |
| `backend/helm_runtime/provider_router.py` (**frozen**) | role → binding | Worker-as-plugin resolution already solved. |
| `backend/helm_runtime/dispatch_gateway.py` (**frozen**) | `ProviderAdapter` interface, worker/mission health | The common adapter interface the mission asked for **already exists**; defining another would fork it. |
| `scripts/council/gateway.py` (`CouncilDispatchGateway`) | the **only** execution choke point | Already enforces allowlist, spend cap, egress guard, ledger. HERMES must not bypass a zero-trust gate. |
| `backend/dispatch/guarded_council.py` | lane → provider/model + `guarded_dispatch()` | Existing guarded call path; HERMES calls it rather than opening a second one. |
| `scripts/scan_ai_runtimes.py` | local discovery (Ollama :11434, LM Studio :1234) | Working probe already shipped — HERMES calls `fetch_json` from it instead of writing a scanner. |
| HELM event ledger (`council_router._record`) | mission analytics sink | "Do not create duplicate event buses." Learning hooks append here. |

## What HERMES ADDS (the genuine gaps)
1. **Worker Registry** — `coordination/hermes/workers.json` + `backend/hermes/worker_registry.py`.
   Per-worker manifests: capabilities, context length, modality, cost class, latency class,
   locality (local/remote), dispatch type, founder-gate status. **No worker manifest layer existed** —
   model metadata was scattered across `modelops_manager` (eval scores), `model_mesh` (reachability)
   and `guarded_council` (lane→model), with no single "what can this worker do and what does it cost".
2. **Capability → WORKER selection** — `backend/hermes/capability_map.py`. The frozen registry stops
   at *role*; nothing chose a concrete worker. Selection is ranked (context fit → local-first → gate →
   cost → latency) and **explainable** (returns reason, candidates, rejected).
3. **Capability dispatcher** — `backend/hermes/dispatcher.py`. `dispatch(capability=...)` with explicit
   `fallback_used` / `fallback_reason` / `tried` recording.
4. **Learning Engine interface + hooks** — `backend/hermes/learning.py`. Records worker · capability ·
   latency · cost · quality · verification · success/failure · selection reason · fallback.

## What was deliberately NOT built (duplicates avoided)
- ❌ a second capability registry — extended by composition instead
- ❌ a second dispatch gateway, queue, scheduler, or event bus
- ❌ a second provider-adapter interface (`dispatch_gateway.ProviderAdapter` already defines it)
- ❌ a second local-discovery scanner
- ❌ any edit to a frozen-target file (test `test_frozen_registry_data_unmodified` enforces this)

## Architectural decisions (and why)
- **Selection separated from execution.** HERMES picks; the gateway executes. Keeps one zero-trust
  choke point and keeps HERMES out of the frozen verification target.
- **Availability is OBSERVED, never asserted.** Manifests may not contain an `availability` field
  (enforced by test). Local = TCP probe; remote = CLI on PATH / credential env. Otherwise `UNKNOWN`.
- **Local-first ranking.** Free + no egress wins ties; frontier workers are marked `founder_gated`
  and the gate stays at the gateway, not in HERMES.
- **Learning is interface-only by founder scope.** `recommend_worker()` returns `NO_RECOMMENDATION`
  / `INTERFACE_ONLY`. Learned routing changes behaviour and therefore needs an **EDR**; until then
  routing stays deterministic and auditable.
- **Fails closed.** No worker for a capability → `resolved:false` with reason + blocked candidates.
  Never a silent substitution.

## Operational evidence (2026-07-18, founder's machine)
```
Worker registry : 6 workers · AVAILABLE = claude_code, grok_cli, gemini_cli, ollama_local,
                  lmstudio_local · NOT_CONFIGURED = openai_api (no OPENAI_API_KEY)
Local discovery : via scripts/scan_ai_runtimes.py → 43 Ollama models, 4 LM Studio models
Capabilities    : 25 known · 22 servable now
Selection       : code_generation → ollama_local (local-first, free)
                  verification    → grok_cli (role=auditor from the FROZEN registry)
                  multimodal      → gemini_cli (FOUNDER-GATED at the gateway)
LIVE DISPATCH   : dispatch(capability="local_private") → runtime chose ollama_local →
                  llama3.2:3b (local·guarded) → "HERMES ONLINE" · 2636 ms · fallback_used=False
Tests           : tests/test_hermes_runtime.py — 16 passed
```

## Known integration seam (reported, not hidden)
The frozen capability registry's vocabulary covers 3 roles (orchestrator/builder/auditor) and a
narrower capability list. Capabilities outside it (`code_generation`, `local_private`, `multimodal`)
resolve to `role=None`, and HERMES defaults those to the **local** lane — safe (no egress, free) but
not role-routed. Widening the frozen vocabulary would edit a frozen-target file, so it requires an
**EDR**. Recorded here rather than silently patched.

## API
```python
from backend.hermes import dispatch, explain, registry_health, capability_matrix

dispatch(capability="code_generation", prompt="...")   # runtime picks the worker
explain("verification")                                # dry run: who/why, dispatches nothing
registry_health()                                      # observed availability + discovery
capability_matrix()                                    # capability → servable workers
```
