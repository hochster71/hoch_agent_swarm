# HELM Voice V1 — Factory + Leadership Role Agents

**Date:** 2026-07-15  
**Doctrine:** no_fake_green  

## Delivered

| Endpoint | Behavior |
|----------|----------|
| `GET /api/v1/helm/voice/factories` | Roster: REGISTERED + PLANNED |
| `GET /api/v1/helm/voice/factory/{code}` | HASF/HMF/HRF observe BRAIN; HSF/HCF/HFF/HHF/HPF = PLANNED |
| `GET /api/v1/helm/voice/roles` | founder, ops, ciso, cfo, qa |
| `GET /api/v1/helm/voice/role/{role}` | Role lens over Runtime Truth |

## Modules

- `backend/voice/factory_agents.py`
- `backend/voice/role_agents.py`

## Verification

```bash
.venv/bin/pytest tests/unit/test_helm_voice_executive.py -q
# 20 passed (2026-07-15)
```
