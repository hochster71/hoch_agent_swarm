# HELM Voice Executive Interface

**Status:** ORCHESTRATION-BACKED VOICE LIVE (read-only + stage-only) · Grok cloud agent binding is founder config · paid TTS still OFF  
**Doctrine:** no_fake_green · Runtime Truth · founder DOORSTEP  
**Prompt (paste-ready):** `docs/prompts/helm_voice_executive_commander.md`  
**Evidence:** `docs/evidence/runtime/voice-executive-e2e-integration.md`  
**API:** `/api/v1/helm/voice/*` · desk `/voice`

---

## Thesis

Voice is **not** the intelligence. Voice is the **executive interface** to a governed, evidence-driven orchestration system (HELM) that coordinates work across factories while preserving Runtime Truth and founder approval gates.

```
Founder
    │
Voice (Grok Voice Agents / future local STT)
    │
    ▼
HELM Executive Brain
    │
Mission Planning · Runtime Truth · Evidence · Policy · Security · Approvals
    │
    ├── HASF  ├── HCF  ├── HRF  ├── HMF
    ├── HSF   ├── HFF  ├── HHF  └── HPF
    │
Live data: GitHub · Jira · Calendar · Email · Monitoring · Telemetry · Security · Finance
```

---

## Capability audit (truth-labeled)

| Capability | Orchestration / product status | Voice-ready as speech UX | Integration status | Priority |
|------------|--------------------------------|--------------------------|--------------------|----------|
| Mission Intake | Yes (missions, ledgers, intake docs) | Yes | STAGE_ONLY voice stage | P0 |
| Goal Decomposition | Yes (PERT, factories, mission docs) | Yes | Brief / priority from orchestrator | P0 |
| Factory Routing | Yes (factory registry, routers) | Yes | STAGE_ONLY `route_task` | P0 |
| Agent Assignment | Yes (queues, pods, adapters) | Yes | UNKNOWN without evidence package | P0 |
| Runtime Truth | Yes (helm live + brain APIs) | Yes | `GET /api/v1/helm/voice/brief` LIVE | P0 |
| Evidence Review | Yes (`docs/evidence/`, ledgers) | Yes | `evidence_gaps` command (observed blockers) | P0 |
| Founder Approval Gates | Yes (approval queues, DOORSTEP, H1C) | Yes | `founder_approvals` command LIVE | P0 |
| Executive Briefings | Yes (voice brief + founder orchestrator) | Yes | `executive_brief` LIVE | P1 |
| Live Dashboard Narration | Planned | Yes | Voice sidecar = event TTS only | P1 |
| Calendar Scheduling | Planned | Yes | No integration | P1 |
| Email Summaries | Planned | Yes | No integration | P1 |
| Jira Operations | Partial | Yes | Not voice-bound | P1 |
| GitHub Status | Partial | Yes | Not voice-bound | P1 |
| Security Incident Response | Planned | Yes | HCF path; not voice IR | P2 |
| Multi-Agent Voice Collaboration | Vision | Future | Future | P3 |

**Read the matrix correctly:**

- **Yes** under “product status” means the *swarm capability* exists or is documented in-repo.
- **Voice-ready** means the interaction is suitable for calm executive speech.
- **Integration status** is what a Grok Voice Agent can *actually* do **today** without inventing state.

A Grok Voice agent loaded only with the personality prompt can **role-play correctly** and refuse fake metrics. It cannot yet **observe** mission counts, factory health, or approval queues unless tools/APIs are connected.

---

## What already exists (evidence)

| Layer | Evidence | Verdict |
|-------|----------|---------|
| HELM coding/execution persona | `docs/prompts/helm_system_prompt.md`, `docs/agents/HELM.md` | LIVE as doc persona |
| Founder orchestrator doctrine | `docs/architecture/AI_MICHAEL_FOUNDER_ORCHESTRATOR.md` | LIVE as doctrine |
| Local UI event voice (TTS) | `docs/evidence/runtime/voice-sidecar-phase-1-*.md` | Phase 1 VERIFIED (local SpeechSynthesis, fail-closed, no paid providers) |
| Mission Commander truth work | `docs/evidence/runtime/mission_commander_*_verify_*` | Relay/dashboard truth upgrades VERIFIED in-scope |
| Runtime Truth APIs | `backend/runtime_governor.py` refs `/api/brain/runtime-truth`, `/api/brain/factory-runtime-truth`; `/api/status` | LIVE when API process is up — not yet a voice tool |
| Voice Phase 2 (backend policy, xAI TTS, paid) | Called out as remaining blocker in Phase 1 implementation evidence | BLOCKED / not done |

---

## Recommended personality (Mission Commander)

Not a chatbot.

- Calm. Executive. Speaks in facts.
- Reports truth. Never hallucinates state.
- Escalates only for founder gates and real blockers.
- Prefers short briefs over monologue.

State labels for every quantitative claim:

| Label | Meaning |
|-------|---------|
| LIVE | Observed from connected system at request time |
| VERIFIED | Backed by evidence artifact / hash / test output |
| PLANNED | Intended, not running |
| BLOCKED | Explicit blocker with reason |
| UNKNOWN | Not observed, missing, or stale without age proof |

---

## Integration stages (safe order)

### Stage 0 — Persona only — DONE

Persona prompt in `docs/prompts/helm_voice_executive_commander.md`.

### Stage 1 — Read-only Runtime Truth — DONE (in-repo)

- `GET /api/v1/helm/voice/brief`
- `POST /api/v1/helm/voice/command` for READ_ONLY intents
- Aggregates runtime, factories, authority, approvals, orchestrator, security
- Fail-closed labels: LIVE / STALE / UNKNOWN

### Stage 2 — Write path with policy — DONE (stage-only)

- `route_task` / `stage_mission` write `artifacts/voice/staging/*.json`
- `execution: NOT_EXECUTED` always
- DOORSTEP verbs blocked in policy + command resolver

### Stage 3 — Multi-source executive desk (P1+)

Calendar, email, GitHub, Jira, monitoring — each source labeled LIVE vs STALE; never blend into a fake single green.

### Stage 4 — Multi-agent voice collaboration (P3)

Separate agent voices only after external sources are tool-bound; otherwise multi-agent speech multiplies hallucination surface.

### Founder: Grok Voice cloud binding

1. Paste persona prompt into Grok Voice Agents use-case field.
2. Point tools at HELM origin using `/api/v1/helm/voice/tools` schemas.
3. Keep paid providers OFF until founder authorizes (`paid_providers_allowed`).

---

## Relationship to Voice Sidecar Phase 1

| Concern | Voice Sidecar (UI) | Grok Voice Agent |
|---------|--------------------|------------------|
| Purpose | Speak approved **events** (GO/NO-GO, approval, security block) | Conversational **executive command** channel |
| STT | No (Phase 1) | Yes (Grok Voice) |
| TTS | Local browser SpeechSynthesis | Grok Voice TTS |
| Cost policy | Zero paid; fail-closed | External beta; treat as founder-chosen channel |
| Secrets | Sanitizer redacts | Prompt + policy must forbid speaking secrets |
| Truth source | Mapped UI events | Must bind to HELM APIs for LIVE claims |

These are complementary, not duplicates. Sidecar = outbound event announcements. Grok Voice = inbound executive dialogue. Both must obey no_fake_green.

---

## Founder DOORSTEP (never voice-autonomous)

Stage in `coordination/coordination_bus.json` → `doorstep_for_founder` (or approval queue):

- Deploy / production push
- Spend / Stripe live / paid providers
- Provision or rotate keys
- Sign / notarize / App Store submit
- Move money

Voice may **describe** the gate and **prepare** the checklist. Voice may **not** clear it.

---

## Success criteria (orchestration voice LIVE — met in-repo)

1. Persona prompt present — yes  
2. Read-only Runtime Truth path — `GET /api/v1/helm/voice/brief` — yes  
3. Offline / missing sources → UNKNOWN labels — yes (fail-closed)  
4. Secrets redaction — `sanitize_for_speech` + tests — yes  
5. DOORSTEP cannot execute via voice — tests — yes  
6. Evidence pack — `docs/evidence/runtime/voice-executive-e2e-integration.md` — yes  

**Still founder-gated:** wiring Grok Voice cloud product to your HELM origin; any paid TTS.

---

## Immediate next actions

| # | Action | Owner | Gate |
|---|--------|-------|------|
| 1 | Paste persona + bind tools to HELM `/api/v1/helm/voice/*` | Founder | None (SAFE) |
| 2 | Open `/voice` on HELM LIVE and run Brief (TTS optional) | Founder | None |
| 3 | Calendar/email/GitHub/Jira tool adapters | Engineering | SAFE read-only |
| 4 | Paid / xAI realtime voice | Engineering | Founder DOORSTEP if paid |

---

## Non-goals

- Replacing Runtime Truth with model memory of prior sessions
- Using voice as release authority
- Multi-agent voice theater without evidence bindings
- Hardcoding metrics into the system prompt
