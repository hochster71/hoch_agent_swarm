/**
 * HERALD-3 Information Operations / Disinformation Scoring Engine
 * ─────────────────────────────────────────────────────────────────────────────
 * Scores each news headline 0–100 for disinformation / IO manipulation risk.
 *
 * Algorithm
 * ─────────
 * For each headline compute a weighted keyword hit-score across 8 IO-risk
 * pattern categories.  Each category contributes to the final D-score.
 *
 *   D-raw  = Σ (category_weight × category_hit_score)
 *   D-norm = min(100, D-raw × scaling_factor)
 *
 * Additionally, two meta-signals amplify the score:
 *   • Source-domain credibility penalty (state media, known IO outlets)
 *   • Cross-source uniqueness penalty (claim appears only in single source)
 *
 * Risk bands
 * ──────────
 *   ≥ 75  CRITICAL — high-confidence IO artifact  (RED)
 *   ≥ 55  HIGH     — strong IO indicators          (ORANGE)
 *   ≥ 35  MODERATE — notable manipulation risk     (YELLOW)
 *   ≥ 15  LOW      — minor suspicious indicators   (BLUE)
 *    < 15  CLEAN   — no major IO indicators         (GREEN)
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type HeraldRisk = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'CLEAN'

export type IOCategory =
  | 'STATE_MEDIA'
  | 'CASUALTY_INFLATION'
  | 'NUCLEAR_THREAT_NARRATIVE'
  | 'CEASEFIRE_FABRICATION'
  | 'COMMAND_RECOVERY_NARRATIVE'
  | 'VICTIM_NARRATIVE'
  | 'AMPLIFICATION_VECTOR'
  | 'ECONOMIC_PANIC_NARRATIVE'

export interface HeraldFlag {
  category:    IOCategory
  matched:     string      // which keyword/phrase triggered this
  weight:      number
  description: string
}

export interface HeraldScore {
  score:       number       // 0–100
  risk:        HeraldRisk
  flags:       HeraldFlag[]
  categories:  IOCategory[]
  sourcePenalty: number     // 0–30 added because of source domain
  uniqueness:  boolean      // true → claim only in 1 source (suspicious)
}

// ---------------------------------------------------------------------------
// Pattern library
// ---------------------------------------------------------------------------
interface IOPattern {
  pattern:     RegExp
  weight:      number
  category:    IOCategory
  description: string
}

const IO_PATTERNS: IOPattern[] = [
  // STATE_MEDIA indicators
  { pattern: /\b(press\s*tv|irna|fars\s*news|tasnim|khamenei\.ir|mehr\s*news|irib)\b/i,                          weight: 25, category: 'STATE_MEDIA',                  description: 'Iranian state / quasi-state media source' },
  { pattern: /\b(rt\.com|sputnik|tass|xinhua|cctv)\b/i,                                                          weight: 18, category: 'AMPLIFICATION_VECTOR',          description: 'Known disinformation-amplification outlet' },
  { pattern: /\b(according\s+to\s+(?:iranian|tehran)\s+(?:tv|media|state))\b/i,                                   weight: 22, category: 'STATE_MEDIA',                  description: 'Sourced exclusively from Iranian state media' },

  // CASUALTY_INFLATION
  { pattern: /\b(\d{3,}(?:,\d{3})*\s*(?:civilians?|innocents?)\s*(?:killed|dead|murdered|slaughtered))\b/i,       weight: 30, category: 'CASUALTY_INFLATION',           description: 'Very large civilian casualty figure claimed' },
  { pattern: /\b(mass\s*(?:casualt|death|killing|murder))/i,                                                      weight: 20, category: 'CASUALTY_INFLATION',           description: 'Mass-casualty framing without attribution' },
  { pattern: /\b(hospital(s)?\s+(?:bombed|destroyed|razed|targeting))\b/i,                                        weight: 22, category: 'CASUALTY_INFLATION',           description: 'Hospital targeting claim — common IO template' },
  { pattern: /\b(genocide|ethnic\s+cleansing|war\s+crime)\b/i,                                                    weight: 15, category: 'CASUALTY_INFLATION',           description: 'Escalatory framing; unverified attribution' },

  // NUCLEAR_THREAT_NARRATIVE
  { pattern: /\b(nuclear\s+(?:countdown|ultimatum|threshold|option|warhead|device|capability))\b/i,               weight: 28, category: 'NUCLEAR_THREAT_NARRATIVE',     description: 'Nuclear threat/option narrative without credible sourcing' },
  { pattern: /\b(iran(?:ian)?\s+(?:has|possesses?|tests?|deploys?)\s+nuclear)\b/i,                               weight: 35, category: 'NUCLEAR_THREAT_NARRATIVE',     description: 'Claim of Iranian nuclear acquisition/test' },
  { pattern: /\b(radiological|dirty\s+bomb|EMP\s+attack)\b/i,                                                     weight: 22, category: 'NUCLEAR_THREAT_NARRATIVE',     description: 'CBRN escalation narrative' },

  // CEASEFIRE_FABRICATION
  { pattern: /\b(ceasefire|cease[\s-]fire)\s+(?:agreed|signed|reached|announced|imminent|confirmed)\b/i,          weight: 32, category: 'CEASEFIRE_FABRICATION',        description: 'Ceasefire claimed — currently unconfirmed by official channels' },
  { pattern: /\b(truce|armistice)\s+(?:reached|declared|agreed|in\s+effect)\b/i,                                  weight: 28, category: 'CEASEFIRE_FABRICATION',        description: 'Truce/armistice claim — fabrication risk high during active combat' },
  { pattern: /\b(us\s+(?:withdrawing|pulling\s+out|retreating))\b/i,                                              weight: 20, category: 'CEASEFIRE_FABRICATION',        description: 'Premature US withdrawal narrative' },

  // COMMAND_RECOVERY_NARRATIVE
  { pattern: /\b(irgc\s+(?:reconstituted|rebuilt|reactivated|still\s+operational|fully\s+operational))\b/i,       weight: 30, category: 'COMMAND_RECOVERY_NARRATIVE',  description: 'IRGC command recovery claim — contradicts ORBAT intel' },
  { pattern: /\b(khamenei|supreme\s+leader)\s+(?:addresses?|appeared?|gives?|delivers?)\b/i,                     weight: 18, category: 'COMMAND_RECOVERY_NARRATIVE',  description: 'SL public appearance — verify authenticity / deepfake risk' },
  { pattern: /\b(iran(?:ian)?\s+(?:military|irgc|armed\s+forces)\s+(?:confident|winning|prevailing))\b/i,        weight: 22, category: 'COMMAND_RECOVERY_NARRATIVE',  description: 'Iranian military confidence narrative — IO template' },

  // VICTIM_NARRATIVE
  { pattern: /\b(us\s+(?:kills?|struck|destroyed|targeted))\s+(?:civilians?|children|school|mosque|market)\b/i,  weight: 28, category: 'VICTIM_NARRATIVE',             description: 'US targeting civilians claim' },
  { pattern: /\b(white\s+phosphorus|cluster\s+munitions?)\b/i,                                                    weight: 20, category: 'VICTIM_NARRATIVE',             description: 'Prohibited-weapon framing — historically inflated during conflicts' },
  { pattern: /\b(famine|starvation|water\s+(?:cut|shortage|crisis)\s+in\s+iran)\b/i,                             weight: 15, category: 'VICTIM_NARRATIVE',             description: 'Humanitarian victim narrative amplification' },

  // AMPLIFICATION_VECTOR
  { pattern: /\b(sources?\s+(?:tell|told|say|says)\s+(?:us|me))\b/i,                                              weight: 12, category: 'AMPLIFICATION_VECTOR',          description: 'Vague unattributed sourcing — common IO signal' },
  { pattern: /\b((?:breaking|urgent|exclusive)[\s:]+.*(?:attack|strike|killed|bomb))\b/i,                        weight: 8,  category: 'AMPLIFICATION_VECTOR',          description: 'Breaking/urgent framing with violence — maximises virality' },
  { pattern: /\b(telegram|t\.me|posted\s+(?:on|to)\s+社交媒体)\b/i,                                              weight: 14, category: 'AMPLIFICATION_VECTOR',          description: 'Telegram/closed-channel sourcing — reduced verifiability' },

  // ECONOMIC_PANIC_NARRATIVE
  { pattern: /\b(oil\s+(?:price\s+)?(?:crash|collapse|spike|\$\d{3}|\$200|\$300))\b/i,                           weight: 15, category: 'ECONOMIC_PANIC_NARRATIVE',     description: 'Hyperbolic oil price prediction' },
  { pattern: /\b(global\s+(?:meltdown|collapse|recession|depression)\s+(?:imminent|looming))\b/i,                 weight: 18, category: 'ECONOMIC_PANIC_NARRATIVE',     description: 'Economic apocalypse framing' },
  { pattern: /\b(bank\s+(?:collapse|run|crisis)\s+(?:linked|due)\s+to\s+(?:iran|war))\b/i,                       weight: 20, category: 'ECONOMIC_PANIC_NARRATIVE',     description: 'War-linked banking crisis claim' },
]

// Domains mapped to credibility penalty scores
const SOURCE_PENALTY: Record<string, number> = {
  'presstv.ir':      30,
  'irna.ir':         30,
  'tasnimnews.com':  28,
  'mehrnews.com':    28,
  'farsnews.agency': 28,
  'rt.com':          25,
  'sputniknews.com': 25,
  'tass.ru':         18,
  'almayadeen.net':  15,
}

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------
function getDomainPenalty(url: string): number {
  try {
    const domain = new URL(url).hostname.replace(/^www\./, '')
    return SOURCE_PENALTY[domain] ?? 0
  } catch {
    return 0
  }
}

function getRisk(score: number): HeraldRisk {
  if (score >= 75) return 'CRITICAL'
  if (score >= 55) return 'HIGH'
  if (score >= 35) return 'MODERATE'
  if (score >= 15) return 'LOW'
  return 'CLEAN'
}

export function scoreHeadline(
  title:  string,
  url:    string = '',
  body:   string = '',
): HeraldScore {
  const text    = `${title} ${body}`.toLowerCase()
  const flags:  HeraldFlag[] = []
  let   rawScore = 0

  for (const p of IO_PATTERNS) {
    const m = text.match(p.pattern)
    if (m) {
      flags.push({
        category:    p.category,
        matched:     m[0].trim().substring(0, 60),
        weight:      p.weight,
        description: p.description,
      })
      rawScore += p.weight
    }
  }

  const sourcePenalty = getDomainPenalty(url)
  rawScore += sourcePenalty

  const score      = Math.min(100, Math.round(rawScore))
  const categories = [...new Set(flags.map(f => f.category))]

  return {
    score,
    risk:          getRisk(score),
    flags,
    categories,
    sourcePenalty,
    uniqueness:    false,   // set to true by caller if claim appears in only 1 feed
  }
}

// ── Conflict-relevance filter ──────────────────────────────────────────────
// Captures legitimate war-related headlines from credible sources that score
// LOW/CLEAN on the IO scale (because they are real journalism, NOT disinfo).
const CONFLICT_TERMS = /\b(iran(?:ian)?|tehran|irgc|quds|hormuz|persian\s+gulf|missile[s]?|ballistic|hezbollah|houthi[s]?|airstrike[s]?|air\s+strike|drone\s+strike|sanction(?:s|ed)?|centcom|nuclear|enrichment|natanz|fordow|pentagon|middle\s+east|shahed|carrier\s+(?:group|strike)|us\s+(?:military|forces?|navy|troops?)|naval\s+(?:blockade|fleet|operation)|cease[\s-]?fire|escalat|retaliat|proxy\s+(?:war|force|militia)|yemen|red\s+sea|gaza|beirut|syria[n]?|iraq[i]?|warship|destroyer|submarine|oil\s+(?:tanker|embargo|blockade|supply|output|production|market|price)|energy\s+crisis|brent\s+crude|strait|idf|mossad|cia|joint\s+chiefs|defense\s+secretary|war\s+(?:cabinet|room|plan)|military\s+(?:operation|offensive|strike)|weapon[s]?\s+(?:system|shipment|transfer)|iron\s+dome|patriot|thaad|aegis|f[\s-]?35|b[\s-]?2|tomahawk|bunker\s+buster|fifth\s+fleet|al\s+udeid|jdam|gbu[\s-]\d+|b-52|b-1b|ac-130|mq-9|ea-18g|f-15|kharg|bandar.?abbas|chabahar|qeshm|abu\s+musa|basij|shahab|zalzal|arash|s-300|s-400|bavar.?373|pantsir|tor\s+m|kh-101|precision\s+(?:strike|munition|guided|bomb)|strategic\s+(?:strike|bombing|attack)|close\s+air\s+support|kinetic\s+(?:strike|action)|hypersonic|cruise\s+missile|sea\s+mine|limpet\s+mine|tanker\s+(?:war|attack|seizure)|shipping\s+lane|strait\s+closure|naval\s+blockade|succession\s+crisis|supreme\s+leader|khamenei|salami|ghaani|uranium|breakout|mashhad|zahedan|isfahan|arak|parchin|esfahan|natanz|pmf|popular\s+mobilization|kataib|fatimiyoun|zaynabiyoun|bahrain|al\s+tanf|deir\s+ez\s+zor|fifth\s+fleet|gulf\s+state|saudi\s+arabia|bahrain|kuwait|jordan|oman\s+mediat|qatar\s+(?:base|usaf)|us\s+(?:carrier|strike\s+group|expeditionary)|carrier\s+strike\s+group|nato\s+(?:warn|condemn|alert|response)|stars\s+and\s+stripes|operation\s+epic\s+fury|theater\s+missile\s+defense|glide\s+bomb|loitering\s+munition|suicide\s+drone)\b/i

/** Returns true if the headline relates to the US–Iran / Middle East conflict theater */
export function isConflictRelevant(text: string): boolean {
  return CONFLICT_TERMS.test(text)
}

/** Score an array of headlines; also detect single-source claims and apply uniqueness penalty */
export function scoreHeadlines(items: Array<{ title: string; url: string; source: string; body?: string }>): Array<{
  title:   string
  url:     string
  source:  string
  herald:  HeraldScore
}> {
  // First pass: title → score
  const scored = items.map(item => ({
    ...item,
    herald: scoreHeadline(item.title, item.url, item.body ?? ''),
  }))

  // Second pass: uniqueness penalty — title words shared by < 2 sources?
  // Simplified version: same domain = non-unique; if only one scored HIGH+ we flag
  const highRisk = scored.filter(s => s.herald.score >= 35)
  const sourceCounts: Record<string, number> = {}
  for (const item of highRisk) {
    const words = item.title.toLowerCase().split(/\s+/).slice(0, 5).join(' ')
    sourceCounts[words] = (sourceCounts[words] ?? 0) + 1
  }
  for (const item of scored) {
    const words = item.title.toLowerCase().split(/\s+/).slice(0, 5).join(' ')
    if ((sourceCounts[words] ?? 0) <= 1 && item.herald.score >= 35) {
      item.herald.uniqueness = true
      item.herald.score      = Math.min(100, item.herald.score + 8)
    }
  }

  return scored.sort((a, b) => b.herald.score - a.herald.score)
}
