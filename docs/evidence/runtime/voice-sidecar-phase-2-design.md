# Voice Sidecar Phase 2 — Backend Voice Policy Design

**Status:** DESIGN / PROPOSAL ONLY — no production code changed by this document.
**Date:** 2026-07-16
**Risk class:** SAFE_DOC (per `has_live_project_tracker/data/operator_next_actions.json` →
`recommended_next_action.id = facilitation-phase-2-design`,
`expected_evidence = docs/evidence/runtime/voice-sidecar-phase-2-design.md`)
**Doctrine:** no_fake_green · unknown_is_unknown · stale_is_not_live · doorstep_founder_only ·
paid_tts_fail_closed · voice_is_interface_not_intelligence

This design covers the four items named in the recommended next action and task brief:
(1) cost gates — per-call + budget ceilings + provider fallbacks + DOORSTEP tie-in,
(2) persistent storage — schema, location, retention,
(3) failure modes, and (4) a testable acceptance checklist.

Everything below is split into **EXISTS TODAY (grounded, cited)** vs **PROPOSED (Phase 2)**.
Proposals are labeled and must not be read as shipped.

---

## 0. Grounding — what actually exists today

### 0.1 Phase 1 (frontend voice sidecar), shipped 2026-07-02

Grounded in:
- `docs/evidence/runtime/voice-sidecar-phase-1-plan.md`
- `docs/evidence/runtime/voice-sidecar-phase-1-implementation.md`

Phase 1 was **frontend-only**: a `<script id="voice-sidecar">` block in `frontend/index.html`
using the browser's native `window.speechSynthesis.speak()` (local TTS). Zero cost, zero network,
no mic, no STT. Defaults: `VOICE_ENABLED=false`, `VOICE_MODE=local_tts`,
`VOICE_DAILY_BUDGET_USD=0` (interpreted as "no paid providers; local TTS allowed when operator
toggles"), `VOICE_PAID_PROVIDERS_ALLOWED=false`, severity gate `WARNING`, rate limit 10 events/hr,
secrets redacted via `sanitizeForSpeech`. Phase 1 explicitly named the Phase 2 blockers as:
"Backend voice_policy.py, xAI TTS integration, paid provider support, persistent policy storage,
advanced rate limiting with budget tracking"
(`voice-sidecar-phase-1-implementation.md`, "Remaining blockers").

### 0.2 A backend voice layer ALREADY shipped after Phase 1 (2026-07-15)

**Important correction to the naive "Phase 2 = build the backend" framing.** Between Phase 1 and
today, a substantial backend voice executive layer was implemented and is LIVE. This design must
build **on top of** it, not pretend it is greenfield. Grounded in:
- `docs/evidence/runtime/voice-executive-e2e-integration.md` (2026-07-15, 12 passed)
- `docs/evidence/runtime/voice-elevenlabs-tts.md` (2026-07-15)
- `docs/evidence/runtime/voice-v1-factory-role-agents.md`,
  `voice-v2-extended-factories.md`, `voice-v3-revenue-security-grok-pack.md`

Concretely, these files exist and are the substrate for Phase 2:

| Component | Path | What it does today |
|-----------|------|--------------------|
| Declarative policy | `config/voice_policy.yaml` | Fail-closed policy: `daily_budget_usd: 0`, `paid_providers_allowed: false`, `elevenlabs_enabled: false`, `doorstep_blocked_verbs`, `redact_patterns`, `freshness_budget_seconds: 300`, `staging_dir`, `audit_log` |
| Policy loader | `backend/voice/policy.py` | `load_voice_policy()` (lru_cached, fail-closed `_DEFAULTS`), `is_doorstep_verb()`, `mode_allowed()`, `staging_dir()`, `audit_log_path()`, `get_policy_public()` |
| Paid TTS provider | `backend/voice/elevenlabs_tts.py` | `elevenlabs_config_status()` + `synthesize_speech()`; fail-closed (READY only if key present AND paid allowed AND explicitly enabled); sanitizes before send; network only to `api.elevenlabs.io` |
| Command registry | `backend/voice/commands.py` | Intents mapped to `READ_ONLY` / `STAGE_ONLY` / `DOORSTEP` modes |
| Execution + staging + audit | `backend/voice/briefing.py` | `execute_voice_command()`, DOORSTEP block, `_stage_route()` / `_stage_mission()` → `artifacts/voice/staging/*.json`, `_audit()` → append-only JSONL |
| HTTP router | `backend/voice/router.py` | `/api/v1/helm/voice/*` incl. `/tts/status`, `/tts/speak`, `/command`, `/policy`, `/brief`, `/sanitize`, `/tools` |
| Tool catalog | `config/voice_agent_tools.json` | Grok Voice tool binding + doctrine (`paid_tts_fail_closed`, `doorstep_founder_only`) |
| Tests | `tests/unit/test_helm_voice_executive.py` | 12 passed (policy fail-closed, redaction, DOORSTEP block, stage-only artifact) |

### 0.3 DOORSTEP posture as it exists today (grounded)

`backend/voice/briefing.py::execute_voice_command()` resolves a command, then:
- if `mode == "DOORSTEP"` or `is_doorstep_verb(cmd["id"])` → returns
  `status: "DOORSTEP"`, `labels: {"execution": "BLOCKED", "gate": "DOORSTEP"}`, and speaks
  "requires founder approval … Voice will not execute deploy, spend, keys, sign, or money moves"
  (`briefing.py` lines ~800-820). Audited as `voice_command_doorstep_blocked`.
- `STAGE_ONLY` commands write a reversible artifact to `artifacts/voice/staging/*.json` with
  `"execution": "NOT_EXECUTED"` and are never run.
- `doorstep_blocked_verbs` in `config/voice_policy.yaml`:
  `deploy, deploy_prod, git_push, spend, stripe_live, provision_keys, rotate_keys, sign,
  notarize, app_store_submit, move_money, clear_release_go, bypass_approval`.

### 0.4 The real Phase 2 gap (grounded, this is the load-bearing finding)

**Cost gating is DECLARED but NOT ENFORCED.** Evidence:
- `config/voice_policy.yaml` sets `daily_budget_usd: 0`, and `backend/voice/policy.py`
  surfaces it in `get_policy_public()` (line ~145) — but **grep of `backend/voice/` for
  `budget` / `cost_usd` / `usage` finds no dollar-accounting enforcement path.** The only
  `budget` uses are `freshness_budget_seconds` (staleness) and the security-event rate window.
- `backend/voice/router.py` line ~343 emits a static `"cost_usd": 0` for `local_tts` — this is a
  label, not a meter.
- The paid path (`elevenlabs_tts.py::synthesize_speech`) is gated ONLY by booleans
  (`key_present AND paid AND enabled_request`). Once those three are true, there is **no
  per-call cost estimate, no cumulative spend counter, and no ceiling check** before the
  `urllib.request.urlopen` call to ElevenLabs. So `daily_budget_usd` today is aspirational.
- Persistence today = append-only `data/runtime/voice_command_audit.jsonl` (commands) + loose
  JSON staging files. There is **no structured voice-session/usage store, no per-day rollup,
  no retention policy** (UNKNOWN whether the JSONL is ever rotated — no rotation code found).

**Therefore Phase 2's core job is: make the money real.** Turn `daily_budget_usd` from a
displayed number into an enforced ceiling, add per-call cost estimation, an ordered provider
fallback chain, a durable usage ledger, retention, and tie budget-exhaustion into the existing
DOORSTEP escalation so paid voice stages at the founder door instead of silently spending.

---

## 1. Cost gates (PROPOSED — Phase 2)

### 1.1 Per-call cost gate (pre-flight, fail-closed)

Proposed new module `backend/voice/cost.py` (PROPOSED — does not exist today), invoked by
`elevenlabs_tts.synthesize_speech()` **before** the network call.

Proposed pre-flight sequence for any paid TTS call:
1. Sanitize text (already done today via `sanitize_for_speech`) and compute `billable_chars`
   = `len(clean)` (already bounded by `max_speech_chars: 1200`).
2. `estimated_cost_usd = billable_chars * provider_rate_usd_per_char` where the rate is read
   from a new policy block (see 1.4). Estimation is deterministic and testable offline.
3. Reject the call fail-closed if ANY of:
   - `estimated_cost_usd > per_call_ceiling_usd`, OR
   - `today_spend_usd + estimated_cost_usd > daily_budget_usd`, OR
   - `month_spend_usd + estimated_cost_usd > monthly_budget_usd`.
4. On rejection: return the existing `(ok=False, meta={status: "BLOCKED", fallback: "local_tts"})`
   shape (`elevenlabs_tts.py` already returns exactly this on not-ready), with
   `reason: "budget_ceiling"` and the numbers, and fall back to `local_tts` (zero cost).
5. On acceptance: proceed, then **record actual spend** post-call (see §2). Estimation gates;
   the ledger records truth. Discrepancies between estimate and provider-reported usage are
   logged, not hidden (no_fake_green).

Doctrine ties: `daily_budget_usd: 0` (today's default) means **every paid call is rejected** —
this is the correct fail-closed default and must remain the shipped default. Local TTS stays free
and always available.

### 1.2 Budget ceilings (three tiers)

| Ceiling | Proposed policy key | Default | Meaning |
|---------|--------------------|---------|---------|
| Per-call | `per_call_ceiling_usd` | `0.05` | Hard cap on a single utterance's estimated cost |
| Daily | `daily_budget_usd` | `0` (existing key, now ENFORCED) | Rolling 24h / calendar-day cap |
| Monthly | `monthly_budget_usd` | `0` | Calendar-month cap; belt-and-suspenders |

All three are checked; the tightest binds. `0` = disabled = fail-closed (no paid spend). The
existing default of `daily_budget_usd: 0` therefore keeps the system exactly as safe as today
until the founder explicitly funds a ceiling.

### 1.3 Provider fallback chain

Today there are three notional providers (`policy.py::get_policy_public` → `tts_providers`):
`local_tts` (AVAILABLE, cost 0), `elevenlabs` (fail-closed), `grok_builtin` (EXTERNAL).

Proposed **ordered, cost-aware fallback** resolved per call:
```
1. grok_builtin   — if the Grok Voice Agent supplies its own voice, use it (cost accounted by xAI, not HELM). PREFERRED when present.
2. elevenlabs     — HELM premium path; ONLY if cost gate (§1.1) passes AND fail-closed flags satisfied.
3. local_tts      — always-available, zero-cost floor. Never gated. This is the guaranteed terminal fallback.
```
Rule: **the chain always terminates at `local_tts`**, so a budget rejection or provider error
degrades to free speech rather than to silence or to an uncontrolled retry. Provider selection
and the reason for each downgrade are recorded in the usage ledger (§2).

### 1.4 Proposed policy additions (config/voice_policy.yaml — PROPOSED, not yet written)

```yaml
# --- PROPOSED Phase 2 cost block (additive; defaults preserve today's fail-closed posture) ---
cost:
  enabled: false                 # master switch; false => paid TTS stays fully blocked
  per_call_ceiling_usd: 0.05
  daily_budget_usd: 0            # promote existing top-level key into enforced meaning
  monthly_budget_usd: 0
  doorstep_on_budget_exhaustion: true   # see §1.5
  providers:
    elevenlabs:
      usd_per_1k_chars: 0.30     # PLACEHOLDER rate — founder must confirm against live pricing; UNKNOWN until verified
      estimation_only: true      # estimate gates; provider-reported usage reconciles in ledger
```
NOTE: `usd_per_1k_chars` is a **placeholder** — the true ElevenLabs rate depends on the founder's
plan and is **UNKNOWN** in-repo. Phase 2 must not hard-code a rate that pretends to be authoritative;
it reads it from policy and labels it estimate.

### 1.5 DOORSTEP tie-in (the key integration)

Paid voice is a form of `spend`, and `spend` is already a `doorstep_blocked_verb`
(`config/voice_policy.yaml`) that `execute_voice_command` blocks. Phase 2 extends the **same**
DOORSTEP posture to cost:

- **Funding a budget** (raising `daily_budget_usd` / `monthly_budget_usd` above 0, or flipping
  `cost.enabled: true`, or `paid_providers_allowed: true`) is a founder-gated change. It stays a
  YAML edit the founder makes (fail-closed, gitignored env per `voice-elevenlabs-tts.md`), never a
  voice- or agent-initiated action. This matches HARD RULE (3) founder-gated actions.
- **Budget-exhaustion escalation:** when `doorstep_on_budget_exhaustion: true` and a paid call is
  rejected because a ceiling would be crossed, Phase 2 emits a DOORSTEP-shaped escalation
  reusing the existing pattern: `status: "DOORSTEP"`, `labels: {execution: "BLOCKED",
  gate: "DOORSTEP"}`, speech = "Voice budget reached; approve additional spend on the doorstep."
  It does **not** auto-raise the ceiling. The call itself falls back to `local_tts` so the founder
  still hears the answer for free.
- **Staging, not spending:** any attempt to cross a ceiling produces a staged artifact under
  `artifacts/voice/staging/*.json` (reusing `_stage_*` in `briefing.py`, `execution: NOT_EXECUTED`)
  describing the requested spend, for founder review. Consistent with today's STAGE_ONLY posture.

Net: paid voice calls "stage at the founder door" exactly as deploy/spend/keys already do.

---

## 2. Persistent storage (PROPOSED — Phase 2)

### 2.1 What persists today (grounded)

- Command audit: append-only JSONL at `data/runtime/voice_command_audit.jsonl`
  (`policy.py::audit_log_path`, written by `briefing.py::_audit`). One JSON object per line.
- Staging artifacts: `artifacts/voice/staging/route_*.json`, `mission_*.json`
  (`briefing.py::_stage_route/_stage_mission`).
- No usage/session/cost store exists. No retention/rotation code found (retention = UNKNOWN today).

HARD-RULE COMPLIANCE: this design **does not modify** any existing `*.jsonl` ledger, the swarm DB,
or `has_live_project_tracker/data` runtime files. The audit JSONL is left exactly as-is. Phase 2
storage is **additive and separate**.

### 2.2 Proposed voice usage ledger

Proposed location (additive, new file, not an existing ledger):
`data/runtime/voice_usage_ledger.jsonl` — append-only, one record per TTS synthesis attempt
(accepted or rejected). Append-only mirrors the existing audit convention and is crash-safe.

Proposed record schema (`schema: helm-voice-usage-v1`):
```json
{
  "schema": "helm-voice-usage-v1",
  "session_id": "vs_2026-07-16T14-02-11Z_ab12",
  "event_id": "ve_...",
  "observed_at": "2026-07-16T14:02:11Z",
  "provider": "elevenlabs | local_tts | grok_builtin",
  "mode": "READ_ONLY | STAGE_ONLY | DOORSTEP",
  "command_id": "executive_brief",
  "billable_chars": 812,
  "estimated_cost_usd": 0.024,
  "actual_cost_usd": 0.0244,          "// provider-reported when available, else null (UNKNOWN)",
  "gate_result": "ALLOWED | BLOCKED_BUDGET | BLOCKED_FAILCLOSED | FALLBACK_LOCAL",
  "budget_snapshot": { "daily_spend_before_usd": 0.31, "daily_budget_usd": 1.00 },
  "fallback_from": "elevenlabs",       "// null unless a downgrade occurred",
  "redacted": true
}
```
Never stored: raw secrets, API keys, or unsanitized text (text is sanitized upstream; the ledger
stores `billable_chars`, not the spoken content, to avoid leaking sensitive briefing text).

### 2.3 Proposed session record + daily rollup

- **Session** (`schema: helm-voice-session-v1`): opened when the `/voice` desk or a Grok tool
  begins a voice interaction; carries `session_id`, `origin` (local/tailnet), `started_at`,
  `ended_at`, counts, and `session_cost_usd`. Enables "what did voice cost this session" briefs.
- **Daily rollup** (`data/runtime/voice_usage_daily.json`, PROPOSED): a small rewritable JSON
  keyed by UTC date `{ "2026-07-16": { "calls": 12, "usd": 0.29, "blocked": 3 } }`. This is the
  fast-read source for the cost gate's `today_spend_usd` check (§1.1) so the gate does not have to
  scan the full JSONL on every call. Rollup is derived/regenerable from the ledger (source of
  truth stays the append-only JSONL — no_fake_green: rollup is a cache, ledger is truth).

### 2.4 Retention

- `voice_usage_ledger.jsonl`: retain 90 days, then roll to
  `data/runtime/archive/voice_usage_ledger_YYYYMM.jsonl.gz` (PROPOSED retention policy — none
  exists today). Rotation runs on a lightweight scheduled check, never touching the live file
  mid-write (rotate-on-boot or size threshold).
- `voice_usage_daily.json`: retain trailing 400 days inline (tiny), older keys pruned into the
  monthly archive.
- Staging artifacts (`artifacts/voice/staging/*.json`): retain 30 days; already-consumed stages
  may be pruned by an existing housekeeping job — CURRENT retention is UNKNOWN, so Phase 2 should
  add an explicit sweep rather than assume one.
- The existing `voice_command_audit.jsonl` retention is left to whatever governs it today
  (UNKNOWN, unchanged by this design).

### 2.5 Why JSONL + JSON rollup, not the swarm DB

HARD RULE (2) forbids modifying the swarm DB. Using append-only JSONL + a derived JSON rollup
keeps Phase 2 storage fully additive, crash-safe, human-auditable, and consistent with the
existing `_audit` pattern, with zero risk to the live soak or the DB. If a DB-backed store is
later desired, the JSONL is a clean import source. (DB option = PROPOSED FUTURE, not Phase 2.)

---

## 3. Failure modes (PROPOSED handling, fail-closed)

| # | Failure | Detection | Fail-closed behavior |
|---|---------|-----------|----------------------|
| F1 | Budget ceiling would be exceeded | Pre-flight cost gate (§1.1) | Reject paid call, fall back to `local_tts`, DOORSTEP escalation if configured, ledger `BLOCKED_BUDGET` |
| F2 | ElevenLabs API error / timeout | `synthesize_speech` HTTPError/except (already returns `status:ERROR, fallback:local_tts` today) | Downgrade to `local_tts`; ledger `FALLBACK_LOCAL`; never retry-storm |
| F3 | Missing/invalid API key | `elevenlabs_config_status` `key_present=false` (exists today) | `status: BLOCKED`; `local_tts` |
| F4 | Paid flag off but call attempted | `paid=false` check (exists today) | BLOCKED with explicit reason; `local_tts` |
| F5 | Policy YAML missing/corrupt | `load_voice_policy` try/except → `_DEFAULTS` (exists today) | Fall back to hard-coded fail-closed defaults (`daily_budget_usd: 0`) |
| F6 | Rate limit exceeded | `max_events_per_hour` (policy) | Suppress speech; no spend; ledger note |
| F7 | Estimate ≠ provider-reported cost | Post-call reconcile in ledger | Record both; if actual > estimate by threshold, tighten next-call estimate; surface discrepancy (no_fake_green) |
| F8 | Ledger write fails | `_audit`-style try/except | Do not crash the request; but if the **usage** ledger cannot be written, treat as fail-closed for paid calls (no untracked spend) — divergence from audit's silent-swallow: money must be tracked or not spent |
| F9 | Daily rollup stale/missing | Regenerate from JSONL on read | Rollup is a cache; ledger is truth; regenerate rather than trust a stale cache |
| F10 | Clock skew / day boundary | UTC-only day keys | Ceilings evaluated in UTC to avoid double-spend across local midnight |
| F11 | Sanitizer would emit `[REDACTED]` only | Existing check in `synthesize_speech` | Block empty/fully-redacted speech; no spend |
| F12 | Secret in text | `redact_patterns` + `sanitize_for_speech` (exists today) | Redact before estimation, ledger, and network |

Design invariant: **no code path spends money without a successful pre-flight gate AND a
durable usage-ledger write.** Local TTS is always the safe floor.

---

## 4. Testable acceptance checklist (PROPOSED)

Grounded to extend `tests/unit/test_helm_voice_executive.py` (12 passing today). Each item is
offline-testable without real spend (mock the ElevenLabs network call).

Cost gate:
- [ ] With `daily_budget_usd: 0` (default), any paid TTS request returns BLOCKED and falls back to `local_tts`; ledger records `BLOCKED_BUDGET`; **zero** network call to ElevenLabs is made.
- [ ] With a funded daily budget, a call whose `estimated_cost_usd` fits is ALLOWED; a call that would exceed `per_call_ceiling_usd` is BLOCKED even if the daily budget has room.
- [ ] Cumulative spend across N mocked calls correctly blocks the call that would cross the daily ceiling; the prior calls succeed.
- [ ] Monthly ceiling blocks independently of daily (set daily high, monthly low → blocked).
- [ ] Estimation is deterministic: same sanitized text → same `estimated_cost_usd`.

Provider fallback:
- [ ] Chain terminates at `local_tts`: a forced ElevenLabs error (F2) and a budget rejection (F1) both yield free local speech, never silence.
- [ ] `fallback_from` is recorded whenever a downgrade occurs.

DOORSTEP tie-in:
- [ ] Budget exhaustion with `doorstep_on_budget_exhaustion: true` returns `status: DOORSTEP`, `labels.gate = DOORSTEP`, and stages an artifact under `artifacts/voice/staging/` with `execution: NOT_EXECUTED`.
- [ ] Voice/agents cannot raise a budget ceiling (no endpoint mutates cost policy; only founder YAML/env edits do). Attempting a `spend`-class verb still hits the existing DOORSTEP block.

Persistence + retention:
- [ ] Every synthesis attempt (allowed or blocked) appends exactly one `helm-voice-usage-v1` record; no raw text, keys, or secrets appear in it.
- [ ] Daily rollup is regenerable from the JSONL and matches a full-scan recomputation.
- [ ] Retention sweep archives records older than 90 days without corrupting or touching the live file mid-write; existing `voice_command_audit.jsonl` is untouched.
- [ ] If the usage ledger write fails, paid calls fail-closed (F8) — a test forcing a write error asserts no "LIVE" paid result is returned.

Fail-closed / doctrine:
- [ ] Corrupt/missing `voice_policy.yaml` → `_DEFAULTS` with `daily_budget_usd: 0` (no spend possible).
- [ ] Fully-redacted text (F11) is never sent and never billed.
- [ ] All existing 12 tests in `tests/unit/test_helm_voice_executive.py` still pass (no regression).

Release-gate parity (per Phase 1 precedent):
- [ ] `no_fake_green`: estimate-vs-actual discrepancies are surfaced, not hidden; rollup labeled cache, ledger labeled truth; placeholder pricing labeled UNKNOWN until founder-confirmed.

---

## 5. Explicit scope boundaries

- This document changes **no** production code, no `*.jsonl`, no swarm DB, no
  `has_live_project_tracker/data` runtime files, and does not touch the running soak.
- Funding budgets, providing keys, and flipping `paid_providers_allowed`/`cost.enabled` remain
  **founder-gated** actions performed via gitignored env / YAML by the founder.
- ElevenLabs per-char pricing in §1.4 is a labeled **placeholder / UNKNOWN** pending founder
  confirmation against live account pricing.
- Grok built-in voice cost accounting is external to HELM and treated as **UNKNOWN** in the
  ledger (`actual_cost_usd: null`) unless xAI reports it.

## 6. Evidence paths

- This design: `docs/evidence/runtime/voice-sidecar-phase-2-design.md`
- Phase 1 grounding: `docs/evidence/runtime/voice-sidecar-phase-1-plan.md`,
  `docs/evidence/runtime/voice-sidecar-phase-1-implementation.md`
- Existing backend grounding: `docs/evidence/runtime/voice-executive-e2e-integration.md`,
  `docs/evidence/runtime/voice-elevenlabs-tts.md`
- Live code grounded: `config/voice_policy.yaml`, `config/voice_agent_tools.json`,
  `backend/voice/policy.py`, `backend/voice/elevenlabs_tts.py`, `backend/voice/commands.py`,
  `backend/voice/briefing.py`, `backend/voice/router.py`,
  `tests/unit/test_helm_voice_executive.py`
- Next-action source: `has_live_project_tracker/data/operator_next_actions.json`
