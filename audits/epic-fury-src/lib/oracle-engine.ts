/**
 * ORACLE-9 Threat Probability Engine
 * ─────────────────────────────────────────────────────────────────────────────
 * Pure-TypeScript multi-domain threat probability estimator.
 *
 * Algorithm
 * ─────────
 * 1.  Bayesian log-odds fusion
 *     Each intelligence signal carries a likelihood ratio (LR) derived from
 *     empirical conflict-intelligence correlations.  The posterior log-odds
 *     are computed as:
 *
 *         logit(p_post) = logit(p_prior) + Σ log(LR_i)  for active signals
 *         p_post        = sigmoid(logit(p_post))
 *
 * 2.  Time-based Poisson hazard model (for periodic threats only)
 *     Inter-event intervals for Iranian ballistic-missile barrages:
 *     [D1, D4, D8, D13, D17] → intervals [3, 4, 5, 4, 5] days
 *     λ = 1 / mean(intervals) ≈ 0.238 events/day
 *     P(event in 72h window) = 1 – exp(–λ × 3)
 *
 * 3.  Fusion
 *     P_final = 1 – (1 – P_bayes) × (1 – P_hazard)
 *     (i.e. "at least one of the two models says YES")
 *
 * 4.  Confidence interval — Wilson score at 90% for final p
 *
 * Usage: import and call `computeAllThreats()` from a server route.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type ThreatSeverity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'MINIMAL'
export type SignalDomain   = 'SIGINT' | 'IMINT' | 'HUMINT' | 'OSINT' | 'GEOINT' | 'CYBER' | 'ECONINT' | 'DIPLOMATIC'

export interface OracleSignal {
  id:          string
  domain:      SignalDomain
  description: string
  /** Likelihood ratio: how much more likely if threat is real */
  lr:          number
  /** Is this signal currently active/observed? */
  active:      boolean
  /** Optional counter-signal (LR < 1 weakens threat) */
  counter?:    boolean
  /**
   * Keywords for dynamic signal resolution from Supabase intel.
   * If ANY keyword found in recent intel text, active = true (or for
   * counter signals = true means the counter fires, weakening the threat).
   */
  keywords?:   string[]
}

export interface OracleThreat {
  id:              string
  label:           string
  domain:          string
  prior:           number          // base-rate probability per window
  windowHours:     number          // time window for this probability
  probability:     number          // final fused probability 0–1
  bayesP:          number          // Bayesian only
  hazardP?:        number          // time-hazard only (periodic threats)
  ciLow:           number          // 90% CI lower bound
  ciHigh:          number          // 90% CI upper bound
  severity:        ThreatSeverity
  trend:           'UP' | 'DOWN' | 'STABLE'
  trendDeltaPp:    number          // percentage-point change vs 24h ago
  activeSignals:   OracleSignal[]
  topSignal:       string          // highest-LR active signal description
  lastModel:       string          // ISO timestamp of last model run
}

// ---------------------------------------------------------------------------
// Math helpers
// ---------------------------------------------------------------------------
function logit(p: number): number {
  const clamped = Math.max(0.001, Math.min(0.999, p))
  return Math.log(clamped / (1 - clamped))
}

function sigmoid(x: number): number {
  return 1 / (1 + Math.exp(-x))
}

/** Wilson score confidence interval at z-level (z=1.645 → 90%) */
function wilsonCI(p: number, n = 100, z = 1.645): [number, number] {
  const denom = 1 + z * z / n
  const centre = (p + z * z / (2 * n)) / denom
  const margin = (z / denom) * Math.sqrt((p * (1 - p)) / n + z * z / (4 * n * n))
  return [Math.max(0, centre - margin), Math.min(1, centre + margin)]
}

/** Poisson hazard: P(≥1 event) in windowDays given rate λ (events/day) */
function poissonHazard(lambdaPerDay: number, windowDays: number): number {
  return 1 - Math.exp(-lambdaPerDay * windowDays)
}

/** Combine two independent probability estimates */
function fuseProbabilities(p1: number, p2: number): number {
  return 1 - (1 - p1) * (1 - p2)
}

function bayesianUpdate(prior: number, signals: OracleSignal[]): number {
  let logOdds = logit(prior)
  for (const s of signals) {
    if (s.active) {
      const lr = s.counter ? (1 / Math.max(0.01, s.lr)) : s.lr
      logOdds += Math.log(Math.max(0.01, lr))
    }
  }
  return sigmoid(logOdds)
}

function getSeverity(p: number): ThreatSeverity {
  if (p >= 0.75) return 'CRITICAL'
  if (p >= 0.55) return 'HIGH'
  if (p >= 0.35) return 'MODERATE'
  if (p >= 0.15) return 'LOW'
  return 'MINIMAL'
}

// ---------------------------------------------------------------------------
// Signal definitions
// ---------------------------------------------------------------------------

/** 6th ballistic missile barrage risk (Al Udeid / Arifjan / Bahrain) */
const BM_SIGNALS: OracleSignal[] = [
  {
    id:          'bm-sigint-hf',
    domain:      'SIGINT',
    description: 'HF authentication burst on IRGCAF launch-authorization frequency (11.5 MHz) — TRIDENT intercept',
    lr:          5.5,
    active:      false,  // default OFF — activated by day-conditional logic or live intel keywords
  },
  {
    id:          'bm-imint-tel',
    domain:      'IMINT',
    description: 'ATLAS-1: 6–8 Emad/Ghadr TELs in dispersed deployment posture / ZULU-14 reconstituting — NRO + Maxar WV-3',
    lr:          4.2,
    active:      false,
    keywords:    ['tel', 'transporter erector', 'emad', 'ghadr', 'tel deployment', 'nro', 'maxar', 'ballistic missile launcher', 'zulu-14'],
  },
  {
    id:          'bm-imint-thermal',
    domain:      'IMINT',
    description: 'ATLAS-1 thermal: TEL engine-start signature — pre-launch warm-up profile',
    lr:          6.8,
    active:      false,
    keywords:    ['thermal signature', 'engine-start', 'pre-launch warm', 'convoy zulu', 'tel engine'],
  },
  {
    id:          'bm-sigint-sl',
    domain:      'SIGINT',
    description: 'TRIDENT: Salami → IRGC CINC secure circuit — traffic class matches pre-strike auth pattern',
    lr:          8.2,
    active:      false,  // Khamenei KIA D22 — Salami command net monitored D27+
    keywords:    ['salami command', 'irgc cinc', 'secure circuit', 'launch authorization', 'flash traffic'],
  },
  {
    id:          'bm-humint-fuel',
    domain:      'HUMINT',
    description: 'HUMINT: Fuel and oxidiser trucks at launch site — corroborated DIA source',
    lr:          3.5,
    active:      false,
    keywords:    ['fuel truck', 'oxidiser', 'bijar', 'site f-7', 'launch propellant', 'zulu-14 fuel'],
  },
  {
    id:          'bm-osint-runway',
    domain:      'OSINT',
    description: 'Al Udeid AB and Camp Arifjan runway/pad operational — credible barrage target',
    lr:          1.8,
    active:      false,
    keywords:    ['al udeid', 'runway', 'arifjan', 'dhahran', 'al dhafra', 'runway operational'],
  },
  {
    id:          'bm-geoint-underground',
    domain:      'GEOINT',
    description: 'ZULU-14 complex: SAR-confirmed vehicle activity near tunnel exit — reconstitution indicators',
    lr:          3.2,
    active:      false,
    keywords:    ['tunnel exit', 'zagros', 'vehicle congregation', 'sar corroboration', 'hardened shelter', 'zulu-14'],
  },
  {
    id:          'bm-counter-48h',
    domain:      'SIGINT',
    // LR > 1 so that 1/LR < 1 → log(1/LR) < 0 → properly REDUCES log-odds when counter fires
    description: 'No confirmed IRGCAF launch-authorization order in 48h quiet window — weakens probability',
    lr:          3.5,
    active:      false,
    counter:     true,
    keywords:    ['no launch order', 'quiet window', 'irgcaf stand-down'],
  },
  {
    id:          'bm-counter-ceasefire',
    domain:      'DIPLOMATIC',
    description: 'Abu Dhabi Ceasefire Framework active (D27) — POTUS announcement + UNSCR 2731 D25 — diplomatic track strongly suppresses barrage authorization probability',
    lr:          6.0,   // 1/6.0 = 0.167 → log = −1.79 (strong reduction)
    active:      false,
    counter:     true,
    keywords:    ['ceasefire', 'abu dhabi framework', 'unscr 2731', 'diplomatic talks', 'proximity talks', 'ceasefire framework', 'de-escalation'],
  },
]

/** Shahed-136/238 drone swarm (mass UAV attack) */
const SHAHED_SIGNALS: OracleSignal[] = [
  {
    id:          'sh-imint-prearm',
    domain:      'IMINT',
    description: 'NRO/Commercial SAR: pre-arm activity Qeshm Island depot — airframes confirmed on hardstand',
    lr:          7.1,
    active:      false,
    keywords:    ['qeshm', 'depot', 'airframe', 'pre-arm', 'hardstand', 'shahed', 'drone staging'],
  },
  {
    id:          'sh-imint-fuel',
    domain:      'IMINT',
    description: 'Bandar Abbas forward staging: fuel bowser activity consistent with Shahed preparation',
    lr:          4.8,
    active:      false,
    keywords:    ['bandar abbas', 'fuel bowser', 'shahed prep', 'drone fuel staging'],
  },
  {
    id:          'sh-sigint-grid',
    domain:      'SIGINT',
    description: 'CERBERUS: IRGCAF/IRGCN grid update transmissions — drone launch net monitoring active',
    lr:          3.6,
    active:      false,
    keywords:    ['cerberus', 'irgcn', 'grid update', 'drone grid', 'qeshm logistics', 'shahed grid'],
  },
  {
    id:          'sh-osint-adsb',
    domain:      'OSINT',
    description: 'Qeshm IFR zone closure / ADS-B gap — launch corridor suppression indicator',
    lr:          2.4,
    active:      false,
    keywords:    ['qeshm ifr', 'adsb gap', 'airspace closed', 'launch corridor suppression'],
  },
  {
    id:          'sh-humint-crew',
    domain:      'HUMINT',
    description: 'Shahed launch crew pre-positioned east coast Hormuzgan province',
    lr:          3.9,
    active:      false,
    keywords:    ['shahed crew', 'launch crew', 'hormuzgan', 'drone crew', 'uav launch team'],
  },
  {
    id:          'sh-counter-ciws',
    domain:      'SIGINT',
    // LR > 1 → 1/LR < 1 → properly reduces log-odds when CIWS-ready counter fires
    description: 'CTF CIWS batteries at full readiness + successful intercept rate — reduces Shahed attack utility',
    lr:          2.5,
    active:      false,
    counter:     true,
    keywords:    ['ciws', 'drone intercept', 'shoot down', 'air defense success', 'drone downed', 'swarm defeated'],
  },
  {
    id:          'sh-counter-ceasefire',
    domain:      'DIPLOMATIC',
    description: 'Ceasefire framework and Abu Dhabi diplomatic track active — reduces IRGCAF launch authorization probability',
    lr:          4.5,   // 1/4.5 = 0.222 → log = −1.50 (strong reduction)
    active:      false,
    counter:     true,
    keywords:    ['ceasefire', 'diplomatic talks', 'abu dhabi', 'de-escalation', 'unscr 2731'],
  },
]

/** IRGCN surface swarm (FAC / missile boat attack on USN group) */
const IRGCN_SIGNALS: OracleSignal[] = [
  {
    id:          'irgcn-imint-fac',
    domain:      'IMINT',
    description: 'Bandar Abbas naval base: FAC/missile-boat readiness indicators — IRGCN dispersed posture maintained',
    lr:          4.4,
    active:      false,
    keywords:    ['fast attack', 'fac', 'missile boat', 'bandar abbas naval', 'ascm loaded', 'irgcn sortie'],
  },
  {
    id:          'irgcn-sigint-order',
    domain:      'SIGINT',
    description: 'IRGCN command-to-flotilla enciphered transmission — mission-type-indicator matches patrol-attack profile',
    lr:          5.2,
    active:      false,
    keywords:    ['irgcn command', 'flotilla', 'patrol attack', 'naval order', 'irgcn transmission'],
  },
  {
    id:          'irgcn-imint-kilo',
    domain:      'IMINT',
    description: 'GOLF-8 Kilo SSK unlocated — EMCON since D17, last observed Bandar-e-Jask; possible ZB-Bravo mine-lay risk',
    lr:          3.8,
    active:      false,
    keywords:    ['kilo submarine', 'ssb', 'mine lay', 'mcm', 'golf-7', 'golf-8', 'mine belt', 'bandar-e-jask'],
  },
  {
    id:          'irgcn-counter-daylight',
    domain:      'OSINT',
    description: 'Daylight ops: IRGCN historically prefers night swarms — reduces 12h probability',
    lr:          2.0,   // fixed: was 0.7, now > 1 so 1/2.0 = 0.5 → log = −0.69 (reduces when active)
    active:      false,
    counter:     true,
  },
  {
    id:          'irgcn-counter-ceasefire',
    domain:      'DIPLOMATIC',
    description: 'Abu Dhabi ceasefire framework + UNSCR 2731 — diplomatic track reduces IRGCN offensive sortie authorization',
    lr:          4.0,   // 1/4.0 = 0.25 → log = −1.39 (strong reduction when ceasefire active)
    active:      false,
    counter:     true,
    keywords:    ['ceasefire', 'diplomatic', 'abu dhabi', 'de-escalation', 'unscr 2731'],
  },
  {
    id:          'irgcn-counter-mcm',
    domain:      'OSINT',
    description: 'MCM ZB-Alpha 78%+ cleared — 7 VLCCs transited D24-D27; mine-threat effect reduced by corridor clearance progress',
    lr:          2.5,   // 1/2.5 = 0.40 → log = −0.92 (moderate reduction)
    active:      false,
    counter:     true,
    keywords:    ['mcm corridor', 'zb-alpha cleared', 'vlcc transit', 'mine cleared', 'hormuz transit', 'mcm sweep'],
  },
]

/** Hezbollah second front (Lebanon → Israel + US assets) */
const HZB_SIGNALS: OracleSignal[] = [
  {
    id:          'hzb-humint-radwan',
    domain:      'HUMINT',
    description: 'Radwan Force (~2,500 elite) elevated readiness — assembly at Bekaa staging areas',
    lr:          3.1,
    active:      false,
    keywords:    ['radwan force', 'hezbollah radwan', 'bekaa staging', 'hezbollah readiness', 'radwan unit'],
  },
  {
    id:          'hzb-imint-pgm',
    domain:      'IMINT',
    // LR > 1 → properly reduces probability when IAF degradation counter fires
    description: 'IAF Bekaa strikes D14 degraded PGM stock est. 3,000–5,000 guided missiles — reduces Hezbollah attack utility',
    lr:          2.5,
    active:      false,
    counter:     true,
    keywords:    ['bekaa strike', 'hezbollah pgm', 'iaf bekaa', 'guided missile stock degraded'],
  },
  {
    id:          'hzb-sigint-quds',
    domain:      'SIGINT',
    // LR > 1 → properly reduces probability when no-Quds-auth counter fires
    description: 'No IRGC Quds Force threshold authorization detected — political brake on Hezbollah escalation',
    lr:          3.0,
    active:      false,
    counter:     true,
    keywords:    ['quds ceasefire', 'hezbollah ceasefire', 'no quds auth', 'political brake'],
  },
  {
    id:          'hzb-osint-rocketfire',
    domain:      'OSINT',
    description: 'Cross-border Kornet/rocket fire ongoing — low-level harassment maintained',
    lr:          1.4,
    active:      false,
    keywords:    ['hezbollah rocket', 'kornet', 'cross-border fire', 'northern israel', 'rocket salvo', 'hezbollah attack'],
  },
]

/** Iranian nuclear escalation (breakout / dirty weapon use) */
const NUCLEAR_SIGNALS: OracleSignal[] = [
  {
    id:          'nuc-iaea-offline',
    domain:      'GEOINT',
    description: 'IAEA monitoring offline since Day 5 — no continuity of knowledge at Fordow, Natanz',
    lr:          2.1,
    active:      false,
    keywords:    ['iaea', 'monitoring offline', 'enrichment', 'fordow', 'continuity of knowledge'],
  },
  {
    id:          'nuc-specter-fordow',
    domain:      'IMINT',
    // LR > 1 → properly reduces probability when Fordow-degraded counter fires
    description: 'SPECTER: Fordow shaft 2-Alpha collapsed, 3-Alpha damaged — above-ground enrichment heavily disrupted',
    lr:          3.5,
    active:      false,
    counter:     true,
    keywords:    ['fordow destroyed', 'shaft collapsed', 'fordow degraded', 'specter strike', 'natanz destroyed'],
  },
  {
    id:          'nuc-argus-1alpha',
    domain:      'IMINT',
    description: 'Shaft 1-Alpha and 2-Beta status uncertain — NRO SAR tasking active; underground reconstitution possible',
    lr:          1.9,
    active:      false,
    keywords:    ['shaft 1-alpha', 'cloud cover natanz', 'nuclear reconstitution', 'underground nuclear', 'argus-1'],
  },
  {
    id:          'nuc-sigint-regime',
    domain:      'SIGINT',
    // LR > 1 → properly reduces probability when deterrence-threshold-not-crossed counter fires
    description: 'No command traffic matching nuclear-authorization pattern — deterrence threshold not crossed',
    lr:          4.0,
    active:      false,
    counter:     true,
    keywords:    ['no nuclear auth', 'nuclear ceasefire', 'nuclear talks', 'deterrence threshold'],
  },
]

// ---------------------------------------------------------------------------
// Hazard parameters (Poisson) — day-aware
// ---------------------------------------------------------------------------
// BM Barrage intervals (days): D1→D4=3, D4→D8=4, D8→D13=5, D13→D17=4, D17→D22=5, D22→D26=4
// Post-Alpha-5 (D26+): ZULU-14 reconstitution phase — estimated 8-10 day inter-event interval
function getBMLambda(day: number): number {
  if (day >= 27) return 1 / 9    // ZULU-14 reconstituting post-Alpha-5 D26
  if (day >= 23) return 1 / 4.5  // succession vacuum – slightly elevated interval uncertainty
  return 1 / 4.2                  // historical average D1-D22
}

// Shahed swarm intervals: D8, D14, D16, D22 → mean ~4.7 days
// Post-D26: stocks ~380-460 remaining; IRGCAF in reduced readiness (ceasefire track)
function getShahedLambda(day: number): number {
  if (day >= 26) return 1 / 4.5  // depleted stocks + ceasefire framework
  return 1 / 3.5                  // historical average
}

// ---------------------------------------------------------------------------
// Day-indexed 24h-ago baselines — autonomous trend calculation
// Reflects what the model would have output on (conflictDay - 1)
// ---------------------------------------------------------------------------
const PREV_24H_TABLE: Array<{ fromDay: number; values: Record<string, number> }> = [
  { fromDay: 28, values: { 'bm-barrage': 0.64, 'shahed-swarm': 0.72, 'irgcn-swarm': 0.45, 'hzb-front': 0.25, 'nuclear': 0.26 } },
  { fromDay: 27, values: { 'bm-barrage': 0.76, 'shahed-swarm': 0.80, 'irgcn-swarm': 0.55, 'hzb-front': 0.30, 'nuclear': 0.28 } },
  { fromDay: 26, values: { 'bm-barrage': 0.82, 'shahed-swarm': 0.86, 'irgcn-swarm': 0.65, 'hzb-front': 0.36, 'nuclear': 0.30 } },
  { fromDay: 25, values: { 'bm-barrage': 0.88, 'shahed-swarm': 0.92, 'irgcn-swarm': 0.72, 'hzb-front': 0.40, 'nuclear': 0.30 } },
  { fromDay: 23, values: { 'bm-barrage': 0.85, 'shahed-swarm': 0.90, 'irgcn-swarm': 0.70, 'hzb-front': 0.42, 'nuclear': 0.28 } },
  { fromDay: 20, values: { 'bm-barrage': 0.67, 'shahed-swarm': 0.82, 'irgcn-swarm': 0.65, 'hzb-front': 0.40, 'nuclear': 0.20 } },
]

function getPrev24H(day: number): Record<string, number> {
  for (const entry of PREV_24H_TABLE) {
    if (day >= entry.fromDay) return entry.values
  }
  return PREV_24H_TABLE[PREV_24H_TABLE.length - 1].values
}

// ---------------------------------------------------------------------------
// Day-conditional signal activation — autonomous healing layer
// As CONFLICT_DAY advances, signal active defaults auto-calibrate.
// Live Supabase intel (resolveSignalsFromIntel) can override these at runtime.
// ---------------------------------------------------------------------------
function getActiveBMSignalIds(day: number): Set<string> {
  if (day <= 22) {
    // Pre-Alpha-4 to Khamenei KIA: maximum barrage indicators hot
    return new Set(['bm-sigint-hf', 'bm-imint-tel', 'bm-imint-thermal', 'bm-humint-fuel', 'bm-osint-runway', 'bm-geoint-underground'])
  } else if (day <= 25) {
    // D23-D25: succession vacuum, pre-ceasefire conditions
    return new Set(['bm-imint-tel', 'bm-imint-thermal', 'bm-humint-fuel', 'bm-osint-runway', 'bm-geoint-underground'])
  } else {
    // D26+: Alpha-5 expended, ZULU-14 reconstituting, ceasefire Abu Dhabi track D27
    return new Set(['bm-imint-tel', 'bm-osint-runway', 'bm-geoint-underground', 'bm-counter-48h', 'bm-counter-ceasefire'])
  }
}

function getActiveShahedSignalIds(day: number): Set<string> {
  if (day <= 21) {
    // Pre-Alpha-3: all indicators hot
    return new Set(['sh-imint-prearm', 'sh-imint-fuel', 'sh-sigint-grid', 'sh-osint-adsb', 'sh-humint-crew'])
  } else if (day <= 25) {
    // D22-D25: post-swarm replenishment + succession vacuum
    return new Set(['sh-imint-fuel', 'sh-sigint-grid', 'sh-humint-crew'])
  } else {
    // D26+: ceasefire track, stocks significantly depleted, CIWS operational
    return new Set(['sh-sigint-grid', 'sh-counter-ceasefire'])
  }
}

function getActiveIRGCNSignalIds(day: number): Set<string> {
  if (day <= 24) {
    // D1-D24: active IRGCN posture, GOLF-7 threat
    return new Set(['irgcn-imint-fac', 'irgcn-sigint-order', 'irgcn-imint-kilo'])
  } else {
    // D25+: GOLF-7 INACTIVE D26, ceasefire track, MCM progress
    return new Set(['irgcn-imint-fac', 'irgcn-imint-kilo', 'irgcn-counter-ceasefire', 'irgcn-counter-mcm'])
  }
}

function getActiveHZBSignalIds(day: number): Set<string> {
  if (day <= 22) {
    return new Set(['hzb-humint-radwan', 'hzb-osint-rocketfire', 'hzb-sigint-quds'])
  } else {
    // Ceasefire track reduces Hezbollah authorization pressure but Radwan still elevated
    return new Set(['hzb-humint-radwan', 'hzb-osint-rocketfire', 'hzb-imint-pgm', 'hzb-sigint-quds'])
  }
}

function getActiveNuclearSignalIds(day: number): Set<string> {
  if (day <= 21) {
    return new Set(['nuc-iaea-offline', 'nuc-specter-fordow', 'nuc-argus-1alpha', 'nuc-sigint-regime'])
  } else if (day <= 24) {
    // D22-D24: Khamenei KIA / succession vacuum — nuc-sigint-regime unreliable (no constitutional SL)
    return new Set(['nuc-iaea-offline', 'nuc-specter-fordow', 'nuc-argus-1alpha'])
  } else {
    // D25+: some succession resolution, Abu Dhabi track — modest nuclear counter signals back
    return new Set(['nuc-iaea-offline', 'nuc-specter-fordow', 'nuc-argus-1alpha', 'nuc-sigint-regime'])
  }
}

/** Apply day-conditional active defaults to a signal array, then resolve from live intel */
function applyDayActivation(
  signals:      OracleSignal[],
  activeIds:    Set<string>,
  recentText:   string,
): OracleSignal[] {
  const withDefaults = signals.map(s => ({ ...s, active: activeIds.has(s.id) }))
  return resolveSignalsFromIntel(recentText, withDefaults)
}

// ---------------------------------------------------------------------------
// Day-parameterised prior probabilities
// ---------------------------------------------------------------------------
function getBMPrior(day: number): number {
  if (day >= 26) return 0.15  // stocks ~92-95% expended post-Alpha-5
  if (day >= 22) return 0.20
  return 0.20
}

function getShahedPrior(day: number): number {
  if (day >= 26) return 0.20  // ~380-460 remaining; high burn-rate dampened by ceasefire
  return 0.30
}

function getIRGCNPrior(day: number): number {
  if (day >= 26) return 0.20  // GOLF-7 INACTIVE, MCM progress
  return 0.25
}

function getNuclearPrior(day: number): number {
  if (day >= 22) return 0.10  // elevated post-Khamenei KIA succession vacuum
  return 0.04
}

// ---------------------------------------------------------------------------
// Keyword patterns for dynamic signal resolution from live Supabase intel
// When any keyword matches in recent intel text, the signal becomes active.
// Counter signals: active = true when keywords present (fires the counter, weakening probability).
// ---------------------------------------------------------------------------
const SIGNAL_KEYWORDS: Record<string, string[]> = {
  // Ballistic Missile signals
  'bm-sigint-hf':          ['launch authorization', 'irgcaf', 'authentication burst', 'hf frequency', 'pre-launch auth'],
  'bm-imint-tel':          ['tel', 'transporter erector', 'emad', 'ghadr', 'tel deployment', 'nro', 'maxar', 'ballistic missile launcher'],
  'bm-imint-thermal':      ['thermal signature', 'engine-start', 'pre-launch warm', 'convoy bijar', 'tel engine'],
  'bm-sigint-sl':          ['supreme leader', 'irgc cinc', 'secure circuit', 'salami command', 'launch authorization'],
  'bm-humint-fuel':        ['fuel truck', 'oxidiser', 'bijar', 'site f-7', 'launch propellant'],
  'bm-osint-runway':       ['al udeid', 'runway', 'arifjan', 'dhahran', 'al dhafra', 'runway operational'],
  'bm-geoint-underground': ['tunnel exit', 'zagros', 'vehicle congregation', 'sar corroboration', 'hardened shelter'],
  'bm-counter-48h':        ['ceasefire', 'diplomatic', 'negotiations pause', 'de-escalation', 'talks resumed'],
  // Shahed drone signals
  'sh-imint-prearm':       ['qeshm', 'depot', 'airframe', 'pre-arm', 'hardstand', 'shahed', 'drone staging'],
  'sh-imint-fuel':         ['bandar abbas', 'fuel bowser', 'shahed prep', 'drone fuel staging'],
  'sh-sigint-grid':        ['cerberus', 'irgcn', 'grid update', 'drone grid', 'qeshm logistics'],
  'sh-osint-adsb':         ['qeshm ifr', 'adsb gap', 'airspace closed', 'launch corridor suppression'],
  'sh-humint-crew':        ['shahed crew', 'launch crew', 'hormuzgan', 'drone crew', 'uav launch team'],
  'sh-counter-ciws':       ['ciws', 'drone intercept', 'shoot down', 'air defense success', 'drone downed', 'swarm defeated'],
  // IRGCN surface swarm signals
  'irgcn-imint-fac':       ['fast attack', 'fac', 'missile boat', 'bandar abbas naval', 'ascm loaded', 'irgcn sortie'],
  'irgcn-sigint-order':    ['irgcn command', 'flotilla', 'patrol attack', 'naval order', 'irgcn transmission'],
  'irgcn-imint-kilo':      ['kilo submarine', 'ssb', 'mine lay', 'mcm', 'golf-7', 'golf-8', 'mine belt'],
  'irgcn-counter-daylight': ['daylight patrol', 'morning', 'dawn', 'visible conditions'],
  // Hezbollah signals
  'hzb-humint-radwan':     ['radwan force', 'hezbollah radwan', 'bekaa staging', 'hezbollah readiness', 'radwan unit'],
  'hzb-imint-pgm':         ['bekaa strike', 'hezbollah pgm', 'iaf bekaa', 'guided missile stock degraded'],
  'hzb-sigint-quds':       ['quds ceasefire', 'hezbollah ceasefire', 'no quds auth', 'political brake'],
  'hzb-osint-rocketfire':  ['hezbollah rocket', 'kornet', 'cross-border fire', 'northern israel', 'rocket salvo', 'hezbollah attack'],
  // Nuclear signals
  'nuc-iaea-offline':      ['iaea', 'monitoring offline', 'enrichment', 'fordow', 'continuity of knowledge'],
  'nuc-specter-fordow':    ['fordow destroyed', 'shaft collapsed', 'fordow degraded', 'specter strike'],
  'nuc-argus-1alpha':      ['shaft 1-alpha', 'cloud cover natanz', 'nuclear reconstitution', 'underground nuclear', 'argus-1'],
  'nuc-sigint-regime':     ['no nuclear auth', 'nuclear ceasefire', 'nuclear talks', 'deterrence threshold'],
}

/**
 * Resolve signal active states from recent Supabase intel text.
 * Pure function — no I/O. Called with the text of recent intel rows concatenated.
 * Falls back to hardcoded defaults when recentText is absent or too short.
 */
function resolveSignalsFromIntel(
  recentText: string,
  signals: OracleSignal[],
): OracleSignal[] {
  if (!recentText || recentText.length < 20) return signals  // no data — keep defaults
  const lower = recentText.toLowerCase()
  return signals.map(signal => {
    const kws = SIGNAL_KEYWORDS[signal.id]
    if (!kws || kws.length === 0) return signal  // no keywords — keep hardcoded
    const matched = kws.some(kw => lower.includes(kw.toLowerCase()))
    return { ...signal, active: matched }
  })
}

// ---------------------------------------------------------------------------
// Main engine — fully day-aware, autonomous healing
// ---------------------------------------------------------------------------
export function computeAllThreats(conflictDay: number, recentIntelText?: string): OracleThreat[] {
  const now    = new Date().toISOString()
  const prev   = getPrev24H(conflictDay)
  const intel  = recentIntelText ?? ''

  // ── Day-conditional signal activation (autonomous healing layer) + live intel override ──
  const bmSignals     = applyDayActivation(BM_SIGNALS,     getActiveBMSignalIds(conflictDay),     intel)
  const shahedSignals = applyDayActivation(SHAHED_SIGNALS, getActiveShahedSignalIds(conflictDay), intel)
  const irgcnSignals  = applyDayActivation(IRGCN_SIGNALS,  getActiveIRGCNSignalIds(conflictDay),  intel)
  const hzbSignals    = applyDayActivation(HZB_SIGNALS,    getActiveHZBSignalIds(conflictDay),    intel)
  const nucSignals    = applyDayActivation(NUCLEAR_SIGNALS, getActiveNuclearSignalIds(conflictDay), intel)

  // ── Day-aware parameters ─────────────────────────────────────────────────
  const bmLambda     = getBMLambda(conflictDay)
  const shahedLambda = getShahedLambda(conflictDay)
  const bmPrior      = getBMPrior(conflictDay)
  const shPrior      = getShahedPrior(conflictDay)
  const iPrior       = getIRGCNPrior(conflictDay)
  const nucPrior     = getNuclearPrior(conflictDay)

  // ── Ballistic Missile 6th Barrage Risk ──────────────────────────────────────────
  const bmBayes    = bayesianUpdate(bmPrior, bmSignals)
  const bmHazard   = poissonHazard(bmLambda, 3)   // 72-hour window
  const bmFinal    = fuseProbabilities(bmBayes, bmHazard)
  const [bmLo, bmHi] = wilsonCI(bmFinal)

  const bm: OracleThreat = {
    id:            'bm-barrage',
    label:         '6th Ballistic Missile Barrage Risk',
    domain:        'Strategic Missiles',
    prior:         bmPrior,
    windowHours:   72,
    probability:   Math.round(bmFinal * 100) / 100,
    bayesP:        Math.round(bmBayes * 100) / 100,
    hazardP:       Math.round(bmHazard * 100) / 100,
    ciLow:         Math.round(bmLo * 100) / 100,
    ciHigh:        Math.round(bmHi * 100) / 100,
    severity:      getSeverity(bmFinal),
    trend:         bmFinal > prev['bm-barrage'] ? 'UP' : 'DOWN',
    trendDeltaPp:  Math.round((bmFinal - prev['bm-barrage']) * 100),
    activeSignals: bmSignals.filter(s => s.active && !s.counter),
    topSignal:     bmSignals.filter(s => s.active && !s.counter).sort((a, b) => b.lr - a.lr)[0]?.description ?? '',
    lastModel:     now,
  }

  // ── Shahed Swarm ───────────────────────────────────────────────────────────
  const shBayes    = bayesianUpdate(shPrior, shahedSignals)
  const shHazard   = poissonHazard(shahedLambda, 1)   // 24-hour window
  const shFinal    = fuseProbabilities(shBayes, shHazard)
  const [shLo, shHi] = wilsonCI(shFinal)

  const shahed: OracleThreat = {
    id:            'shahed-swarm',
    label:         'Shahed-136/238 Swarm Attack',
    domain:        'Air / UAS',
    prior:         shPrior,
    windowHours:   24,
    probability:   Math.round(shFinal * 100) / 100,
    bayesP:        Math.round(shBayes * 100) / 100,
    hazardP:       Math.round(shHazard * 100) / 100,
    ciLow:         Math.round(shLo * 100) / 100,
    ciHigh:        Math.round(shHi * 100) / 100,
    severity:      getSeverity(shFinal),
    trend:         shFinal > prev['shahed-swarm'] ? 'UP' : 'DOWN',
    trendDeltaPp:  Math.round((shFinal - prev['shahed-swarm']) * 100),
    activeSignals: shahedSignals.filter(s => s.active && !s.counter),
    topSignal:     shahedSignals.filter(s => s.active && !s.counter).sort((a, b) => b.lr - a.lr)[0]?.description ?? '',
    lastModel:     now,
  }

  // ── IRGCN Surface Swarm ────────────────────────────────────────────────────
  const iFinal     = bayesianUpdate(iPrior, irgcnSignals)
  const [iLo, iHi] = wilsonCI(iFinal)

  const irgcn: OracleThreat = {
    id:            'irgcn-swarm',
    label:         'IRGCN FAC Swarm / ASCM Strike',
    domain:        'Maritime',
    prior:         iPrior,
    windowHours:   48,
    probability:   Math.round(iFinal * 100) / 100,
    bayesP:        Math.round(iFinal * 100) / 100,
    ciLow:         Math.round(iLo * 100) / 100,
    ciHigh:        Math.round(iHi * 100) / 100,
    severity:      getSeverity(iFinal),
    trend:         iFinal > prev['irgcn-swarm'] ? 'UP' : 'STABLE',
    trendDeltaPp:  Math.round((iFinal - prev['irgcn-swarm']) * 100),
    activeSignals: irgcnSignals.filter(s => s.active && !s.counter),
    topSignal:     irgcnSignals.filter(s => s.active && !s.counter).sort((a, b) => b.lr - a.lr)[0]?.description ?? '',
    lastModel:     now,
  }

  // ── Hezbollah Second Front ─────────────────────────────────────────────────
  const hFinal     = bayesianUpdate(0.12, hzbSignals)
  const [hLo, hHi] = wilsonCI(hFinal)

  const hzb: OracleThreat = {
    id:            'hzb-front',
    label:         'Hezbollah Second Front',
    domain:        'Proxy / Regional',
    prior:         0.12,
    windowHours:   72,
    probability:   Math.round(hFinal * 100) / 100,
    bayesP:        Math.round(hFinal * 100) / 100,
    ciLow:         Math.round(hLo * 100) / 100,
    ciHigh:        Math.round(hHi * 100) / 100,
    severity:      getSeverity(hFinal),
    trend:         hFinal > prev['hzb-front'] ? 'UP' : 'STABLE',
    trendDeltaPp:  Math.round((hFinal - prev['hzb-front']) * 100),
    activeSignals: hzbSignals.filter(s => s.active && !s.counter),
    topSignal:     hzbSignals.filter(s => s.active && !s.counter).sort((a, b) => b.lr - a.lr)[0]?.description ?? '',
    lastModel:     now,
  }

  // ── Nuclear Escalation ─────────────────────────────────────────────────────
  const nFinal     = bayesianUpdate(nucPrior, nucSignals)
  const [nLo, nHi] = wilsonCI(nFinal)

  const nuclear: OracleThreat = {
    id:            'nuclear',
    label:         'Iranian Nuclear Escalation',
    domain:        'CBRN / Strategic',
    prior:         nucPrior,
    windowHours:   168,
    probability:   Math.round(nFinal * 100) / 100,
    bayesP:        Math.round(nFinal * 100) / 100,
    ciLow:         Math.round(nLo * 100) / 100,
    ciHigh:        Math.round(nHi * 100) / 100,
    severity:      getSeverity(nFinal),
    trend:         'STABLE',
    trendDeltaPp:  0,
    activeSignals: nucSignals.filter(s => s.active && !s.counter),
    topSignal:     'IAEA monitoring offline since Day 5 — continuity of knowledge lost at Fordow',
    lastModel:     now,
  }

  void conflictDay  // used by caller for context, not needed in pure math
  return [bm, shahed, irgcn, hzb, nuclear]
}
