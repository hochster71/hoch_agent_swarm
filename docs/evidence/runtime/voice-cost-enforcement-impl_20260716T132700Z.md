# Voice Cost Enforcement — Phase 2 Implementation Evidence

**Status:** IMPLEMENTED (additive, backward-compatible). Real runnable code + real tests.
**Date:** 2026-07-16T13:27:00Z
**Doctrine:** no_fake_green · fail_closed · unknown_is_unknown · doorstep_founder_only · paid_tts_fail_closed
**Design implemented:** `docs/evidence/runtime/voice-sidecar-phase-2-design.md`

---

## 0. Headline

`daily_budget_usd` is now **truly enforced**, not merely displayed. Before this change,
`config/voice_policy.yaml::daily_budget_usd` was surfaced by `backend/voice/policy.py::get_policy_public()`
but gated **nothing** — `backend/voice/elevenlabs_tts.py::synthesize_speech` hit the paid ElevenLabs
API after only three boolean checks (key present / paid allowed / enabled). This change inserts a
**fail-closed pre-flight cost gate** in front of the paid network call. With the shipped defaults
(`cost_enabled: false`, `daily_budget_usd: 0`, `monthly_budget_usd: 0`) **every paid call is blocked**
and degrades to the always-free `local_tts` path — exactly as safe as before, now provably so.

No paid provider, key, or secret was enabled. No network call to ElevenLabs was made. Nothing was
deployed. The 24h Phase C soak was not touched.

---

## 1. What was built

### New module — `backend/voice/cost_gate.py` (399 lines)
- `estimate_cost_usd(chars, provider, policy)` — deterministic pre-flight estimate
  = `chars/1000 × usd_per_1k_chars`. Free providers → `0.0`. **Unknown-priced provider → `(None, price_unknown=True, None)`** (fail-closed).
- `preflight_cost_gate(billable_chars, provider, *, policy, ledger_path, now)` — the gate. Fail-closed
  ordering: `cost_disabled` → `provider_price_unknown` → `ledger_unreadable` → `per_call_ceiling`
  → `daily_budget` → `monthly_budget` → **ALLOWED**. Returns a verdict with `allow`, `gate_result`,
  `reason`, `estimated_cost_usd`, `price_unknown`, `doorstep`, `fallback: local_tts`,
  `budget_snapshot`, `staged`, and a ready-to-write `ledger_record`.
- `append_usage(record, ledger_path)` — append-only JSONL writer; returns `False` on failure (load-bearing:
  callers fail-closed → **no untracked spend**, design F8).
- `_read_records` / `daily_rollup` / `_spend_before` — ledger is the source of truth; the daily rollup is a
  **derived cache** regenerable from the JSONL. Missing file → 0 spend; corrupt file → `LedgerError` → block.
- `write_staging_artifact(staged_verdict, staging_dir)` — DOORSTEP-shaped `execution: NOT_EXECUTED`
  artifact (schema `helm-voice-stage-v1`). Not written on the live paid path (verdict returned instead,
  per "return/record the staged verdict; do not create founder-queue entries").
- Three FAIL-CLOSED ceilings read from policy: `per_call_ceiling_usd`, `daily_budget_usd`, `monthly_budget_usd`.
- Provider handling: `local_tts` free & never gated (guaranteed terminal fallback); `elevenlabs` HELM-metered;
  unknown providers → price UNKNOWN → block.
- Usage ledger schema `helm-voice-usage-v1`: `observed_at, provider, billable_chars, estimated_cost_usd,
  actual_cost_usd(=null; provider does not report per-call cost → UNKNOWN), gate_result, reason,
  budget_snapshot, fallback_from, price_unknown, redacted:true`. **No raw text, keys, or secrets stored.**
- Retention: 90-day note only (design §2.4). Nothing is deleted now.

### Config — `config/voice_policy.yaml` (lines 33–45, additive)
`cost_enabled: false`, `per_call_ceiling_usd: 0.05`, `monthly_budget_usd: 0`,
`doorstep_on_budget_exhaustion: true`, `elevenlabs_usd_per_1k_chars: 0.30` (labeled **PLACEHOLDER /
UNKNOWN until founder-confirmed**), `voice_usage_ledger: data/runtime/voice_usage_ledger.jsonl`.
Existing `daily_budget_usd: 0` is unchanged and now enforced.

**Documented deviation from design §1.4:** the design sketched a *nested* `cost:` YAML block. The repo's
dependency-free loader (`backend/voice/policy.py::_parse_yaml_simple`) only supports one nesting level and
does not strip inline comments, so the keys are implemented **flat** with own-line comments. Same semantics,
parseable by the existing loader; no new dependency added.

### Policy loader — `backend/voice/policy.py`
- `_DEFAULTS` gains the six cost keys (lines 28–33) so a missing/corrupt YAML **fails closed** to
  `cost_enabled=False`, zero budgets, ledger path default.
- `get_policy_public()` gains a `cost` block (lines ~154–164) marked `enforced_by: backend/voice/cost_gate.py`
  with `pricing_note: estimate only; UNKNOWN/placeholder until founder-confirmed`.

### Paid entry point — `backend/voice/elevenlabs_tts.py::synthesize_speech` (lines ~108–186)
Added keyword-only `policy` / `ledger_path` injection params (backward-compatible; existing callers such as
`router.py::/tts/speak` unaffected). Pre-flight order:
1. existing boolean readiness gate (unchanged),
2. existing sanitize + empty/fully-redacted check (unchanged),
3. **NEW** `cost_gate.preflight_cost_gate(len(clean), "elevenlabs", ...)` before the `urllib` call:
   - blocked → append blocked ledger record, return `(False, {status: BLOCKED|DOORSTEP, fallback: local_tts, ...}, None)`;
   - allowed → write the ALLOWED record **before** the network call; if the write fails →
     `budget_gate:usage_ledger_unwritable` fail-closed, no network (design F8);
   - success meta now carries `estimated_cost_usd`, `budget_snapshot`, `gate_result`.

`elevenlabs` is the only paid provider entry point in `backend/voice/` (grep of `urlopen` / `api.elevenlabs`
confirms a single network site). `grok_builtin` is billed externally by xAI (UNKNOWN to HELM); `local_tts` is free.

---

## 2. Fail-closed matrix (design §3 → verified by tests)

| # | Condition | Result | gate_result | Test |
|---|-----------|--------|-------------|------|
| F5 | Missing/empty config | BLOCK | BLOCKED_FAILCLOSED (`cost_disabled`) | `test_missing_config_fails_closed`, `test_default_repo_policy_is_failclosed` |
| — | Shipped repo default (`cost_enabled:false`,`daily:0`) | BLOCK → local_tts | BLOCKED_FAILCLOSED | `test_default_repo_policy_is_failclosed` |
| — | UNKNOWN provider price | BLOCK | BLOCKED_FAILCLOSED (`provider_price_unknown`) | `test_unknown_price_blocks_failclosed` |
| F1 | Per-call ceiling exceeded (daily has room) | BLOCK → local_tts | BLOCKED_BUDGET (`per_call_ceiling`) | `test_per_call_ceiling_blocks_even_with_daily_room` |
| F1 | Daily ceiling crossed cumulatively | BLOCK; prior calls succeed | BLOCKED_BUDGET (`daily_budget`) | `test_daily_ceiling_blocks_cumulatively` |
| F1 | Monthly ceiling (daily high, monthly low) | BLOCK | BLOCKED_BUDGET (`monthly_budget`) | `test_monthly_ceiling_blocks_independently_of_daily` |
| — | Under budget | ALLOW | ALLOWED | `test_under_budget_allows` |
| — | Free provider | ALLOW (never gated) | ALLOWED | `test_free_provider_is_zero_and_never_gated` |
| F5b | Ledger exists but unreadable/corrupt | BLOCK | BLOCKED_FAILCLOSED (`ledger_unreadable`) | `test_ledger_unreadable_fails_closed` |
| F8 | Usage ledger unwritable on allowed call | BLOCK, no network | (`usage_ledger_unwritable`) | `test_synthesize_failcloses_when_ledger_unwritable` |
| §1.5 | Budget exhaustion + doorstep on | staged NOT_EXECUTED verdict | BLOCKED_BUDGET + doorstep | `test_budget_exhaustion_stages_at_doorstep` |
| §1.5 | Doorstep disabled | BLOCK, no staged verdict | BLOCKED_BUDGET | `test_doorstep_can_be_disabled` |
| integ | synthesize blocked → **no network call** | (False, local_tts) | BLOCKED_BUDGET | `test_synthesize_blocks_on_budget_and_never_calls_network` |
| integ | synthesize funded → LIVE + 1 ledger record | (True, LIVE) | ALLOWED | `test_synthesize_allows_and_records_when_funded` |

Determinism, append+rollup regeneration, and no-secrets-in-ledger also covered
(`test_estimate_is_deterministic_and_priced`, `test_ledger_append_and_rollup_match_fullscan`).

---

## 3. Real test output (system python3, in-sandbox)

Environment: sandbox `python3` = **3.10.12**, `pytest` **9.1.1**. The repo `.venv` is macOS-only; the
sandbox lacked `fastapi`/`httpx`/`stripe`, which are needed only to *collect/import* the existing test module
and the full FastAPI app (not by the cost gate). These were installed locally in the sandbox (free, no paid
API) to run the regression suite. **No paid provider/key was configured; no ElevenLabs network call was made.**

### New tests — `tests/unit/test_voice_cost_gate.py`
```
$ python3 -m pytest tests/unit/test_voice_cost_gate.py -q
................                                                         [100%]
16 passed in 0.14s
```

### Existing regression — `tests/unit/test_helm_voice_executive.py` (26 tests)
Run in batches to fit the sandbox's per-call time limit; every test passed, 0 failures:
```
# fast surface (policy/sanitizer/doorstep/elevenlabs/resolve/commands/role_unknown)
11 passed, 15 deselected in 0.32s
# executive brief
test_executive_brief_has_labels ......................... 1 passed in 6.50s
# full-app HTTP routes
test_helm_live_api_voice_routes, test_api_factory_and_role_routes ... 2 passed in 16.64s
test_main_app_voice_routes .............................. 1 passed in 1.23s   (after `pip install stripe`)
# role/revenue
2 passed in 30.38s
# factory HASF/HSF
2 passed in 0.51s
# factory HCF/HFF, security_events, grok_pack, stage_route, goal_status, repo_status, brief_includes
7 passed in 18.09s
```
**Tally: 26/26 existing + 16/16 new = 42 passed, 0 failed.** The only transient failure observed was
`test_main_app_voice_routes` raising `ModuleNotFoundError: No module named 'stripe'` — a pre-existing
missing sandbox dependency (imported by `backend/routers/stripe_webhook.py` via `backend.main`), **not** a
regression from this change; it passes once `stripe` is installed.

---

## 4. Safety / doctrine attestation

- **No paid provider or key enabled.** `paid_providers_allowed`, `elevenlabs_enabled`, `cost_enabled` all remain
  `false` in `config/voice_policy.yaml`; no `ELEVENLABS_API_KEY`, `HELM_*` paid env, or secret was set.
- **No real paid API call / no money spent.** The gate makes no network calls; the integration tests mock
  `urllib.request.urlopen` and assert it is **not** invoked on any blocked path.
- **Nothing deployed.** No daemon/launchagent/process was started or restarted; `soak_runner.py`,
  `launch_8factory_moonshot.py`, `secure_sync_hoch200.sh` untouched.
- **No forbidden files modified.** The swarm DB, `has_live_project_tracker/data`, and existing `*.jsonl`
  runtime ledgers were not modified. The new usage ledger writes only under `data/runtime/` and **tests use
  tmp paths** — the real `data/runtime/voice_usage_ledger.jsonl` was never created by this work.
- **Additive / backward-compatible.** The free/local voice path is unchanged; all pre-existing voice tests pass.
- **Not mine, left untouched:** `backend/voice/router.py` shows a 2-line pre-existing working-tree change
  (`mission_state` `computed_at`/`observed_at`) authored before this task — not modified here.

---

## 5. Files created / modified

**Created**
- `backend/voice/cost_gate.py`
- `tests/unit/test_voice_cost_gate.py`
- `docs/evidence/runtime/voice-cost-enforcement-impl_20260716T132700Z.md` (this doc)

**Modified (additive)**
- `config/voice_policy.yaml` (lines 33–45: flat cost-enforcement keys)
- `backend/voice/policy.py` (`_DEFAULTS` cost keys; `get_policy_public()` `cost` block)
- `backend/voice/elevenlabs_tts.py` (`synthesize_speech` pre-flight cost gate + ledger write + cost meta)
