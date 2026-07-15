# HELM Voice Executive — End-to-End Integration

**Date:** 2026-07-15  
**Branch:** `helm/h1b-r2-remediation`  
**Doctrine:** no_fake_green · Runtime Truth · DOORSTEP founder-only  

## Scope delivered

| Layer | Path | Status |
|-------|------|--------|
| Policy | `config/voice_policy.yaml` | LIVE |
| Tool catalog | `config/voice_agent_tools.json` | LIVE |
| Backend module | `backend/voice/*` | LIVE |
| API (HELM LIVE) | `/api/v1/helm/voice/*` on `helm_live_api` | LIVE |
| API (main swarm) | same routes on `backend.main` | LIVE |
| Voice desk UI | `/voice` → `frontend_live/voice.html` | LIVE |
| Shared client | `frontend_live/voice_panel.js` | LIVE |
| Console mount | `frontend_live/console.html` | LIVE |
| Founder mount | `frontend_live/founder.html` | LIVE |
| Index link | `frontend/index.html` → `/voice` | LIVE |
| Persona prompt | `docs/prompts/helm_voice_executive_commander.md` | LIVE |
| Architecture | `docs/architecture/HELM_VOICE_EXECUTIVE_INTERFACE.md` | updated |
| Tests | `tests/unit/test_helm_voice_executive.py` | see verification |

## Endpoints

- `GET /api/v1/helm/voice/health`
- `GET /api/v1/helm/voice/policy`
- `GET /api/v1/helm/voice/commands`
- `GET /api/v1/helm/voice/brief`
- `POST /api/v1/helm/voice/command` (also GET with query params)
- `POST /api/v1/helm/voice/sanitize`
- `GET /api/v1/helm/voice/tools` — Grok Voice function schemas
- `GET /voice` — executive desk
- `GET /frontend_live/voice_panel.js`

## Command modes

| Mode | Behavior |
|------|----------|
| READ_ONLY | Observe Runtime Truth / authority / factories / orchestrator |
| STAGE_ONLY | Write `artifacts/voice/staging/*.json` — **not executed** |
| DOORSTEP | Always blocked; speech escalates to founder |

## What is NOT claimed

- Grok Voice Agents cloud product is not auto-configured in xAI UI (founder pastes persona + points tools at these endpoints).
- Paid TTS / xAI realtime STT not enabled (`paid_providers_allowed: false`).
- Voice does not clear release GO or execute deploy/spend/keys.
- Idle-agent reassignment remains UNKNOWN without attributed evidence package (no fabricated leaderboard).

## Verification commands

```bash
.venv/bin/pytest tests/unit/test_helm_voice_executive.py -q
# or
python -m pytest tests/unit/test_helm_voice_executive.py -q
```

## Verification result (2026-07-15)

```
12 passed in 1.32s
```

Proven: policy fail-closed, secret redaction, DOORSTEP block on deploy, stage-only route artifact, brief labels, both FastAPI apps expose `/api/v1/helm/voice/*`, `/voice` desk + `voice_panel.js` served.

## Follow-on (same series)

- Goal registry: `goal_status` + brief labels from `coordination/goal/goal_state.json` (validator weight-sum; founder-minutes-per-dollar stays UNKNOWN when null).
- Local git: `repo_status` observes branch/head/dirty_count; **GitHub remote remains UNKNOWN** (no fake GH status).
- Surfaces: voice panel also mounted on `frontend_live/helm.html` wall.

## Grok Voice binding (founder)

1. Paste persona from `docs/prompts/helm_voice_executive_commander.md`.
2. Discover tools: `GET {HELM_ORIGIN}/api/v1/helm/voice/tools`.
3. Map each `x_helm_http` path to the HELM LIVE origin.
4. Rule: tool failure or UNKNOWN → say UNKNOWN; never invent metrics.
