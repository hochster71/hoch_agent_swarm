# HELM → Grok Voice Agent Tool Pack

**Purpose:** Paste-ready founder guide to bind Grok Voice Agents to HELM Runtime Truth.

**Live export (preferred):**

```
GET {HELM_ORIGIN}/api/v1/helm/voice/grok-pack?base_url={HELM_ORIGIN}
GET {HELM_ORIGIN}/api/v1/helm/voice/grok-pack?base_url={HELM_ORIGIN}&format=md
GET {HELM_ORIGIN}/api/v1/helm/voice/tools
```

Also: `config/voice_agent_tools.json` (static index).

---

## 1. Persona

Copy the full use-case block from:

`docs/prompts/helm_voice_executive_commander.md`

Into Grok Voice Agents → “Describe your agent’s use case”.

---

## 2. Doctrine (non-negotiable)

- Every LIVE number comes from a HELM tool call.
- Tool fail / UNKNOWN → say **UNKNOWN**. Never invent dashboards.
- **DOORSTEP** (deploy, spend, keys, sign, money) → escalate; do not execute.
- **Revenue** only via `helm_revenue` / `GET /api/v1/helm/voice/revenue` (SETTLED verified ledger).
- **Security speech** is HIGH-only and rate-limited via `helm_security_events`.

---

## 3. Core tools (map each to HTTP)

Replace `https://YOUR-HELM-ORIGIN` with your HELM LIVE origin (Tailscale / local).

| Tool name | Method | Path |
|-----------|--------|------|
| helm_executive_brief | GET | `/api/v1/helm/voice/brief` |
| helm_voice_command | POST | `/api/v1/helm/voice/command` |
| helm_list_voice_commands | GET | `/api/v1/helm/voice/commands` |
| helm_voice_policy | GET | `/api/v1/helm/voice/policy` |
| helm_sanitize_speech | POST | `/api/v1/helm/voice/sanitize` |
| helm_factory_brief | GET | `/api/v1/helm/voice/factory/{code}` |
| helm_role_brief | GET | `/api/v1/helm/voice/role/{role}` |
| helm_revenue | GET | `/api/v1/helm/voice/revenue` |
| helm_security_events | GET | `/api/v1/helm/voice/security/events` |
| helm_grok_tool_pack | GET | `/api/v1/helm/voice/grok-pack` |

`POST /api/v1/helm/voice/command` body:

```json
{ "command": "executive_brief", "utterance": null, "args": null }
```

Factory codes: `HASF`, `HMF`, `HRF`, `HSF`, `HCF`, `HFF`, `HPF`, `HHF`  
Roles: `founder`, `ops`, `ciso`, `cfo`, `qa`

---

## 4. Smoke checklist

1. `GET /api/v1/helm/voice/health` → subsystem LIVE  
2. `GET /api/v1/helm/voice/brief` → speech_text + labels  
3. `GET /api/v1/helm/voice/revenue` → zero settled = honest zero / UNDEFINED metric  
4. `GET /api/v1/helm/voice/security/events` → HIGH findings or none  
5. `GET /api/v1/helm/voice/factory/HSF` → Stripe env status without secrets  
6. `GET /api/v1/helm/voice/role/ciso` → posture + critical path  

---

## 5. Local desk (optional)

Open `{HELM_ORIGIN}/voice` — enable local TTS, use **Revenue**, **Sec HIGH**, and **Poll security** (60s interval, rate-limited).

---

## 6. What Grok is *not*

Grok is a **builder / voice interface**. HELM is the **executive OS** (mission, truth, policy, evidence). Models are interchangeable; governance is not.
