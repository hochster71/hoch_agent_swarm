# HELM Voice V3 — Revenue ledger · Security HIGH speech · Grok tool pack

**Date:** 2026-07-15  
**Doctrine:** no_fake_green  

## 1. Verified revenue

- Module: `backend/voice/revenue.py`
- Endpoint: `GET /api/v1/helm/voice/revenue`
- Source: `HochLedger.summary()` — only **SETTLED + verified** rows
- Zero settled dollars → observed zero; north-star metric **UNDEFINED**; no fake EARNING
- Stripe dashboard balances are **not** spoken as truth

## 2. Security HIGH event-to-speech

- Module: `backend/voice/security_events.py`
- Endpoints:
  - `GET /api/v1/helm/voice/security/events`
  - `GET ...?mark_spoken=true` / `POST .../ack`
- Sources: control posture HIGH controls, cyber swarm NOT_SECURE/HIGH, goal REQ-CP-SECURITY
- Rate limit: max 10/hour (capped by policy max_events_per_hour)
- UI: `/voice` panel — **Sec HIGH** + **Poll security** (60s)

## 3. Grok tool pack

- Module: `backend/voice/grok_pack.py`
- `GET /api/v1/helm/voice/grok-pack?base_url=...&format=json|md`
- Founder paste doc: `docs/prompts/GROK_VOICE_TOOL_PACK.md`
- Catalog: `config/voice_agent_tools.json` v2

## Verification

```bash
.venv/bin/pytest tests/unit/test_helm_voice_executive.py -q
```
