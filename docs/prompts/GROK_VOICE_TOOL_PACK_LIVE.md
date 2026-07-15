# HELM Grok Voice Tool Pack (LIVE)

**Generated for your Mac tailnet origin.**

| Use | URL |
|-----|-----|
| Phone / Tailscale voice desk | https://michaels-macbook-pro.tail826763.ts.net/voice |
| Local voice desk | http://127.0.0.1:8770/voice |
| Tool base_url (Grok) | `https://michaels-macbook-pro.tail826763.ts.net` |
| Ops guide | `docs/ops/HELM_VOICE_PHONE_AND_GROK.md` |

> Paste persona from `docs/prompts/helm_voice_executive_commander.md`, then register tools below.
> Prefer Grok built-in TTS if present; else use `helm_tts_speak` (ElevenLabs via HELM).

---

# HELM Executive Mission Commander — Grok Voice Tool Pack

**Base URL:** `https://michaels-macbook-pro.tail826763.ts.net`

## Setup

- 1. Create a Grok Voice Agent in Grok Voice Agents (Beta).
- 2. Paste the persona from docs/prompts/helm_voice_executive_commander.md into use-case.
- 3. Set HELM base URL to your LIVE origin (replace https://michaels-macbook-pro.tail826763.ts.net if placeholder).
- 4. Register each tool below as an HTTP / function tool mapped to the URL template.
- 5. Or poll GET {base}/api/v1/helm/voice/tools for live schemas.
- 6. Enable local TTS only on the HELM /voice desk if you want browser speech; Grok has its own TTS.

## Doctrine

- Call tools for every LIVE metric
- Tool fail or UNKNOWN → say UNKNOWN; never invent dashboards
- DOORSTEP (deploy/spend/keys/sign/money) is never auto-executed
- Revenue dollars only from verified SETTLED ledger via helm_revenue
- Security speech is HIGH-only and rate-limited

## Tools

### `helm_executive_brief`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/brief`
- **Description:** Get HELM executive briefing from Runtime Truth. Returns speech_text and per-field LIVE/STALE/UNKNOWN labels. Never invent metrics if this tool fails — report UNKNOWN.

### `helm_voice_command`

- **Method:** `POST`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/command`
- **Description:** Execute a governed HELM voice command. READ_ONLY observes truth; STAGE_ONLY stages artifacts; DOORSTEP actions are blocked and must escalate to founder.

### `helm_list_voice_commands`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/commands`
- **Description:** List available HELM voice commands and modes.

### `helm_voice_policy`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/policy`
- **Description:** Get HELM voice policy (DOORSTEP verbs, TTS defaults, doctrine).

### `helm_sanitize_speech`

- **Method:** `POST`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/sanitize`
- **Description:** Sanitize text before speaking; redacts secrets and keys.

### `helm_factory_brief`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/factory/{code}`
- **Description:** Per-factory voice brief. BRAIN-registered: HASF, HMF, HRF. Declared-observable (PARTIAL): HSF, HCF, HFF, HHF, HPF. Never invent revenue or secure posture.

### `helm_role_brief`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/role/{role}`
- **Description:** Leadership role brief: founder, ops, ciso, cfo, qa. Role-specific lens over Runtime Truth; DOORSTEP never auto-executed.

### `helm_revenue`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/revenue`
- **Description:** Verified settled revenue from hash-chained HochLedger only. Zero settled dollars is observed zero — not green earning. Never invent Stripe dashboard balances.

### `helm_security_events`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/security/events`
- **Description:** HIGH-severity security findings eligible for speech (rate-limited). Does not speak secrets. Use for incident awareness, not auto-remediation.

### `helm_grok_tool_pack`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/grok-pack`
- **Description:** Export founder Grok Voice tool pack (JSON) for binding tools to HELM.

### `helm_tts_status`

- **Method:** `GET`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/tts/status`
- **Description:** TTS provider status. local_tts always available; ElevenLabs READY only when key + paid policy allow. Use when Grok Voice Agents has no built-in voice.

### `helm_tts_speak`

- **Method:** `POST`
- **URL:** `https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/tts/speak`
- **Description:** Synthesize speech via HELM ElevenLabs (premium). Pass format=json for base64 audio when Grok has no built-in TTS. Fails closed to local_tts if not configured — do not invent audio.

## Smoke checks

- `GET https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/health`
- `GET https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/brief`
- `GET https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/revenue`
- `GET https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/security/events`
- `GET https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/factory/HASF`
- `GET https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/role/ciso`

Persona source: `docs/prompts/helm_voice_executive_commander.md` — copy that file into the Grok agent use-case field.
