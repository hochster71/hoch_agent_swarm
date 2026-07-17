# AUDIT 01 — DATA INTEGRITY (Epic Fury) — Impossible / Wrong Values

**Scope:** Read-only audit of `audits/epic-fury-src` (Next.js `app/`). Focus: percentages / confidence / probability that can exceed 100 or go below 0, out-of-range scores, contradictory counts, fabricated/placeholder values, and unbounded math. Founder flag: *"intelligence-report percentages exceed 100% in the newsroom."*

**Verdict:** Founder's report is CONFIRMED and root-caused. There is a real, systemic **double-scaling** bug: `/api/intel/digest` already converts threat probability to a 0–100 integer, but the **newsroom page and both newsroom AI-script routes multiply it by 100 again**, producing threat probabilities up to ~10,000% (e.g. a 41% threat renders as **"4100%"**, a 6% threat as **"600%"**). Every ORACLE-9 threat percentage surfaced through the newsroom is 100× too large.

Other dashboards (COP, SITREP, Command Center, Oracle panel) handle the scale correctly because they read the correct endpoint — the newsroom is the odd one out. This is not cosmetic: it appears in the on-air teleprompter scripts, the closing summary, AND is fed into the GPT prompt that writes the anchor scripts.

---

## Root cause (the founder's bug)

`app/api/intel/digest/route.ts:170` returns threat probability **pre-scaled to 0–100**:
```ts
topThreats = threats.sort(...).slice(0,5).map(t => ({
  ...,
  probability: Math.round(t.probability * 100),   // oracle 0–1  →  0–100 integer
}))
```
The oracle engine's native `probability` is `0–1` (`lib/oracle-engine.ts:61`, values rounded to 2 dp at lines 629/654/677/699/721).

The newsroom then treats that 0–100 value as if it were still 0–1 and multiplies by 100 **again**.

---

## Findings table

| # | file:line | Defective value / expression | Why it's wrong | Severity | Suggested fix |
|---|-----------|------------------------------|----------------|----------|---------------|
| 1 | `app/dashboard/newsroom/page.tsx:257` | `const pct = (p) => p != null ? \`${Math.round(p * 100)}%\` : '—'` — called at **:278, :283 (×2), :313, :318** on `d.topThreats[i].probability` | `d.topThreats[].probability` from `/api/intel/digest` is **already 0–100** (digest:170). Multiplying by 100 again yields up to ~10,000%. A 41% threat prints **"4100%"**. This is the exact newsroom symptom the founder saw — in anchor scripts, the threat-assessment segment, and the closing summary. | **HIGH** | The digest value is already a percent. Either render `${Math.round(p)}%` in the newsroom, OR change the digest `topThreats` to emit 0–1 like the raw oracle. Whichever, clamp to `Math.max(0, Math.min(100, …))`. Pick ONE convention project-wide. |
| 2 | `app/api/newsroom/generate/route.ts:94` | `digest.topThreats?.slice(0,4).map(t => \`• ${t.label} (${Math.round((t.probability ?? 0) * 100)}%, ${t.severity})\`)` | Same double-scale. `fetchDigest()` (line 64) pulls `/api/intel/digest` whose `probability` is 0–100, then ×100 → "4100%". This string is injected into the GPT-4o prompt, so the AI is *told* the threat is 4100% and can parrot impossible figures into the generated broadcast scripts. | **HIGH** | Drop the `* 100` (value is already a percent); clamp 0–100. |
| 3 | `app/api/newsroom/seed/route.ts:123` | `.map(t => \`• ${t.label}: ${Math.round(t.probability * 100)}% — ${t.severity}\`)` | Same double-scale; `digest` fetched at line 113 from `/api/intel/digest` (0–100). Feeds the seed-generation GPT prompt → impossible percentages baked into cached scripts. | **HIGH** | Drop the `* 100`; clamp 0–100. |
| 4 | `app/api/analyze/route.ts:115` | `confidence: Math.min(95, baseConf + Math.floor(Math.random() * 15))` | Extracted-claim "confidence %" is **randomly jittered per request** — the same headline yields a different confidence each call. Bounded (≤95, ≥40) so not >100, but it is a **fabricated value presented as analysis** in the Live Intel report (rendered `{c.confidence}%` in `LiveNewsBoard.tsx:164`, `TruthReport.tsx:237`). Non-deterministic "intelligence." | **MED** | Derive confidence deterministically from tier + HERALD score + corroboration count; remove `Math.random()`. |
| 5 | `app/dashboard/page.tsx:348` | `sub: \`${stats.count > 0 ? Math.round((stats.verified/stats.count)*100) : 74}% corroborated\`` | Hardcoded **74%** placeholder shown as a live "corroborated" stat whenever there is no data. Fabricated figure indistinguishable from a real metric. | **MED** | Show `—`/`N/A` when `count === 0` instead of an invented 74%. |
| 6 | `components/CompassPanel.tsx:170` | `delta={\`${Math.round((1 - cascade.hormuzThroughputMbpd / 18.9) * 100)}% cut\`}` | No clamp. If `hormuzThroughputMbpd` exceeds the 18.9 baseline, the "cut" goes **negative** (nonsense: a negative % reduction); no floor/ceiling. | **LOW** | `Math.max(0, Math.min(100, …))`. |
| 7 | `app/dashboard/threats/page.tsx` (static `pct` values 67/82/71 + "fourth barrage", Day 22) vs `app/dashboard/newsroom/page.tsx` (Day 27, "fifth and final barrage", ceasefire) | Cross-page contradiction: the Threats board hardcodes a *forecast* of a not-yet-occurred 4th BM barrage on Day 22, while the newsroom/war-stats narrative is Day 27 with 5 barrages already fired and a ceasefire. Counts contradict each other across dashboards. Values themselves are in-range (0–100), but the data set is internally inconsistent/stale. | **LOW** | Drive both from the same live source / conflict-day model; retire the hardcoded scenario block. |

---

## Verified CORRECT (no defect) — checked to bound the bug

These render probability/confidence and were confirmed to use the right scale, so they are NOT part of the bug:

- `components/OraclePanel.tsx:137` `Math.round(t.probability * 100)` — source is `/api/oracle/enhance` which returns **0–1** (`api/oracle/enhance/route.ts:87`). Correct.
- `components/CommandCenterDashboard.tsx:625,634` `t.probability * 100` — source `/api/oracle` returns raw `computeAllThreats` = **0–1** (`api/oracle/route.ts:36,40`). Correct.
- `components/SitrepAutoFeed.tsx:249,258` and `components/LiveSitrepDoc.tsx:271,275` render `{t.probability}%` **without** ×100 — source `/api/intel/digest` is **0–100**. Correct.
- `components/SynthesisPanel.tsx:124,168,267` and `components/ForesightPanel.tsx:62,116,368` `Math.round(confidence * 100)` — synthesis/foresight confidence is **0–1** (`lib/synthesis-engine.ts:159-161`, `lib/foresight-engine.ts:289` clamped `Math.max(0,Math.min(1,…))`). Correct.
- Intel/claim `confidence` from AI extraction is clamped 0–100 via the `int(v,0,100,default)` helper (`lib/ai-extraction.ts:233,276`); `computeVerdict` truthScore clamped `Math.max(0,Math.min(100,…))` (`api/analyze/route.ts:155`); HERALD score `Math.min(100,…)` (`lib/herald-engine.ts:169`). Correct.
- `lib/war-stats.ts` — all percentages (`zbAlphaPct`, `compassCeasefire`, `nuclearDegradedPct`, `tbmdInterceptPct`, `bmStockPct`) are `Math.min/Math.max`-clamped (lines 104,121,124,128,131,134). Correct.
- `components/AccuracyReport.tsx:68` bar width `Math.min(pct,100)%` — clamped. `components/RevenuePanel.tsx:83` `Math.min(100,…)` — clamped.

---

## Bottom line

- **1 HIGH-severity data-integrity defect, triple-instanced** (newsroom page + generate route + seed route) — the confirmed source of the founder's ">100% in the newsroom" report. Fix = remove the redundant `* 100` (and add a 0–100 clamp) at those three sites, since `/api/intel/digest` already emits 0–100.
- **2 MED** (fabricated random confidence; hardcoded 74% placeholder), **2 LOW** (unclamped Hormuz "cut"; stale cross-page barrage contradiction).
- The safest systemic fix is to **standardize one probability convention** (recommend keep oracle's 0–1 end-to-end and scale only at the render layer with a clamp), because the current mix of 0–1 and 0–100 across endpoints is what caused the newsroom to scale twice.
