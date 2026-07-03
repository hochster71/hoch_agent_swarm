# Voice Sidecar Phase 1 Plan (2026-07-02)

**Approved Scope**
- Frontend-only, isolated in `frontend/index.html`
- Native browser `SpeechSynthesis` (local TTS, macOS compatible, zero cost, no network, no mic, no STT)
- `VOICE_ENABLED=false` by default
- `VOICE_MODE=local_tts`
- `VOICE_DAILY_BUDGET_USD=0` interpreted as "no paid providers allowed" — local TTS permitted when operator enables toggle
- `VOICE_PAID_PROVIDERS_ALLOWED=false`
- `VOICE_MIN_SEVERITY=WARNING`
- `VOICE_MAX_EVENTS_PER_HOUR=10`
- `VOICE_SPEAK_SECRETS=false`
- `VOICE_REQUIRE_OPERATOR_TOGGLE=true`
- Fail-closed: no speech unless explicitly enabled and policy passes
- Sanitizer redacts secrets, tokens, keys, paths, JSON dumps before speech
- Allowed events: FINAL GO, FINAL NO-GO, release gate failed, human approval required, stale telemetry quarantine, security/public exposure blocked, evidence written, mission ready
- Blocked: INFO below WARNING, secrets, repetitive heartbeats, raw JSON, private data

**Architecture**
- New `<script id="voice-sidecar">` block in `frontend/index.html` (policy constants, `voiceSanitizer`, `voiceEventMapper`, rate limiter, `speakEvent` guard, `SpeechSynthesis` wrapper)
- Small Voice Control Panel added to sidebar (under Local Models nav) or as floating HUD (toggle, mode display, severity, last spoken, mute, test button, policy status)
- `window.HASFVoiceSidecar` test hooks (getPolicy, sanitize, speakEvent, getLastSpoken, getPolicyStatus, resetRateLimitForTest) — no secrets exposed
- No changes to theatrical POD bay, skill cards, NorthStar, PERT, visual baseline (`hoch-pods-theater-reference.jpeg`), or release truth logic
- New test: `tests/e2e/rc54-voice-sidecar-policy.spec.ts` (mocks SpeechSynthesis, verifies toggle, redaction, rate-limit, no network, existing tests still pass)

**Risk Assessment**
Low. Additive only, guarded by defaults and sanitizer. No network, no new deps, no secrets spoken, no visual regression. Playwright will intercept SpeechSynthesis to verify behavior without audible output.

**Test Plan**
- rc54 test: panel renders, disabled by default, test button silent when disabled, enabled allows LOCAL_TTS FINAL GO event, INFO below WARNING silent, secrets redacted, rate-limited, no network calls, visual baseline unchanged
- Full Playwright (140/140)
- `npm --prefix frontend run build`
- `bash scripts/rc29_release_verify.sh`
- `npm run baseline:scan-static`

**Acceptance Criteria**
- Voice disabled by default; no speech on load
- Local TTS only; zero-budget does not disable local voice
- Sanitizer redacts secrets/tokens/paths/JSON before speech
- Only approved events speak when policy passes
- Rate limit, severity, toggle, and operator confirmation enforced
- UI panel shows all required controls and status
- No regression to theatrical UI, visual baseline, or existing tests
- Evidence updated with policy, test results, changed files, Phase 2 blockers (backend policy, xAI integration)

**Evidence paths**
- `docs/evidence/runtime/voice-sidecar-phase-1-plan.md`
- `docs/evidence/runtime/voice-sidecar-phase-1-implementation.md` (post-implementation)

**Single next VS Code action**
Ctrl+Shift+P → "Tasks: Run Task" → "Voice Sidecar Phase 1 Implementation" (or open `docs/evidence/runtime/voice-sidecar-phase-1-plan.md` for final review before edits)