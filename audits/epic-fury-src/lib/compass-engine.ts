/**
 * COMPASS Economic Cascade Model
 * ─────────────────────────────────────────────────────────────────────────────
 * Deterministic macroeconomic model: given conflict day N and a Hormuz closure
 * severity level, projects energy prices, freight costs, insurance premia,
 * sovereign credit spreads, and CPI impulse.
 *
 * Methodology
 * ───────────
 * 1.  Oil price trajectory  (Hotelling / inventory-depletion model)
 *     P(t) = P₀ + α × (1 – e^(–β×t)) × severity_factor
 *     α = max shock absorption (plateau premium): $82/bbl
 *     β = market learning / hedging rate: 0.045
 *
 * 2.  LNG spot price         (LNG = oil_equivalent × premium_multiplier)
 *     premium_multiplier = 1.32 + 0.008 × t  (rising as substitution demand grows)
 *
 * 3.  Tanker war-risk insurance (Lloyd's H&M schedule)
 *     Lloyd's uses a 4-tier banding: 0.5%–3.5% CIF value per voyage
 *     Rate at day t modeled as exponential approach to 3.5% ceiling.
 *
 * 4.  Cape of Good Hope rerouting impact
 *     18-day voyage extension (ABuDhabi → Rotterdam via Cape vs Suez)
 *     Incremental cost: charter_rate × 18 days × 0.62 (loaded leg fraction)
 *     Charter rates: VLCC spot ~$65k/day in disrupted market
 *
 * 5.  Strait throughput (mb/d)  ~17% of world seaborne oil
 *     At Day 0: 18.9 mb/d reference
 *     Reduction = base × severity × (1 – diversion_rate × t/30)
 *
 * 6.  GCC sovereign risk
 *     UAE/Saudi CDS spread: +12 bps/wk during active hostilities
 *
 * 7.  Oil-to-CPI transmission (Fed / IMF estimate: $10 oil = ~0.2pp CPI)
 */

export type ClosureSeverity = 'PARTIAL' | 'CONTESTED' | 'CLOSED'

export interface EconomicCascade {
  /** Brent crude spot estimate (USD/bbl) */
  brentUsd:              number

  /** WTI discount to Brent (USD/bbl) */
  wtiDiscount:           number

  /** Natural gas / LNG spot (USD/MMBtu equiv.) */
  lngSpotUsd:            number

  /** Strait of Hormuz throughput (mb/d) */
  hormuzThroughputMbpd:  number

  /** Lloyd's war-risk insurance (% CIF value per voyage) */
  lloydWarRiskPct:       number

  /** Cape rerouting incremental cost per VLCC voyage (USD, thousands) */
  capeReroutingCostKusd: number

  /** Est. spot VLCC charter rate (USD/day, thousands) */
  vllcCharterKusd:       number

  /** UAE sovereign CDS spread increase vs pre-conflict (bps) */
  uaeCdsBps:             number

  /** Saudi ARAMCO equity discount vs pre-conflict (%) */
  aramcoDiscountPct:     number

  /** Global CPI impulse — annualised pp above baseline */
  globalCpiImpulsePp:    number

  /** US headline CPI impulse (annualised pp) */
  usCpiImpulsePp:        number

  /** EU/Euro-area CPI impulse (annualised pp — more exposed) */
  euCpiImpulsePp:        number

  /** GCC SWF estimated outflows (USD bn, cumulative) */
  gccSwfOutflowBn:       number

  /** Dollar index (DXY) estimated move from pre-conflict base (pp) */
  dxyMovePp:             number

  /** Model inputs snapshot */
  inputs: {
    conflictDay:      number
    severity:         ClosureSeverity
    oilBaseline:      number
    scenarioLabel:    string
  }

  computedAt: string
}

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------
const OIL_SHOCK_MAX    = 52           // max plateau premium over baseline ($)
                                       // calibrated: Day-36 CONTESTED → Brent ≈ $109 (actual Apr-5-2026)
const OIL_LEARNING_RATE = 0.045       // market hedging / adjustment rate
const LNG_BASE_MULT    = 1.32         // LNG premium vs oil equivalent at Day 0
const VLCC_BASE_RATE   = 65_000       // spot VLCC daily charter rate ($) at conflict baseline
const CAPE_EXTRA_DAYS  = 18           // additional voyage days via Cape
const WTI_BASE_DISCOUNT = 4.20        // WTI pre-conflict discount to Brent; inverts to premium under Hormuz closure
const HORMUZ_BASE_MBPD = 18.9         // reference throughput
const CPI_SENSITIVITY  = 0.022        // pp CPI per $10 oil (global, Fed/IMF mid-estimate)
const CDS_WEEKLY_RISE  = 12           // bps per week during active hostilities

const SEVERITY_FACTORS: Record<ClosureSeverity, number> = {
  PARTIAL:    0.45,
  CONTESTED:  0.75,
  CLOSED:     1.00,
}

const THROUGHPUT_REDUCTION: Record<ClosureSeverity, number> = {
  PARTIAL:   0.30,
  CONTESTED: 0.60,
  CLOSED:    0.90,
}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------
export function computeEconomicCascade(
  conflictDay:   number,
  severity:      ClosureSeverity = 'CONTESTED',
  oilBaseline:   number          = 78,   // pre-conflict Brent ($/bbl)
): EconomicCascade {
  const sf    = SEVERITY_FACTORS[severity]
  const t     = Math.max(1, conflictDay)
  const weeks = t / 7

  // 1. Oil price
  const oilPremium   = OIL_SHOCK_MAX * (1 - Math.exp(-OIL_LEARNING_RATE * t)) * sf
  const brentUsd     = Math.round((oilBaseline + oilPremium) * 10) / 10

  // WTI inverts to a premium over Brent when Hormuz is contested: US Gulf supply
  // becomes safe-haven vs Middle East Brent, and US shale ramp adds domestic supply.
  // PARTIAL(sf=0.45): +$0.15 Brent premium; CONTESTED(sf=0.75): −$2.55 (WTI+$2.55); CLOSED: −$4.80
  const wtiDiscount  = Math.round((WTI_BASE_DISCOUNT - sf * 9) * 10) / 10

  // 2. LNG
  const oilEq        = brentUsd / 5.8    // rough barrel-to-MMBtu
  const lngMult      = LNG_BASE_MULT + 0.008 * t * sf
  const lngSpotUsd   = Math.round(oilEq * lngMult * 10) / 10

  // 3. Hormuz throughput
  const reductionFraction = THROUGHPUT_REDUCTION[severity] *
                            (1 - 0.12 * Math.min(1, t / 30))  // slow diversion ramp
  const hormuzThroughput  = Math.round((HORMUZ_BASE_MBPD * (1 - reductionFraction)) * 10) / 10

  // 4. Lloyd's war-risk insurance (approach to 3.5% ceiling)
  const lloydMax     = 3.5
  const lloydBase    = 0.5
  const lloydRate    = lloydBase + (lloydMax - lloydBase) * (1 - Math.exp(-0.08 * t * sf))
  const lloydWarRisk = Math.round(lloydRate * 100) / 100

  // 5. Cape rerouting cost
  const vllcDailyRate = VLCC_BASE_RATE * (1 + sf * 0.45 * Math.log1p(t / 7))
  const capeCost_kusd = Math.round((vllcDailyRate * CAPE_EXTRA_DAYS * 0.62) / 1000)

  // 6. UAE CDS spread
  const uaeCds       = Math.round(CDS_WEEKLY_RISE * weeks * sf)

  // 7. Aramco discount (equity risk)
  const aramcoDisc   = Math.round(Math.min(35, sf * 18 * Math.log1p(t / 10)) * 10) / 10

  // 8. CPI impulse
  const oilDelta     = brentUsd - oilBaseline
  const globalCpi    = Math.round((oilDelta / 10) * CPI_SENSITIVITY * 100 * 10) / 10
  const usCpi        = Math.round(globalCpi * 0.75 * 10) / 10   // US less exposed
  const euCpi        = Math.round(globalCpi * 1.35 * 10) / 10   // EU more exposed

  // 9. GCC SWF outflows (precautionary / defensive rebalancing)
  const gccSwf       = Math.round(sf * 3.8 * weeks * 10) / 10   // $bn cumulative

  // 10. DXY demand spike (flight-to-safety)
  const dxy          = Math.round(sf * 0.4 * Math.log1p(t) * 10) / 10

  const scenarioLabel = {
    PARTIAL:    'Partial interruption — contested passage, naval escorts',
    CONTESTED:  'Active contested closure — MCM + mining + FAC harassment',
    CLOSED:     'Full closure — effective naval blockade by IRGCN',
  }[severity]

  return {
    brentUsd,
    wtiDiscount,
    lngSpotUsd,
    hormuzThroughputMbpd: hormuzThroughput,
    lloydWarRiskPct:      lloydWarRisk,
    capeReroutingCostKusd: capeCost_kusd,
    vllcCharterKusd:      Math.round(vllcDailyRate / 1000),
    uaeCdsBps:            uaeCds,
    aramcoDiscountPct:    aramcoDisc,
    globalCpiImpulsePp:   globalCpi,
    usCpiImpulsePp:       usCpi,
    euCpiImpulsePp:       euCpi,
    gccSwfOutflowBn:      gccSwf,
    dxyMovePp:            dxy,
    inputs: {
      conflictDay:   t,
      severity,
      oilBaseline,
      scenarioLabel,
    },
    computedAt: new Date().toISOString(),
  }
}
