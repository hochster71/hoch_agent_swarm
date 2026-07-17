# AUDIT_03 — Integrations: ElevenLabs Voices + AI Models

- **Scope:** Read-only source audit of `audits/epic-fury-src` (mirror of the live Vercel app `epic-fury-2026.vercel.app`).
- **Date:** 2026-07-16
- **Rules honored:** No files modified, no deploys, no secret VALUES printed (env var NAMES only). NO FAKE GREEN — findings below reflect only what the source shows.
- **Bottom line:** Both integrations are **present and fully wired in code**. Neither is removed, commented out, or stubbed. Every symptom the founder describes maps to **missing/mismatched ENV configuration on the Vercel deployment**, not lost code or a lost binary.

---

## 1. ElevenLabs Voices — STATUS: WIRED / INTACT

### Where it lives
| Concern | File |
|---|---|
| Server API route (calls ElevenLabs) | `app/api/tts/route.ts` |
| Reusable client button | `components/TtsPlayer.tsx` |
| Main consumer — 9-anchor newsroom | `app/dashboard/newsroom/page.tsx` |
| Subscriber gate used by the route | `lib/api-auth.ts` (`requireSubscriber`) |

### What the code actually does (confirmed, not assumed)
- `app/api/tts/route.ts` POSTs to `https://api.elevenlabs.io/v1/text-to-speech/{voiceId}` with header `xi-api-key`, `model_id: 'eleven_turbo_v2_5'`, and voice settings. It reads the key from **`process.env.ELEVENLABS_API_KEY`** (line 48). Full production hardening is present: subscriber gate, per-IP rate limit (20/5min), 25s timeout, and a circuit breaker that trips **only on 401** (bad/expired key).
- The route is **subscriber-gated**: `requireSubscriber(req)` runs first. A logged-out / non-subscriber caller gets **403** back.
- All **9 anchor voices are hard-coded** in `app/dashboard/newsroom/page.tsx` (lines ~67-121) with real ElevenLabs voice IDs (Rachel `21m00Tcm4TlvDq8ikWAM`, Daniel `onwK4e9ZLuTAKqWW03F9`, Matilda, Arnold, Charlotte, Adam, Serena, Joseph, Alice). Voice IDs are NOT env-driven, so a "renamed voice_id env var" is **not** a possible cause here.
- The newsroom has an explicit **graceful fallback to the browser Web Speech API**. The playback logic (lines ~557-607) treats responses as:
  - `200` → play real ElevenLabs audio.
  - `401` → key wrong/expired: mark unavailable for 30 min, fall back to Web Speech.
  - `403` → "session_required" (not signed in / not a subscriber): silently fall back to Web Speech, retry next load.
  - network / `503` / other → transient, fall back to Web Speech, retry next segment.
- The UI renders a banner **"⚠ ElevenLabs AI Voice not configured — Browser speech synthesis active as fallback"** and a setup card telling the user to add `ELEVENLABS_API_KEY`, shown precisely when the key is absent.

### Required ENV VAR NAMES (voices)
- **`ELEVENLABS_API_KEY`** — the only variable required for real voices. (Declared, commented-out, in `.env.example` line 22-23.)
- Indirectly, because the route is subscriber-gated, the Supabase session stack must also work for a real user to reach it: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (see §3).

### Most likely root cause of "the voices are gone" (ranked)
1. **`ELEVENLABS_API_KEY` is not set on the Vercel deployment** (or set on Preview but not Production, or on the wrong project). → route returns 503 → app silently drops to robotic Web Speech and shows the "not configured" banner. This is the single most probable cause and matches the exact symptom.
2. **Key present but invalid/expired/out-of-credits** → ElevenLabs returns 401 → circuit breaker trips for 5 min server-side and the client blocks EL for 30 min, so it sounds "gone" for a while then may recover.
3. **The founder is not viewing as a signed-in subscriber** → `requireSubscriber` returns 403 → silent Web Speech fallback with no error shown. Real voices only play for a logged-in subscriber/admin/QA/founder session.

_Not the cause:_ removed component (present), broken route (intact), or a changed/renamed voice_id (IDs are hard-coded in source, not env).

---

## 2. AI Models (LLMs) — STATUS: WIRED / INTACT (multi-provider, graceful-degradation by design)

### Providers & models found in code
| Provider | Model(s) | Where | Env var |
|---|---|---|---|
| OpenAI | `gpt-4o`, `gpt-4o-mini` | `lib/openai-safe.ts`, `lib/ai-engine.ts`, `lib/foresight-engine.ts` (uses `openai` SDK), plus routes `api/intel/*`, `api/newsroom/generate` & `/seed`, `api/oracle/enhance`, `lib/revenue-engine.ts`, `lib/synthesis-engine.ts`, `lib/kg-engine.ts` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-haiku-20240307` (raw fetch fallback) | `lib/ai-engine.ts` (`_callAnthropic`, `ANTHROPIC_URL`) | `ANTHROPIC_API_KEY` |
| OpenAI DALL·E 3 | image/infographic generation | `lib/visual-engine.ts` | `OPENAI_API_KEY` |
| xAI / Grok | Grok research (AEC) + Grok-2 image | `lib/autonomous-engine.ts`, `lib/visual-engine.ts` | `XAI_API_KEY` (and, in visual-engine, `GROK_API_KEY`) |
| Kling / Runway | video generation (visuals) | `lib/visual-engine.ts`, `lib/governor.ts` | `KLING_API_KEY`, `RUNWAY_API_KEY` |

### Wiring quality (confirmed)
- **Central helper `lib/ai-engine.ts`**: `AI_AVAILABLE = hasValidOpenAIKey() || ANTHROPIC_API_KEY`. `hasValidOpenAIKey()` requires the key to start with `sk-`. It calls OpenAI first, and **falls back to Anthropic Claude haiku** if OpenAI is unavailable (`[AI] OpenAI unavailable — falling back to Claude`). Secrets are redacted from logs; 15s timeouts; input truncation for prompt-injection safety.
- **`lib/openai-safe.ts`**: thin, safe OpenAI chat wrapper; returns `null` (no throw) when the key is missing/invalid — so the app degrades instead of crashing.
- **This is intentional graceful degradation, not a stub.** Nearly every intel route (`forecast`, `world`, `pulse`, `digest`, `breaking`, `extract`, `debate`) and the newsroom generator return **deterministic static fallbacks** with a visible note like *"Enable OPENAI_API_KEY for live AI synthesis"* when no key is set. That is exactly the founder's report: *"the AI models within are not configured."* The app is running in its **keyless fallback mode**, which is why analysis looks canned/static rather than live.
- Dashboards surface the state honestly: `app/dashboard/settings/page.tsx` shows `OPENAI_KEY: SET ✓ / MISSING ✗`; `api/platform/status` reports `GPT-4o / GPT-4o-mini` vs `Fallback mode`; `api/platform/security-scan` raises a CRITICAL finding *"No AI provider configured"* when both OpenAI and Anthropic keys are absent.

### Required ENV VAR NAMES (models)
- **`OPENAI_API_KEY`** — primary; unlocks GPT-4o / GPT-4o-mini everywhere and DALL·E 3 visuals. (Declared, commented, in `.env.example`.)
- **`ANTHROPIC_API_KEY`** — fallback LLM (claude-3-haiku). (Declared, commented, in `.env.example`.)
- Optional/adjacent AI: `XAI_API_KEY` (and `GROK_API_KEY`), `KLING_API_KEY`, `RUNWAY_API_KEY` — only needed for the autonomous-enhancement research loop and image/video visuals, **not** for core intel/newsroom text.

### Most likely root cause of "AI models are not configured"
1. **`OPENAI_API_KEY` (and `ANTHROPIC_API_KEY`) are not set on the Vercel Production environment.** With neither present, `AI_AVAILABLE` is false, every LLM call returns `null`, and the whole app renders its deterministic static fallbacks + "activate OPENAI_API_KEY" notes. This is the expected symptom and the most probable cause.
2. **Key present but malformed** — note `hasValidOpenAIKey()` requires the value to **start with `sk-`**. A project/org-scoped key that does not start with `sk-`, or a stray-whitespace/quoted value, will be treated as invalid and silently ignored (fallback mode). Worth verifying the key format on Vercel.
3. Env set on Preview but not Production, or on a different Vercel project than the live one.

_Not the cause:_ removed engine code (all engines present), or a hard model-name break (model IDs `gpt-4o` / `gpt-4o-mini` / `claude-3-haiku-20240307` are current and valid).

---

## 3. Cross-check — ENV names referenced in code but MISSING from `.env.example`

`.env.example` only declares (commented in most cases): `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `HOSTNAME`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `NEWS_API_KEY`, `GROQ_API_KEY`, `XAI_API_KEY`, `GITHUB_PAT`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`, `VERCEL_DEPLOY_HOOK_URL`, `AUTO_MERGE_ENABLED`.

The code actually references **many more**. The following NAMES are used in code but **absent from `.env.example`** — a real misconfiguration hazard (someone provisioning from the example will miss them):

**Auth / access / identity**
- `CRON_SECRET` (gates all cron routes; fail-closed 503 in prod if unset)
- `ADMIN_EMAIL`, `NEXT_PUBLIC_ADMIN_EMAIL`
- `EPIC_FURY_ADMIN_EMAILS`, `NEXT_PUBLIC_EPIC_FURY_ADMIN_EMAILS`
- `EPIC_FURY_QA_EMAILS`, `NEXT_PUBLIC_EPIC_FURY_QA_EMAILS`
- `EPIC_FURY_INTERNAL_PREVIEW_ENABLED`, `NEXT_PUBLIC_EPIC_FURY_INTERNAL_PREVIEW_ENABLED`
- `NEXT_PUBLIC_ENABLE_GOOGLE_OAUTH`
- `SUPABASE_SERVICE_KEY` (a second, variant name alongside the declared `SUPABASE_SERVICE_ROLE_KEY` — inconsistent naming; verify which the live code path expects)

**Site URLs**
- `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_APP_URL`

**Payments / entitlements**
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_ANNUAL`
- `EPIC_FURY_STRIPE_TEST_MODE`, `NEXT_PUBLIC_EPIC_FURY_STRIPE_TEST_MODE`
- `NEXT_PUBLIC_REVENUECAT_IOS_KEY`, `REVENUECAT_WEBHOOK_SECRET`

**Extra AI / media providers**
- `GROK_API_KEY` — used in `lib/visual-engine.ts`, but `.env.example` only lists `XAI_API_KEY` (and a `GROQ_API_KEY` that is **not referenced anywhere in code**). Note the easy-to-confuse trio: **GROK ≠ GROQ ≠ XAI**. `.env.example` documents GROQ + XAI; code uses XAI + GROK. This naming drift is a likely quiet misconfig.
- `KLING_API_KEY`, `RUNWAY_API_KEY`

**Vercel automation (self-deploy loop)**
- `VERCEL_API_TOKEN`, `VERCEL_TEAM_ID`, `VERCEL_PROJECT_ID`

**Also note — declared but unused:** `NEWS_API_KEY` and `GROQ_API_KEY` are in `.env.example` but not referenced anywhere in the source (stale/aspirational). (Vercel-injected `VERCEL_URL`, `VERCEL_PROJECT_PRODUCTION_URL`, `NODE_ENV` are used in code and are provided automatically by the platform — not misconfig.)

---

## Summary for the founder

- **Voices are NOT gone from the code.** The ElevenLabs integration, all 9 anchor voice IDs, the API route, rate limiting, and the fallback are all present and intact. The app is running on its Web-Speech fallback. **Fix path: confirm `ELEVENLABS_API_KEY` is set (and valid/in-credit) on the live Vercel Production environment for the correct project, and view the newsroom as a signed-in subscriber.**
- **AI models are NOT gone or stubbed.** OpenAI (gpt-4o / gpt-4o-mini) with an Anthropic (claude-3-haiku) fallback are fully wired; the app is in deterministic keyless-fallback mode by design. **Fix path: set `OPENAI_API_KEY` (must start with `sk-`) — optionally `ANTHROPIC_API_KEY` — on live Vercel Production.**
- **Exact env NAMES each needs (values never shown, set them on Vercel):**
  - Voices: **`ELEVENLABS_API_KEY`** (+ working `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` for the subscriber gate).
  - Models: **`OPENAI_API_KEY`** (primary), **`ANTHROPIC_API_KEY`** (fallback); optional `XAI_API_KEY`/`GROK_API_KEY`, `KLING_API_KEY`, `RUNWAY_API_KEY` for visuals/AEC.
- **Likely underlying misconfig source:** `.env.example` is significantly out of date vs. the code (missing ~25 referenced names, plus a GROK/GROQ/XAI naming drift and a `SUPABASE_SERVICE_KEY` vs `SUPABASE_SERVICE_ROLE_KEY` variant). Anyone configuring Vercel from the example alone would omit required keys — a plausible reason a previously-working feature reads as "gone."

_No values were read or printed. No source files were modified. Verification of what is actually set on Vercel Production requires reading the deployment's env (dashboard or `vercel env ls`) — that is the recommended next, still-read-only, step and is Michael's authenticated action._
