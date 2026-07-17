# HELM Mission Runtime Architecture

**Status:** Substrate design (2026-07-17 revision) — four engines, versioned mission transactions, event bus, model-agnostic roles.  
**Not claimed:** Fully automated end-to-end OS in production.

---

## Core distinction

**Runtime is not an actor.** Nobody “plays” Truth.

| Layer | What it is |
|---|---|
| **HELM Executive Runtime** | The **platform** (computes, governs, publishes) |
| **Founder / Orchestrator / Builder / Auditor** | The **actors** (humans and model workers) |

Truth is **derived**. The Runtime **computes** it from evidence, telemetry, and external milestones. Actors propose and produce evidence; they do not own truth.

```
HELM Executive Runtime  (platform)
├── Mission Runtime
├── Runtime Truth Engine
├── Governance Engine
├── Event Bus
├── Evidence Ledger
└── API Layer

Actors (only)
├── Founder
├── Orchestrator  (bound model — e.g. ChatGPT Agent)
├── Builder       (bound model — e.g. Claude)
└── Auditor       (bound model — e.g. Grok)
```

---

## Four engines (split “Runtime” so jobs do not blur)

### 1. Mission Runtime
**Owns:** coordination, ownership, queues, proposals, mission object versioning.  
**Does not:** invent truth, clear founder gates, self-certify.

### 2. Runtime Truth Engine
**Owns:** telemetry, evidence intake, external milestones, **computed** truth projections (`mission_state`, HMAI, external machines).  
**Does not:** accept narrative as green; forge APPROVED/SETTLED.

### 3. Governance Engine
**Owns:** founder gates, authorization, policy, Design Constitution checks, field ownership enforcement.  
**Does not:** implement product features.

### 4. Event Bus (Digital Nervous System)
**Owns:** publishing every material runtime event; fan-out to truth recompute and subscribers.  
**Does not:** side-channel peer chat between models.

**Nothing else in HELM should communicate directly.** Everything material publishes events.

---

## Projection chain (dashboard is never source)

```
Executive Mission  (intent + roles + queues + proposals — versioned)
        ↓
Mission Runtime    (validate / authorize / commit)
        ↓
Runtime Truth      (recompute derived state)
        ↓
Executive Dashboard / Voice / CLI  (projections only)
```

Do **not** treat raw `mission_state.json` as the human control surface.  
It is a **projection** of Runtime Truth. The durable control object is **Executive Mission** (+ evidence + events).

---

## Transaction semantics (OS-like writes)

Every material write:

```
BEGIN
  → Proposal
  → Validate (schema, ownership, constitution)
  → Authorize (governance / founder gate if required)
  → Commit (atomic mission version bump)
  → Publish Event
  → Recompute Runtime Truth
  → Notify Subscribers
END
```

Required mission versioning fields:

| Field | Purpose |
|---|---|
| `mission_version` | Monotonic integer |
| `transaction_id` | Unique id for this commit |
| `parent_version` | Prior version (replay chain) |
| `created_at` | First creation |
| `updated_at` | Last commit |
| `correlation_id` | Cross-system trace |

---

## Actors (frozen responsibilities)

### Founder (minimal)
Owns **only:** money · publication · legal acceptance · external submissions · secrets · organizational direction.  
Everything else is delegated under governance.

### Orchestrator (Chief of Staff — not boss)
Owns: orchestration · dependency resolution · mission planning · reconciliation coordination · executive briefing generation.  
**Not:** approving work · auditing work · writing production code · self-certifying.

### Builder
Owns: architecture · implementation · refactoring · UI · tests · packaging · **Engineering Decision Records (EDRs)**.  
**Not:** final assurance verdict · clearing founder gates.

### Auditor
Owns: audits · red team · verification · adversarial testing · performance measurement · regression verification · evidence validation.  
**Not:** primary product ownership · orchestration as CoS.

---

## Model-agnostic roles

Prefer:

- `ROLE_ORCHESTRATOR.md`
- `ROLE_BUILDER.md`
- `ROLE_AUDITOR.md`

Bind providers at runtime via `coordination/governance/role_bindings.json`:

```yaml
role_bindings:
  orchestrator: { provider: openai, model: gpt-5.6, mode: agent }
  builder:      { provider: anthropic, model: claude }
  auditor:      { provider: xai, model: grok-4.5 }
```

Changing models updates the binding—not the architecture.

---

## Implementation map (repo)

| Piece | Path |
|---|---|
| Charter | `docs/helm/HELM_EXECUTIVE_RUNTIME_CHARTER.md` |
| This architecture | `docs/helm/HELM_MISSION_RUNTIME_ARCHITECTURE.md` |
| Executive Mission | `coordination/goal/executive_mission.json` |
| Field ownership | `coordination/governance/field_ownership.json` |
| Role bindings | `coordination/governance/role_bindings.json` |
| Role docs | `coordination/governance/role_overlays/ROLE_*.md` |
| EDR template | `docs/helm/templates/ENGINEERING_DECISION_RECORD.md` |
| Mission Runtime | `backend/helm_runtime/mission_runtime.py` |
| Event Bus | `backend/helm_runtime/event_bus.py` |
| Transactions | `backend/helm_runtime/transaction.py` |
| Governance gate | `backend/helm_runtime/governance_engine.py` |
| Truth recompute hook | `backend/helm_runtime/truth_engine.py` |

---

## After audit freeze lifts

Focus work here—not on which model is “in charge.” Build the substrate so **any** qualified model can occupy a role under the same constitution.
