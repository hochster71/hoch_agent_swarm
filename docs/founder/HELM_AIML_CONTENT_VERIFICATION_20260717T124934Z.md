# HELM — AI/ML + Content Pipeline Verification

**Generated:** 2026-07-17T12:49:34Z
**Scope:** Honest verification that HELM's AI/ML and content pipelines are real and firing.
**Method:** Live HTTP against production, source reading of the staged Epic Fury tree, and **actual execution** of product engines on sample inputs. READ-ONLY audit. No keys typed, no deploys, no money moved.
**Doctrine:** NO FAKE GREEN — nothing below is marked green without captured evidence.

---

## Bottom line

The **OSINT ingestion + deterministic-ML pipeline is genuinely LIVE and firing** in production, and **all three product engines run for real** and emit valid artifacts. The **one honest red flag: the OpenAI/Anthropic LLM narrative layer is wired in code but is NOT active in production** — the live `/api/intel/digest` returns `aiAvailable: false` and `aiNarrative: null`, i.e. no `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` is set on the Vercel deployment, so the LLM engines are gracefully degraded. Content fixes (banner + percentage clamp) are confirmed in place on the live site.

---

## Green / Red table

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Epic Fury `/api/intel/digest` returns real structured data | 🟢 GREEN | HTTP 200, 3076 bytes; `conflictDay:139`, `verifyRate:45`, `sourceCount:20`, `total24h:100`; real news titles from named wires |
| 2a | OSINT ingestion → Supabase → deterministic engines live | 🟢 GREEN | Digest theaters/keyDevelopments carry real dated headlines (Guardian, Al Jazeera, Kurdistan 24…) pulled from Supabase `intel` table |
| 2b | Deterministic ML models (ORACLE-9, COMPASS, HERALD-3) firing | 🟢 GREEN | Digest `topThreats` (Bayesian ORACLE probabilities) + `economics` (COMPASS cascade) populated; pure-TS engines run regardless of keys |
| 2c | OpenAI/Anthropic **LLM** narrative layer active in prod | 🔴 RED | Live digest: `aiAvailable:false`, `aiNarrative:null`. Code is fully wired (`safeOpenAIChatCompletion`) but **no API key is set on Vercel** → degrades to deterministic-only |
| 3a | HFF Runway engine runs on sample → real numbers + XLSX/PDF | 🟢 GREEN | Ran `generateRunwayPacket` on 25-txn sample: 30/60/90d net = 972.41/5390.82/8548.52; est annual tax 19,654.18; XLSX 13,912 B (`PK`), PDF 1,896 B (`%PDF-`) |
| 3b | HFF Invoice-Aging engine runs on sample → real numbers + XLSX/PDF | 🟢 GREEN | Ran `generateAgingReport`: 7 outstanding, totalOutstanding $19,200; buckets incl. 90+d=$14,500(3); XLSX 10,324 B (`PK`), PDF 2,278 B (`%PDF-`) |
| 3c | HRF Clarity-Briefs citation linter runs | 🟢 GREEN | `unittest`: **12/12 OK** incl. moat tests; CLI end-to-end produced `coverage=100%` brief (.md/.html/.json) |
| 4a | Homepage banner is accurate "LIVE OSINT FEED + MODELED SIMULATION" | 🟢 GREEN (live) | Live site banner: `UNCLASSIFIED // OPEN-SOURCE // LIVE OSINT FEED + MODELED SIMULATION — CHECK EACH PANEL'S LABEL` |
| 4b | Old blanket "NOT REAL-TIME" banner removed from live | 🟡 NOTE | Live = fixed. **Staged `audits/epic-fury-src/app/page.tsx:96` still shows the OLD banner** — the staged tree is a pre-fix snapshot, not what is deployed |
| 4c | >100% percentage clamp fix in place | 🟢 GREEN | Pervasive clamps: `war-stats.ts` `Math.min(99/95/94,…)`; `ai-engine.ts`/`kg-engine.ts`/`herald-engine.ts`/`news-fetcher.ts` `Math.max(0, Math.min(100, …))`; digest `verifyRate` structurally bounded (verified≤total) |

---

## 1. Live pipeline evidence — `GET https://epic-fury-2026.vercel.app/api/intel/digest`

HTTP **200**, 3076 bytes, ~1.1s. Sample of the real structured payload:

```json
{"ok":true,"conflictDay":139,"dtg":"1390800Z JUL 2026","total24h":100,
 "verified24h":45,"verifyRate":45,"sourceCount":20,
 "theaters":[{"name":"Persian Gulf / Hormuz","count":20,"verified":11,"avgConf":53,
   "topTitle":"Marines board tanker amid blockade of Iranian ports...","topSource":"The Guardian — World"}],
 "topThreats":[{"label":"6th Ballistic Missile Barrage Risk","probability":40,"severity":"MODERATE"}],
 "economics":{"brentUsd":116.9,"hormuzThroughputMbpd":8.9,"lloydWarRiskPct":3.5},
 "assessmentLevel":"ELEVATED",
 "aiAvailable":false,"aiNarrative":null}
```

The named-wire headlines with real timestamps prove the **news-fetcher → Supabase → digest** ingest chain is live. ORACLE-9 threat probabilities and COMPASS economics are computed by pure-TypeScript models that fire independent of any API key. **`aiAvailable:false` is the honest limit** — the LLM synthesis narrative is off in prod.

## 2. AI/ML engine inventory (staged `audits/epic-fury-src/lib/`)

**LLM-wired (require `OPENAI_API_KEY`, `sk-`-validated via `lib/openai-safe.ts`; `AI_AVAILABLE` also accepts `ANTHROPIC_API_KEY`) — all degrade to `null`/fallback when unset:**
- `ai-engine.ts` (NEXUS core; GPT-4o-mini/4o; `generateSitrep`) · `ai-extraction.ts` · `synthesis-engine.ts` (Layer-10 CIA) · `debate-engine.ts` (5-agent truth debate) · `foresight-engine.ts` (MC-search) · `kg-engine.ts` (LLM-as-Judge KG) · `revenue-engine.ts` · `autonomous-engine.ts` (also GROK/xAI + GitHub PR) · `governor.ts`
- `visual-engine.ts` — multi-provider images/video, each gated on its own env var: `OPENAI_API_KEY` (DALL-E 3), `GROK_API_KEY`, `KLING_API_KEY`, `RUNWAY_API_KEY`, `SORA_API_KEY`. Returns `null` per-provider when its key is absent.

**Deterministic, no-LLM (always fire; these are what's live in prod):**
- `oracle-engine.ts` (ORACLE-9 Bayesian log-odds threat model) · `compass-engine.ts` (COMPASS macro cascade) · `herald-engine.ts` (HERALD-3 IO/disinfo keyword scoring) · `news-fetcher.ts` (RSS aggregation + credibility tiers) · `neural-map.ts` (circuit-breaker health) · `war-stats.ts` · `conflict-day.ts`

**Other env needed:** `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (DB — clearly live given real rows), `CRON_SECRET` (scheduled heartbeats).

`lib/openai-safe.ts` is a genuine hardened wrapper: `sk-` key validation, secret redaction in logs, timeout/abort, `response_format: json_object`, returns `null` on any failure so the pipeline never hard-fails — it falls back to the deterministic models above.

## 3. Product engines — executed for real

- **HFF Runway** (`products/hff-runway`, Node/exceljs): `generateRunwayPacket` on `sample_transactions.csv` → `validation.ok=true`, 25 txns/0 rejected, real cashflow + tax worksheet, **valid XLSX (`PK`, 13,912 B) and PDF (`%PDF-`, 1,896 B)**. Advice-linter fail-closed guard in pipeline.
- **HFF Invoice-Aging** (`products/hff-invoice-aging`, Node/exceljs): `generateAgingReport` on `sample_invoices.csv` → `validation.ok=true`, 7 outstanding / $19,200, aging buckets correct (90+d = $14,500×3), **valid XLSX (`PK`, 10,324 B) and PDF (`%PDF-`, 2,278 B)**.
- **HRF Clarity-Briefs** (`products/hrf-clarity-briefs`, Python): citation-coverage linter (`engine/linter.py`) — **12/12 unittests pass** including the moat (`test_catches_uncited_claim`, `test_catches_fabricated_quote` anti-fabrication verbatim grounding, `test_engine_raises_on_uncited_claim` → 422 fail-closed). CLI end-to-end on `examples/request.sample.json` emitted a **`coverage=100%`** brief in md/html/json.

## 4. Content correctness

- **Banner (live):** correct — `LIVE OSINT FEED + MODELED SIMULATION — CHECK EACH PANEL'S LABEL`. This matches the AUDIT_02 recommended fix and replaces the old over-broad "NOT REAL-TIME" that falsely disclaimed the genuinely-live feed/newsroom/intel panels.
- **Staleness note:** the staged `audits/epic-fury-src` tree still carries the OLD banner at `app/page.tsx:96`; it is a pre-fix snapshot and does not reflect production. If that tree is ever redeployed, the banner regression would return.
- **Percentage clamp:** in place and pervasive — no path can emit >100% (see table 4c).

---

## Honest caveats
1. The audit could not read Vercel env vars directly; `aiAvailable:false` from the live digest is the authoritative signal that the LLM key is unset in prod.
2. Engine verification used the products' own sample inputs; real customer CSV variety is not exercised here.
3. Clarity-Briefs linter is the deterministic floor (verbatim quote-grounding); semantic "does the quote support the claim" is an LLM council pass documented as a future integration point, not yet wired.
