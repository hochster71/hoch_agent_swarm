# HELM Executive Command Center — Vision & Phased Roadmap

> Founder vision (Michael Hoch, 2026-07-17): HELM as an **Executive Cyber Command Center** — a Cyber Operations Center purpose-built for AI, software factories, and continuous authorization. Navy operational discipline × DoD RMF/NIST 800-53 × AI-native ops × executive decision support. "Truth. Evidence. Governance. Mission."
>
> This file is the durable spec. Build it in phases, evidence-first, NO FAKE GREEN. Reference mockup: the 15-panel command center.

## Governing principles (from HELM doctrine)
- Every color/number backed by real evidence + freshness; UNKNOWN stays UNKNOWN (never green).
- One authoritative runtime truth; voice/dashboard/CLI/API must agree. No separate "voice truth."
- Founder gates (money, publish, secrets, deploy) are never cleared by voice/model/test.

## The 15 panels → current status → phase

| # | Panel | Status today | Phase |
|---|-------|-------------|-------|
| 1 | **Executive** (HELM brain + readiness metrics) | **BUILT** — `frontend_live/executive.html` + `backend/truth/hmai.py` (`/api/v1/helm/hmai`) | ✅ P1 |
| — | **HMAI bar** (composite Mission Assurance Index + pillars) | **BUILT** — real 7-pillar index, UNKNOWN down-weighted | ✅ P1 |
| 4 | **Runtime Truth Engine** | **BUILT** — `backend/truth/*`, `/api/v1/helm/{goal,factories,runtime,wall,tasks,integrity,pert}` live | ✅ P1 |
| 14 | **Mission Assurance Shield** | **BUILT** (= HMAI composite) | ✅ P1 |
| 3 | **Cyber Operations Center** (readiness board) | **PARTIAL** — NIST CSF×800-53 matrix `/api/v1/helm/nist`, conmon, zero-trust middleware exist; viz PLANNED | P2 |
| 9 | **Zero Trust Sphere** | **PARTIAL** — zero-trust middleware exists; sphere viz PLANNED | P2 |
| 10 | **Continuous Monitoring** (CVE/SBOM/STIG/secrets) | **PARTIAL** — conmon ledger exists; CVE/SBOM/STIG feeds + viz PLANNED | P2 |
| 5 | **Executive Timeline** (intake→release) | **PARTIAL** — goal/PERT data exists; timeline viz PLANNED | P2 |
| 6 | **Agent Swarm Network** | **PARTIAL** — `/api/v1/helm/agents` (integrity-gated); live graph viz PLANNED | P2 |
| 7 | **AI Cognition View** (model routing) | **PARTIAL** — model router + provider registry + cost exist; routing viz + hallucination metric PLANNED | P2 |
| 12 | **Factory Galaxy** | **PARTIAL** — factory_registry + census truth; galaxy viz PLANNED | P2 |
| 15 | **Evidence River** (collect→hash→verify→archive) | **PARTIAL** — AU-9 evidence chain + manifests exist; river viz PLANNED | P2 |
| 11 | **HELM Voice Interface** | **PARTIAL (~80%)** — `backend/voice/*`, voice.html, ElevenLabs adapter (gated); gateway/Alexa/device PLANNED (see HELM_VOICE prompt) | P3 |
| 2 | **Mission Control Bridge** | **PLANNED** (viz) | P3 |
| 8 | **Cyber Terrain Map** (services as terrain) | **PLANNED** — model GitHub/Docker/Apple/Stripe/Cloudflare as live graph | P3 |
| 13 | **Knowledge Galaxy** | **PLANNED** | P3 |

## Phased build
- **Phase 1 — Executive Bridge (DONE this session):** HMAI + Executive screen + Runtime Truth, evidence-sourced. Security hardening (auth + CORS allowlist) staged behind flags.
- **Phase 2 — Cyber Operations Center:** unify the two security hosts (helm_live_api:8770 + main.py) into one Command Center; wire NIST/zero-trust/conmon into operational views; live terrain + evidence river + agent-swarm graphs. Add CVE/SBOM/STIG feeds. AI-native controls (model inventory, hallucination reconciliation, tool-invocation audit).
- **Phase 3 — Mission Assurance + Voice:** HELM Voice Gateway (common gateway, Alexa adapter, dedicated wake-word device) per HELM_VOICE prompt; Mission Control Bridge + Cyber Terrain + Knowledge Galaxy; "why did readiness fall from 96→88%" executive decision-support answers.

## Immediate prerequisites (from the Grok 51/100 audit + baseline)
1. Activate the staged API hardening (auth + CORS allowlist) — founder flips `HELM_REQUIRE_AUTH=1` + `HELM_API_TOKEN`. Runbook: `docs/security/HELM_LIVE_API_HARDENING.md`.
2. Fix validator env rot (pytest missing in the Xcode python running validators) — a chunk of the 51/100 is environment, not capability.
3. Unify the two security hosts before the Cyber Ops viz.
4. Make the AI egress guard fail-closed; add a hallucination-rate metric.
5. Containerize (started: `deploy/container/`) — resolve hardcoded `/Users` paths + SQLite ledger path for HA.

## Definition of done (per panel)
A panel goes live only when its data derives from a real, fresh source with an evidence reference; UNKNOWN pillars render UNKNOWN. No panel is "done" because it renders — only when its truth is exercised.
