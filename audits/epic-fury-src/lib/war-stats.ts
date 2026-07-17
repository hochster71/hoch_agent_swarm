/**
 * war-stats.ts — MODELED PROJECTIONS. NOT OBSERVATIONS. NOT REPORTING.
 *
 * ⚠ READ THIS BEFORE YOU USE ANYTHING IN THIS FILE ⚠
 *
 * Every number here is EXTRAPOLATED FROM A DAY COUNTER. Nothing in this file observes
 * the real world. There is no feed, no source, no verification. `brentUsd` is a slope.
 * `compassCeasefire` is `1.4 * day`, capped at 95. `hormuzFullyOpen` is `day >= 44`.
 *
 * THE HARM THIS CAUSED
 * --------------------
 * On 13 JUL 2026 this model told the public, on a page headed "LIVE REAL-TIME ANALYSIS"
 * and "Trusted data for every American citizen — just the facts":
 *
 *     ALL THEATERS SILENT · HORMUZ 100% OPEN · CEASEFIRE 95% · FPCON NORMAL
 *
 * On that same day, the actual ceasefire had disintegrated, the US was reinstating a
 * blockade of the Strait of Hormuz, a second round of strikes had been completed, and
 * transits through the strait were down 52%.
 *
 * The model did not lag reality. It INVERTED it — and it will keep inverting it, more
 * confidently every day, because the formulas only know what day it is.
 *
 * THE RULE
 * --------
 * These values may be used ONLY on surfaces explicitly labelled SIMULATED or MODELED
 * (see lib/data-provenance.ts). They may NEVER appear on the public landing page, in
 * site metadata, or anywhere a reader could mistake them for current reporting.
 * scripts/verify-no-fabricated-claims.mjs enforces this at build time.
 *
 * If you want these numbers to be true, wire them to a real source. Until then they are
 * a model, and a model that is presented as fact is a lie with a spreadsheet attached.
 *
 * Formula sources:
 *  - Sorties: 300/day D10-D43 (CDG surge D27+); ISR-only 60/day post-ceasefire D43+
 *  - ZB-Alpha: MCM operations 2%/day post D24, capped at 100 from D44
 *  - Brent: peaks $123 D17, declines ~$2.20/day on ceasefire progress, floor $68
 *  - BM stock: ORACLE-9 model, erodes ~2%/day post D17, floor 2%
 *  - Ceasefire COMPASS: 1.4pp/day post D24, capped at 95
 *  - FPCON: DELTA -> CHARLIE (D28) -> BRAVO (D36) -> ALPHA (D44) -> NORMAL (D55)
 */

import { getConflictDay } from './conflict-day'

export interface WarStats {
  day: number
  /** Total coalition combat/ISR sorties since Day 1 */
  totalSorties: number
  /** Formatted sortie count, e.g. "13,200+" */
  sortiesLabel: string
  /** ZB-Alpha Hormuz MCM corridor clearance % */
  zbAlphaPct: number
  /** Brent crude USD/bbl (model floor $68 post-Hormuz recovery) */
  brentUsd: number
  /** Iran remaining BM inventory as % of pre-conflict (floor 2%) */
  bmStockPct: number
  /** COMPASS ceasefire probability % within 72h */
  compassCeasefire: number
  /** Iran nuclear infrastructure degradation % (fixed post D25) */
  nuclearDegradedPct: number
  /** THAAD/PATRIOT intercept rate % */
  tbmdInterceptPct: number
  /** Days since last IRGCAF sortie */
  daysSinceIRGCAFSortie: number | null
  /** Ceasefire trial is active — all offensive operations paused (D43+) */
  ceasefireActive: boolean
  /** Strait of Hormuz fully open — ZB-Alpha 100% cleared, unrestricted commercial transit (D44+) */
  hormuzFullyOpen: boolean
  /** IAEA inspectors have regained access to Natanz FEP (D41+) */
  iaeaAccessGranted: boolean
  /** IAEA inspectors have entered Fordow FEP — IR-2m/IR-6 cascades verified inoperative (D45+) */
  fordowAccessGranted: boolean
  /** Phase IV armistice framework negotiations underway in Abu Dhabi (D55+) */
  armisticeActive: boolean
  /** Current FPCON level: DELTA -> CHARLIE (D28) -> BRAVO (D36) -> ALPHA (D44) -> NORMAL (D55) */
  fpconLevel: 'DELTA' | 'CHARLIE' | 'BRAVO' | 'ALPHA' | 'NORMAL'
}

export function getWarStats(day?: number): WarStats {
  const d = day ?? getConflictDay()

  // Sortie model: pre-D10 ramp (200/day), D10-D24 sustained (350/day),
  // D24-D27 deceleration (250/day), D27-D43 CDG surge (280/day),
  // D43+ ceasefire: ISR/recon only ~60/day
  const SORTIES_AT_D43 = 2000 + 14 * 350 + 3 * 250 + 16 * 280 // 12,130
  let totalSorties: number
  if (d <= 10) {
    totalSorties = d * 200
  } else if (d <= 24) {
    totalSorties = 2000 + (d - 10) * 350
  } else if (d <= 27) {
    totalSorties = 2000 + 14 * 350 + (d - 24) * 250
  } else if (d <= 43) {
    // CDG Rafale M adds ~30 sorties/day from D27
    totalSorties = 2000 + 14 * 350 + 3 * 250 + (d - 27) * 280
  } else {
    // Ceasefire active D43+: ISR and strategic recon only ~60/day
    totalSorties = SORTIES_AT_D43 + (d - 43) * 60
  }

  // ZB-Alpha MCM clearance: started D24 at 60%.
  // D33: 84%, D40: 96%, D42: 99%, D44: 100% complete.
  // Rate ~2.17%/day. Hard-caps at 100 from D44 onward.
  const zbAlphaPct = d >= 44
    ? 100
    : Math.min(99, Math.max(0, d < 24 ? 0 : 60 + (d - 24) * 2.17))

  // Brent crude: peaks $123 D17, secondary elevation D28 barrage ($116), then:
  //   D28-D36: rapid ceasefire-progress decline to $84 (-4/day)
  //   D36-D44: plateau near Hormuz clearance $84->$82 (-0.25/day)
  //   D44+: post-Hormuz acceleration to floor $68 (-0.56/day)
  //   Key: D36=$84, D41=$82, D44=$82, D51=$78, D53=$77, D61=$72
  const brentUsd: number = d < 17
    ? Math.round(74 + (d / 17) * (123 - 74))
    : d < 28
    ? Math.round(123 - (d - 17) * 0.6)
    : d < 36
    ? Math.round(116 - (d - 28) * 4.0)
    : d < 44
    ? Math.round(84 - (d - 36) * 0.25)
    : Math.max(68, Math.round(82 - (d - 44) * 0.56))

  // Iran BM stock: 6 barrages fired through D52; CRITICAL depletion
  const bmStockPct = Math.max(2, Math.round(28 - Math.max(0, d - 17) * 1.8))

  // COMPASS ceasefire probability: ramps post D24 at ~1.4pp/day
  // Day 53 = 71% (Abu Dhabi Phase III binding clauses active)
  const compassCeasefire = Math.min(95, Math.max(10, 30 + Math.max(0, d - 24) * 1.4))

  // Nuclear degradation: assessed 94% at D25, fixed thereafter
  const nuclearDegradedPct = d >= 25 ? 94 : Math.min(94, Math.round(d * 3.5))

  // TBMD intercept rate: PAC-3 + THAAD, degrades slightly as inventory thins
  const tbmdInterceptPct = Math.max(75, Math.round(90 - Math.max(0, d - 20) * 0.3))

  // IRGCAF last sortie was D21 (both F-14s destroyed)
  const daysSinceIRGCAFSortie = d >= 21 ? d - 21 : null

  // Ceasefire trial active D43+
  const ceasefireActive = d >= 43

  // Hormuz fully open D44+ (ZB-Alpha MCM mission complete)
  const hormuzFullyOpen = d >= 44

  // IAEA regained access to Natanz FEP D41+
  const iaeaAccessGranted = d >= 41

  // IAEA entered Fordow FEP Day 45 -- IR-2m/IR-6 cascades confirmed inoperative
  const fordowAccessGranted = d >= 45

  // Phase IV armistice framework negotiations opened Abu Dhabi Day 55
  const armisticeActive = d >= 55

  // FPCON: DELTA -> CHARLIE D28 -> BRAVO D36 -> ALPHA D44 -> NORMAL D55
  const fpconLevel: WarStats['fpconLevel'] =
    d >= 55 ? 'NORMAL' :
    d >= 44 ? 'ALPHA' :
    d >= 36 ? 'BRAVO' :
    d >= 28 ? 'CHARLIE' :
    'DELTA'

  return {
    day: d,
    totalSorties,
    sortiesLabel: `${totalSorties.toLocaleString()}+`,
    zbAlphaPct,
    brentUsd,
    bmStockPct,
    compassCeasefire,
    nuclearDegradedPct,
    tbmdInterceptPct,
    daysSinceIRGCAFSortie,
    ceasefireActive,
    hormuzFullyOpen,
    iaeaAccessGranted,
    fordowAccessGranted,
    armisticeActive,
    fpconLevel,
  }
}
