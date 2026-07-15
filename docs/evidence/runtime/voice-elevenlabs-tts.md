# HELM Voice — ElevenLabs TTS integration

**Date:** 2026-07-15  
**Doctrine:** paid TTS fail-closed · secrets never logged · fallback local_tts  

## Why

Grok Voice Agents may include built-in voices. When they do not (or when HELM desk needs a fixed premium voice), HELM provides **ElevenLabs** as an optional TTS path.

## Delivered

| Path | Behavior |
|------|----------|
| `GET /api/v1/helm/voice/tts/status` | Provider readiness (no API key leakage) |
| `POST /api/v1/helm/voice/tts/speak` | `format=audio` → mpeg; `format=json` → base64 |
| `backend/voice/elevenlabs_tts.py` | Sanitize → ElevenLabs API → audio |
| `/voice` desk | TTS select: Local / Auto / ElevenLabs |
| Grok tools | `helm_tts_status`, `helm_tts_speak` |

## Enable (founder)

1. `export ELEVENLABS_API_KEY=...`
2. Optional: `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID`
3. `export HELM_ELEVENLABS_TTS=1` **or** policy `elevenlabs_enabled: true`
4. Policy: `paid_providers_allowed: true` (default is **false**)
5. Restart HELM LIVE or `POST /api/v1/helm/voice/policy/reload` after YAML edit

Without all of the above → **BLOCKED**, clients use **local_tts**.

## Tests

Unit: fail-closed without key; blocked when paid=false even if key present; routes return 503 fallback.
