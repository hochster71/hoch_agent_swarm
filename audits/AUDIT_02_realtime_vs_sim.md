# AUDIT 02 — Epic Fury: LIVE vs SIMULATED data map

**Scope:** READ-ONLY. Source: `audits/epic-fury-src` (Next.js App Router). No files modified, nothing deployed.
**Date:** 2026-07-16 · **Standard:** NO FAKE GREEN — findings reflect only what the code shows.

## Bottom line

The founder is right that Epic Fury is a **MIX**, and the codebase already contains a genuinely
good honesty mechanism: `lib/data-provenance.ts` declares a per-page verdict (LIVE / SIMULATED /
MIXED / PLACEHOLDER / UNKNOWN) and `components/ProvenanceBanner.tsx` renders it at the top of
**every** dashboard page via the layout. That system is the right foundation and should be kept.

But two labeling surfaces are currently **inaccurate in opposite directions**, and one of them is a
real consumer-safety hole:

1. **The public homepage banner is falsely "all-not-real-time."** `app/page.tsx:96` prints a blanket
   `UNCLASSIFIED // NOT REAL-TIME // MODELED PROJECTIONS — NOT CURRENT REPORTING` across the whole
   site — yet the same page's own feature cards (lines 42, 50) advertise the Intel Feed as "backed by
   a real ingested data source" and the Newsroom as produced "from ingested sources," and
   `data-provenance.ts` labels `/dashboard/feed`, `/newsroom`, `/intel`, `/oracle`, `/timeline`,
   `/world` as **LIVE**. The banner contradicts the app. This is the "falsely not-real-time" error.

2. **Two LIVE-labeled pages fall back to fabricated scenario content dressed as verified wire
   reporting.** This is the dangerous direction and the top risk (see Section 3).

---

## 1. Panel-by-panel LIVE / SIMULATED / MIXED map

Legend: **Declared** = verdict in `lib/data-provenance.ts`. **Actual** = what the code really does.
✅ declared verdict matches code · ⚠️ mismatch / caveat.

### Declared LIVE

| Route | Actual data source (evidence) | Verdict |
|---|---|---|
| `/dashboard/feed` | Supabase `.from('intel')` (`feed/page.tsx:23-24`), **fed by the real RSS ingest pipeline** (`app/api/ingest/route.ts` pulls Reuters/AP/BBC/USNI/etc. RSS in `lib/news-fetcher.ts:41+` and writes CRITICAL/HIGH rows). **BUT** on empty/failed DB it substitutes `STATIC_INTEL` (`feed/page.tsx:37-39`) — fabricated war events (see §3). | ⚠️ LIVE **only when seeded**; fabricated fallback under a LIVE banner |
| `/dashboard/newsroom` | `fetch('/api/newsroom/generate')` + `fetch('/api/intel/digest')` (live), **plus** `getWarStats()` (modeled) and `buildDayAwareBroadcast()` fallback (`newsroom/page.tsx:8,438-439`). Blends live ingest with modeled war figures. | ⚠️ Really **MIXED**, declared LIVE |
| `/dashboard/intel` | Supabase `.from('intel')` (`intel/page.tsx:438-442`); some hardcoded sample rows w/ `classification: 'TS/SI/NF'` (lines 89,97). | ✅ mostly LIVE |
| `/dashboard/oracle` | `fetch('/api/oracle')` + `/api/intel/calibration` — model inference over live inputs (`oracle/page.tsx:155-156`). | ✅ LIVE (model over live data) |
| `/dashboard/timeline` | Supabase `.from('intel')` + `STATIC_INTEL` fallback (`timeline/page.tsx:1-4,151-152`). | ⚠️ LIVE when seeded; fabricated fallback |
| `/dashboard/world` | Supabase intel headlines feed an AI brief (`world/page.tsx:33-34`), **but** the static fallback (lines 68-95) is **entirely fabricated scenario** — "Iran expelled all IAEA inspectors on Day 8," "DEFCON 3," "340,000+ displaced," VIX 42 — each with real citations (IAEA, SIPRI, CISA, Lloyd's, IMF). `revalidate = 1200`. | ⚠️ Really **MIXED**, declared LIVE; fabricated fallback (see §3) |
| `/dashboard/nexus` | `fetch('/api/intel/stats','/api/platform/status','/api/oracle/enhance','/api/compass',...)` (`nexus/page.tsx:186-191`). Platform telemetry. | ✅ LIVE (admin) |
| `/dashboard/agents` | Supabase auth + roster; **hardcoded reasoning logs contain modeled figures** ("Post-Alpha-5 cascade model… Brent $94/bbl," `agents/page.tsx:286-288`); header brags "live feeds · auto-refresh" (514). | ⚠️ MIXED (admin roster + modeled log text) |
| `/dashboard/revenue` | Supabase auth-gated revenue records (`revenue/page.tsx:22-32`). | ✅ LIVE (admin) |
| `/dashboard/workflows` | Supabase auth + workflow state. | ✅ LIVE (admin) |
| `/dashboard/autonomous` | Supabase auth + autonomous-enhancement state. | ✅ LIVE (admin) |
| `/dashboard/settings` | Supabase connection check / account (`settings/page.tsx`). | ✅ LIVE (admin) |

### Declared SIMULATED (scenario / invented ops — Operation Epic Fury, CONFLICT_DAY, JADC2/DMO)

All of these import `lib/conflict-day.ts` (day counter from a fixed 01 MAR 2026 epoch) and/or
`lib/war-stats.ts` (formula output — see §3 warning), or carry hardcoded scenario arrays.

| Route | Actual data source (evidence) | Verdict |
|---|---|---|
| `/dashboard/homeland` | Hardcoded **real** APT actors marked fake `status: 'ACTIVE'` — `APT33/Holmium`, `APT34/OilRig`, `APT35/Charming Kitten` (`homeland/page.tsx:146-182`) + fabricated federal advisory text (fake `ED 26-01`, `NERC CIP-2026-03`, `FinCEN FIN-2026-A002`, lines 43-88). Embeds a genuinely-live `TheaterIntelFeed` (line ~495). | ✅ correctly SIMULATED (underlying is MIXED; SIMULATED is the safe label) |
| `/dashboard/hva` | Hardcoded high-value-asset target deck. | ✅ SIMULATED |
| `/dashboard/econ` | Scenario premium model; embeds live "economic & energy intel" `TheaterIntelFeed` (`econ/page.tsx:355`); explicit in-page note "Scenario projection prices… NOT real market data" (line 502). Pulls a real spot price via `/api/market/prices` (fetch line 45). | ✅ correctly SIMULATED (body); has a live sub-panel |
| `/dashboard/ceasefire` | Scenario negotiation track, `conflict-day` derived. | ✅ SIMULATED |
| `/dashboard/threats` | Scenario threat board; cites RAND/think-tank links. | ✅ SIMULATED |
| `/dashboard/news` | Scenario wire copy (hardcoded). | ✅ SIMULATED |
| `/dashboard/brief` | Scenario daily brief, `conflict-day` derived. | ✅ SIMULATED |
| `/dashboard/sitrep` | `getWarStats()` modeled figures + `conflict-day` (`sitrep/page.tsx:3-4`). | ✅ SIMULATED |
| `/dashboard/bda` | Supabase `.from('bda_strikes')` (`bda/page.tsx:377`) — live **table**, but rows are simulated engagements; `conflict-day` derived. | ✅ SIMULATED (note self-declares "live store, simulated engagements") |
| `/dashboard/orbat` | Supabase `.from('orbat_updates')` + `getWarStats()` (`orbat/page.tsx:7,602`). | ✅ SIMULATED |
| `/dashboard/cop` | Supabase `.from('scenario_events')` + `.from('intel')` (`cop/page.tsx:169-174`). | ✅ SIMULATED |
| `/dashboard/dmo` | JADC2/DMO canvas sim; `getWarStats()` + `.from('scenario_events')` (`dmo/page.tsx:5,35`). This is the component the founder flagged as simulation. | ✅ SIMULATED |
| `/dashboard/logistics` | Supabase `.from('logistics_events')` + `conflict-day` (`logistics/page.tsx:16,314`). | ✅ SIMULATED |

### Declared MIXED

| Route | Actual | Verdict |
|---|---|---|
| `/dashboard` (hub) | Interleaves live feed items with scenario narrative; note says "Each panel is labelled." | ✅ MIXED |

### Declared PLACEHOLDER (not built / not sold)

| Route | Note | Caveat |
|---|---|---|
| `/dashboard/command` | "Not built yet." | verify it is excluded from the paid tier |
| `/dashboard/debate` | Labeled placeholder, but `debate/page.tsx` has real content/persistence text ("All sessions persisted with full provenance," line 31). | ⚠️ verify: code suggests it is NOT empty |
| `/dashboard/foresight` | "Not built yet." | verify |
| `/dashboard/visuals` | Labeled placeholder, but `visuals/page.tsx:32` describes AI-visual watermarks. | ⚠️ verify: code suggests content exists |

---

## 2. Honesty-label surfaces and their accuracy

| Surface | What it says | Accurate? |
|---|---|---|
| `app/page.tsx:96` top banner | Blanket "NOT REAL-TIME // MODELED PROJECTIONS — NOT CURRENT REPORTING" | ❌ **Inaccurate (too broad).** feed/newsroom/intel/oracle are genuinely live-ingest backed. Contradicts this page's own feature cards. |
| `app/page.tsx:42,50,58,66,74,82` feature cards | Per-feature: Intel Feed "real ingested data source," Homeland/Ceasefire/Econ/SITREP "Modeled / scenario." | ✅ **Accurate and nuanced** — this is the model to follow. |
| `app/page.tsx:12-18` code comment + empty `QUICK_STATS` | Modeled war figures were **removed** from the public landing; build guard `scripts/verify-no-fabricated-claims.mjs` fails if `lib/war-stats` is imported here. | ✅ Good, real guardrail. |
| `app/page.tsx:174-183` breaking strip / `261-265` footer | "MODELED PROJECTION — NOT CURRENT REPORTING" | ⚠️ Same over-broad framing as the top banner. |
| `components/ProvenanceBanner.tsx` + `lib/data-provenance.ts` | Per-page LIVE / SIMULATED / MIXED / PLACEHOLDER / UNVERIFIED, rendered in the layout so no page ships without it. | ✅ **Strong mechanism.** Mostly accurate; misclassifies newsroom & world as LIVE (they're MIXED); does not cover the fabricated-fallback state. |
| `app/terms/page.tsx:43-59` | "EPIC FURY CONTAINS SIMULATED CONTENT… Operation Epic Fury is a fictional conflict scenario… The App also provides live, open-source intelligence… Every dashboard is labelled at the top of the page as LIVE / SIMULATION / MIXED / UNVERIFIED." | ✅ **Accurate and matches the provenance system.** Best-written honesty surface in the app. |
| `lib/war-stats.ts:1-40` header | Self-documents the 13 JUL 2026 incident where a "LIVE REAL-TIME ANALYSIS" header showed inverted reality; mandates SIMULATED-only use. | ✅ Honest internal guardrail. |
| SIMULATED pages' "on-air" badges + "Live feeds" section headers | e.g. red `on-air-badge`, "Live feeds — cyber/homeland intel" (homeland:495, econ:355) | ⚠️ Mildly misleading — "LIVE/ON AIR" chrome on a SIMULATED page. (Some of those sub-panels ARE live `TheaterIntelFeed`, which is why the page is really MIXED.) |

---

## 3. Real risk — where SIMULATED could be mistaken for REAL current intelligence

**RISK 1 (HIGHEST — consumer safety): LIVE-labeled pages show fabricated war content as
"verified" wire reporting when the DB is empty.**
- `lib/static-intel.ts` is invented scenario content — e.g. "Iran's third major ballistic missile
  barrage… **Three US personnel confirmed killed in action; 12 wounded**" — with
  `verified: true`, `source_name: 'Reuters'`, `source_url: reuters.com`, `confidence: 91`.
- `feed/page.tsx` serves this under the header **"Live Intel Feed"** and the ProvenanceBanner
  **LIVE — "Live intel feed from the ingestion pipeline."** The only tell is a small amber
  "STATIC CACHE" chip; the individual cards still read *verified · Reuters · 91%*.
- `world/page.tsx:68-95` does the same: fabricated "IAEA inspectors expelled… DEFCON 3… 340,000+
  displaced" attributed to IAEA/SIPRI/CISA/IMF, under a **LIVE** banner, on a 20-minute cache.
- A reader on an unseeded/degraded deployment sees invented US casualties and nuclear/DEFCON claims
  presented as verified real-wire, current, live intelligence about an **active geopolitical
  conflict**. This is the core misrepresentation hazard.

**RISK 2: Homepage banner is now false in the "not-real-time" direction** (§1/§2). Over-disclaiming
is not harmless here — it trains users to ignore the banner, and it contradicts the paid pitch that
the Intel Feed is live, which undermines the honest per-panel labels.

**RISK 3: Real threat actors carry fabricated "ACTIVE" status and fake federal advisories.**
`/dashboard/homeland` names real APTs (APT33/Holmium, APT34/OilRig, APT35/Charming Kitten) as
`ACTIVE` and prints fabricated DHS/FBI/CISA advisory language with invented directive numbers
(`ED 26-01`, `NERC CIP-2026-03`, `FinCEN FIN-2026-A002`). It **is** correctly SIMULATED-labeled
(good), but the fabricated *official-advisory voice* is a high misrepresentation surface even with
the banner — a screenshot stripped of the banner reads as a genuine federal cyber alert.

**RISK 4: "LIVE / ON AIR" chrome on SIMULATED pages** dilutes the SIMULATED banner (§2 last row).

**RISK 5: PLACEHOLDER pages (debate, visuals) contain real-looking content** in code while declared
"not built" — verify they are truly gated out of the paid tier and render an empty/"not built" state.

---

## 4. Recommended accurate labeling fix

**Do NOT delete honesty labels while modeled data is shown.** Keep the ProvenanceBanner system.
The fix is to make the labels *accurate*, not fewer.

**A. Fix the homepage header (top recommendation).** Replace the blanket
`NOT REAL-TIME // MODELED PROJECTIONS — NOT CURRENT REPORTING` (`app/page.tsx:96`, and the matching
174-183 / 261-265 strips) with a MIXED-accurate line, e.g.:

> `UNCLASSIFIED // MIXED — LIVE OSINT FEED + MODELED SIMULATION · CHECK EACH PANEL'S LABEL`

This tells the truth in both directions: the live feed is live, the scenario is modeled, and the
per-panel banner is authoritative. The existing feature cards (already accurate) stay.

**B. Close the fabricated-fallback hole (the actual safety fix).** When `feed`/`timeline`/`world`
render `STATIC_INTEL` / the `world` static object, they must not present it under a LIVE banner as
`verified · Reuters/IAEA`. Either: (i) switch the ProvenanceBanner for that render to
**SIMULATED — "Demonstration fallback; DB empty. Not live reporting."**, or (ii) strip
`verified: true` and the real source attribution and stamp each fallback card "DEMO / NOT LIVE."
Right now `verified: true` + a real wire name is the load-bearing lie.

**C. Reclassify to MIXED in `data-provenance.ts`:** `/dashboard/newsroom` and `/dashboard/world`
(both blend live ingest with modeled war-stats / fabricated fallback). `/dashboard/agents` is admin
but its modeled log text also argues for MIXED.

**D. Keep SIMULATED (do NOT relabel live):** `dmo` (JADC2/DMO — the component the founder already
calls a simulation), `homeland`, `hva`, `econ`, `ceasefire`, `threats`, `news`, `brief`, `sitrep`,
`bda`, `orbat`, `cop`, `logistics`. These are the invented-ops core (Operation Epic Fury,
CONFLICT_DAY, war-stats formulas) and must stay SIMULATED.

**E. Keep genuinely LIVE:** `feed` (once B is fixed), `intel`, `oracle`, `nexus`, and admin
surfaces — these are backed by the real RSS→Supabase ingest pipeline or platform telemetry.

**F. De-conflict the chrome:** drop or restyle the red "ON AIR" / "Live feeds" badges on SIMULATED
pages, or scope them only to the genuinely-live `TheaterIntelFeed` sub-panels.

**G. Verify PLACEHOLDER truth:** confirm `debate`/`visuals`/`foresight`/`command` are excluded from
`SUBSCRIBER_ROUTES` and render an empty state, matching their "not built" declaration.

---

### One-line top recommendation
Change the homepage banner from the blanket false **"NOT REAL-TIME / MODELED PROJECTIONS"** to a
**MIXED — "live OSINT feed + modeled simulation, check each panel's label"** statement, and in the
same change stop the LIVE-labeled `feed`/`world` pages from serving fabricated `STATIC_INTEL` /
static scenario content as `verified · Reuters/IAEA` — those two edits remove both the
falsely-not-real-time error and the genuine consumer-safety hazard without deleting a single
honesty label.
