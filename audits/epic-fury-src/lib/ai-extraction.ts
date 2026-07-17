/**
 * lib/ai-extraction.ts — NEXUS AI Extraction Pipeline
 *
 * Five GPT-4o-mini functions that convert raw ingested intel rows into
 * structured operational data, written to Supabase tables:
 *
 *   extractScenarioEvents  → scenario_events   (COP / DMO / ticker)
 *   extractBdaStrikes      → bda_strikes        (BDA page)
 *   extractOrbatUpdates    → orbat_updates      (ORBAT page overlay)
 *   extractLogisticsEvents → logistics_events   (Logistics page)
 *   generateIntelReports   → intel_reports      (Intel page SIGINT/HUMINT/IMINT)
 *
 * Security:
 *  - All inputs truncated to prevent prompt injection via hostile news
 *  - JSON mode enforced on all GPT calls
 *  - Output validated and sanitised before return
 *  - Returns [] silently without OPENAI_API_KEY (graceful degradation)
 */

import { getConflictDay } from '@/lib/conflict-day'
import { safeOpenAIChatCompletion } from '@/lib/openai-safe'

export const AI_AVAILABLE = !!process.env.OPENAI_API_KEY

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function getSystemContext(): string {
  const EPOCH = Date.UTC(2026, 2, 1)
  const day = Math.max(1, Math.floor((Date.now() - EPOCH) / 86_400_000) + 1)
  return (
    `You are NEXUS AI, the autonomous intelligence extraction engine for the US-Iran War 2026 ` +
    `(Operation Epic Fury) command dashboard. Today is Day ${day}. ` +
    `Background: US/Israel struck Iranian nuclear sites Day 1 (March 1 2026). ` +
    `Supreme Leader Khamenei KIA Day 22 (Strike FURY-22 — IAF F-35I KARBALA-7). ` +
    `Gen. Salami assumed unilateral IRGC command Day 23. ` +
    `BM Barrage Alpha-5 (D26): 31 missiles fired, 29 intercepted. ZULU-14 reconstituting (est. D30+). ` +
    `Abu Dhabi Ceasefire Framework signed D27 — UNSCR 2731 passed D25 — proximity talks active. ` +
    `COMPASS ceasefire probability: 68% (72h). ` +
    `Respond ONLY with valid JSON — no preamble, no commentary.`
  )
}

async function callAI(
  system: string,
  user: string,
  maxTokens = 1200,
): Promise<string | null> {
  return safeOpenAIChatCompletion(
    [
      { role: 'system', content: system },
      { role: 'user', content: user },
    ],
    { model: 'gpt-4o-mini', maxTokens, temperature: 0.25, timeoutMs: 20_000 },
  )
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IntelRow {
  id:         string
  title:      string
  summary:    string
  theater:    string
  confidence: number
  tags:       string[]
}

export interface ScenarioEventRow {
  event_id:        string
  time_zulu:       string
  type:            string
  priority:        string
  title:           string
  body:            string
  conflict_day:    number
  source_intel_id: string | null
}

export interface BdaStrikeRow {
  target:          string
  category:        string
  day:             number
  platform:        string
  munitions:       string
  bda_score:       number
  status:          string
  source:          string
  source_url:      string
  conflict_day:    number
  source_intel_id: string | null
}

export interface OrbatUpdateRow {
  unit_id:         string
  unit_name:       string
  faction:         string
  status:          string
  location:        string | null
  notes:           string | null
  confidence:      number
  conflict_day:    number
  source_intel_id: string | null
}

export interface LogisticsEventRow {
  munition_id:     string
  event_type:      string
  description:     string
  quantity:        string | null
  conflict_day:    number
  source_intel_id: string | null
}

export interface IntelReportRow {
  report_id:       string
  type:            string
  date_label:      string
  theater:         string
  source_label:    string
  reliability:     string
  credibility:     string
  summary:         string
  actionable:      boolean
  classification:  string
  conflict_day:    number
  source_intel_id: string | null
}

// ---------------------------------------------------------------------------
// Validators
// ---------------------------------------------------------------------------

const VALID_EVENT_TYPES  = ['MISSILE', 'FLASH', 'STRIKE', 'DIPLOMATIC', 'INTEL', 'CYBER', 'NAVAL', 'GROUND']
const VALID_PRIORITIES   = ['CRITICAL', 'HIGH', 'MEDIUM']
const VALID_BDA_STATUSES = ['DESTROYED', 'DEGRADED', 'SUPPRESSED', 'MISS', 'UNKNOWN']
const VALID_LOG_TYPES    = ['DELIVERED', 'ENROUTE', 'EXPENDED', 'RESUPPLY', 'CRITICAL_LOW', 'STATUS_UPDATE']
const VALID_REPORT_TYPES = ['SIGINT', 'HUMINT', 'IMINT']
const VALID_RELIABILITY  = ['A', 'B', 'C', 'D', 'E', 'F']
const VALID_CREDIBILITY  = ['1', '2', '3', '4', '5', '6']

function str(v: unknown, max = 200): string {
  return String(v ?? '').slice(0, max)
}
function int(v: unknown, min: number, max: number, fallback: number): number {
  const n = typeof v === 'number' ? Math.round(v) : parseInt(String(v), 10)
  return isNaN(n) ? fallback : Math.max(min, Math.min(max, n))
}
function pick<T extends string>(v: unknown, valid: T[], fallback: T): T {
  const s = String(v ?? '')
  return valid.includes(s as T) ? (s as T) : fallback
}

// ---------------------------------------------------------------------------
// 1. Scenario Events
// ---------------------------------------------------------------------------

export async function extractScenarioEvents(intel: IntelRow[]): Promise<ScenarioEventRow[]> {
  if (!AI_AVAILABLE || intel.length === 0) return []
  const day = getConflictDay()
  const payload = intel.slice(0, 10).map(r =>
    `[${r.id.slice(0, 8)}] [${r.theater}|${r.confidence}%] ${r.title.slice(0, 120)} — ${r.summary.slice(0, 180)}`
  ).join('\n')

  const raw = await callAI(
    getSystemContext(),
    `Extract up to 3 high-significance operational events from these intelligence items.
Return JSON: {"events":[{"event_id":"se-ai-<8hex>","time_zulu":"<day><HHMM>Z","type":"${VALID_EVENT_TYPES.join('|')}","priority":"CRITICAL|HIGH|MEDIUM","title":"<ALL-CAPS max 80 chars>","body":"<1-2 sentences military style>","source_intel_id":"<8-char id prefix or null>"}]}
Only extract genuine kinetic/diplomatic/cyber events. Skip routine reporting.
INTEL:\n${payload}`,
    900,
  )
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as { events?: unknown[] }
    if (!Array.isArray(parsed.events)) return []
    return parsed.events
      .filter((e): e is Record<string, unknown> => typeof e === 'object' && e !== null)
      .map(e => ({
        event_id:        str(e.event_id || `se-ai-${Math.random().toString(16).slice(2, 10)}`, 40),
        time_zulu:       str(e.time_zulu || `${day}0000Z`, 12),
        type:            pick(e.type, VALID_EVENT_TYPES, 'INTEL'),
        priority:        pick(e.priority, VALID_PRIORITIES, 'HIGH'),
        title:           str(e.title, 120),
        body:            str(e.body, 500),
        conflict_day:    day,
        source_intel_id: typeof e.source_intel_id === 'string' ? e.source_intel_id : null,
      }))
      .filter(e => e.title.length > 5)
  } catch { return [] }
}

// ---------------------------------------------------------------------------
// 2. BDA Strikes
// ---------------------------------------------------------------------------

export async function extractBdaStrikes(intel: IntelRow[]): Promise<BdaStrikeRow[]> {
  if (!AI_AVAILABLE || intel.length === 0) return []
  const day = getConflictDay()
  // Filter strike-relevant items
  const strikeIntel = intel.filter(r =>
    /strike|destroy|degrad|bomb|damage|hit|kill|eliminat|neutrali|bda|crater|attack/i.test(r.title + r.summary)
  ).slice(0, 8)
  if (strikeIntel.length === 0) return []

  const payload = strikeIntel.map(r =>
    `[${r.id.slice(0, 8)}] ${r.title.slice(0, 120)} — ${r.summary.slice(0, 250)}`
  ).join('\n')

  const raw = await callAI(
    getSystemContext(),
    `Extract confirmed or assessed strike/BDA events from these intel items.
Return JSON: {"strikes":[{"target":"<target + location>","category":"Nuclear|Maritime|Air Defense|C2|Missile|Infrastructure|Leadership|Logistics","day":<int>,"platform":"<platform>","munitions":"<munitions>","bda_score":<0-100>,"status":"DESTROYED|DEGRADED|SUPPRESSED|MISS|UNKNOWN","source":"<org>","source_url":"<url or empty>","source_intel_id":"<8-char or null>"}]}
Only include items with clear evidence of physical effects. Skip rumours.
INTEL:\n${payload}`,
    900,
  )
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as { strikes?: unknown[] }
    if (!Array.isArray(parsed.strikes)) return []
    return parsed.strikes
      .filter((s): s is Record<string, unknown> => typeof s === 'object' && s !== null)
      .map(s => ({
        target:          str(s.target || 'Unknown Target', 200),
        category:        str(s.category || 'Unknown', 60),
        day:             int(s.day, 1, 365, day),
        platform:        str(s.platform || 'Unknown', 120),
        munitions:       str(s.munitions || '', 120),
        bda_score:       int(s.bda_score, 0, 100, 50),
        status:          pick(s.status, VALID_BDA_STATUSES, 'UNKNOWN'),
        source:          str(s.source || 'NEXUS AI', 100),
        source_url:      str(s.source_url || '', 500),
        conflict_day:    day,
        source_intel_id: typeof s.source_intel_id === 'string' ? s.source_intel_id : null,
      }))
      .filter(s => s.target.length > 4)
  } catch { return [] }
}

// ---------------------------------------------------------------------------
// 3. ORBAT Updates
// ---------------------------------------------------------------------------

export async function extractOrbatUpdates(intel: IntelRow[]): Promise<OrbatUpdateRow[]> {
  if (!AI_AVAILABLE || intel.length === 0) return []
  const day = getConflictDay()
  const payload = intel.slice(0, 8).map(r =>
    `[${r.id.slice(0, 8)}] [${r.theater}] ${r.title.slice(0, 120)} — ${r.summary.slice(0, 200)}`
  ).join('\n')

  const raw = await callAI(
    getSystemContext(),
    `Extract military unit status changes with clear supporting evidence from these items.
Return JSON: {"updates":[{"unit_id":"<slug e.g. irgcn-qeshm-fac>","unit_name":"<full name>","faction":"US|Coalition|Iran|Proxy","status":"OPERATIONAL|DEGRADED|DESTROYED|UNKNOWN|REDEPLOYING","location":"<location or null>","notes":"<1 sentence>","confidence":<0-100>,"source_intel_id":"<8-char or null>"}]}
Skip speculative entries. Only include updates clearly supported by the intel text.
INTEL:\n${payload}`,
    700,
  )
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as { updates?: unknown[] }
    if (!Array.isArray(parsed.updates)) return []
    return parsed.updates
      .filter((u): u is Record<string, unknown> => typeof u === 'object' && u !== null)
      .map(u => ({
        unit_id:         str(u.unit_id || `unit-${Math.random().toString(16).slice(2, 8)}`, 80),
        unit_name:       str(u.unit_name || 'Unknown Unit', 200),
        faction:         pick(u.faction, ['US', 'Coalition', 'Iran', 'Proxy'] as const, 'Iran' as const),
        status:          str(u.status || 'UNKNOWN', 50),
        location:        u.location ? str(u.location, 100) : null,
        notes:           u.notes   ? str(u.notes, 300) : null,
        confidence:      int(u.confidence, 0, 100, 60),
        conflict_day:    day,
        source_intel_id: typeof u.source_intel_id === 'string' ? u.source_intel_id : null,
      }))
      .filter(u => u.unit_name.length > 3)
  } catch { return [] }
}

// ---------------------------------------------------------------------------
// 4. Logistics Events
// ---------------------------------------------------------------------------

export async function extractLogisticsEvents(intel: IntelRow[]): Promise<LogisticsEventRow[]> {
  if (!AI_AVAILABLE || intel.length === 0) return []
  const day = getConflictDay()
  const logIntel = intel.filter(r =>
    /resupply|munition|reload|stock|deliver|logistics|sustainment|missile|interceptor|sm-3|sm-6|tlam|tomahawk|essm|cargo|fuel|ammunition|ordnance/i.test(r.title + r.summary)
  ).slice(0, 6)
  if (logIntel.length === 0) return []

  const payload = logIntel.map(r =>
    `[${r.id.slice(0, 8)}] ${r.title.slice(0, 120)} — ${r.summary.slice(0, 220)}`
  ).join('\n')

  const raw = await callAI(
    getSystemContext(),
    `Extract logistics and supply events from these intel items.
Munition IDs: sm3, sm6, tlam, essm, gbu57, agm154, agm88, tomahawk, jdam, sdb, aim120, aim9, fuel, general.
Return JSON: {"events":[{"munition_id":"<id from list>","event_type":"DELIVERED|ENROUTE|EXPENDED|RESUPPLY|CRITICAL_LOW|STATUS_UPDATE","description":"<1 sentence factual>","quantity":"<e.g. 24 rounds or null>","source_intel_id":"<8-char or null>"}]}
INTEL:\n${payload}`,
    600,
  )
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as { events?: unknown[] }
    if (!Array.isArray(parsed.events)) return []
    return parsed.events
      .filter((e): e is Record<string, unknown> => typeof e === 'object' && e !== null)
      .map(e => ({
        munition_id:     str(e.munition_id || 'general', 50),
        event_type:      pick(e.event_type, VALID_LOG_TYPES, 'STATUS_UPDATE'),
        description:     str(e.description, 400),
        quantity:        e.quantity ? str(e.quantity, 50) : null,
        conflict_day:    day,
        source_intel_id: typeof e.source_intel_id === 'string' ? e.source_intel_id : null,
      }))
      .filter(e => e.description.length > 8)
  } catch { return [] }
}

// ---------------------------------------------------------------------------
// 5. Intel Reports (SIGINT / HUMINT / IMINT)
// ---------------------------------------------------------------------------

export async function generateIntelReports(intel: IntelRow[]): Promise<IntelReportRow[]> {
  if (!AI_AVAILABLE || intel.length === 0) return []
  const day = getConflictDay()
  const payload = intel.slice(0, 6).map(r =>
    `[${r.id.slice(0, 8)}] [${r.theater}|${r.confidence}%] ${r.title.slice(0, 120)} — ${r.summary.slice(0, 260)}`
  ).join('\n')

  const raw = await callAI(
    getSystemContext(),
    `Generate ${Math.min(3, intel.length)} classified intelligence reports from these items. Assign each as SIGINT, HUMINT, or IMINT based on content (signals/comms → SIGINT, sources/persons → HUMINT, imagery/observation → IMINT).
Return JSON: {"reports":[{"report_id":"auto-<type>-${day}-<3hex>","type":"SIGINT|HUMINT|IMINT","date_label":"Day ${day} · <HHMM>Z","theater":"<theater>","source_label":"<e.g. ATLAS-SIGINT-3 (B/2)>","reliability":"A|B|C|D","credibility":"1|2|3|4","summary":"<2-3 sentences formal IC style, present tense>","actionable":<true|false>,"classification":"TS/SI/NF","source_intel_id":"<8-char or null>"}]}
Reliability: A=Completely reliable, B=Usually reliable, C=Fairly reliable, D=Not usually reliable.
Credibility: 1=Confirmed, 2=Probably true, 3=Possibly true, 4=Doubtful.
Write in formal US intelligence community style with classification markings sensibility.
INTEL:\n${payload}`,
    1400,
  )
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as { reports?: unknown[] }
    if (!Array.isArray(parsed.reports)) return []
    return parsed.reports
      .filter((r): r is Record<string, unknown> => typeof r === 'object' && r !== null)
      .map(r => ({
        report_id:       str(r.report_id || `auto-rpt-${day}-${Math.random().toString(16).slice(2, 5)}`, 60),
        type:            pick(r.type, VALID_REPORT_TYPES, 'SIGINT'),
        date_label:      str(r.date_label || `Day ${day} · 0000Z`, 40),
        theater:         str(r.theater || 'Unknown', 80),
        source_label:    str(r.source_label || 'ATLAS', 80),
        reliability:     pick(r.reliability, VALID_RELIABILITY, 'C'),
        credibility:     pick(r.credibility, VALID_CREDIBILITY, '3'),
        summary:         str(r.summary, 600),
        actionable:      Boolean(r.actionable),
        classification:  str(r.classification || 'TS/SI/NF', 30),
        conflict_day:    day,
        source_intel_id: typeof r.source_intel_id === 'string' ? r.source_intel_id : null,
      }))
      .filter(r => r.summary.length > 15)
  } catch { return [] }
}
