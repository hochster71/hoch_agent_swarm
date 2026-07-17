/**
 * lib/neural-map.ts — NEXUS Self-Healing Neural Circuit Model
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * Models each platform subsystem as a "neuron" in a dependency network.
 * Each neuron has a circuit-breaker state and an exponential-backoff scheduler.
 *
 * Circuit States
 * ──────────────
 *   CLOSED     — healthy, passing traffic normally
 *   HALF_OPEN  — testing after outage; single probe in flight
 *   OPEN       — tripped; no traffic sent until cooldown expires
 *
 * Healing Priority Score (0–100)
 * ──────────────────────────────
 * Each OFFLINE/DEGRADED neuron gets a priority score based on:
 *   • downstreamDependents: how many other neurons depend on this one
 *   • msSinceLastSeen:      how long it has been dark
 *   • consecutiveFailures:  how many healing attempts have already failed
 *
 * Score = w_dep × (dependents / MAX_DEP) + w_age × min(age/MAX_AGE, 1)
 *         - w_backoff × backoffPenalty
 *
 * Dependency Graph
 * ────────────────
 *   RSS News Pipeline  ──→  HERALD-3 Ingest
 *   HERALD-3 Ingest    ──→  NEXUS Batch Analysis
 *   NEXUS Batch        ──→  Intel Database (augments quality)
 *   Intel Database     ──→  ORACLE-9
 *   Intel Database     ──→  COMPASS Economic
 *   ORACLE-9           ──→  Platform (top-level)
 *   NEXUS-AI Engine    ──→  HERALD-3, NEXUS Batch, Sitrep (augments quality)
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CircuitState = 'CLOSED' | 'HALF_OPEN' | 'OPEN'

/** Canonical system IDs — must match names used in platform/status */
export type NeuronId =
  | 'herald'
  | 'nexus-batch'
  | 'oracle'
  | 'compass'
  | 'rss'
  | 'database'
  | 'nexus-ai'

export interface NeuronConfig {
  id:           NeuronId
  label:        string
  /** System IDs this neuron depends on (upstream) */
  upstreamDeps: NeuronId[]
  /** Max consecutive failures before circuit opens */
  failThreshold: number
  /** Base cooldown (ms) before a HALF_OPEN probe is attempted */
  cooldownMs:    number
  /** Heal action: which internal API path to hit to attempt recovery */
  healPath:      string | null
  /** How critical this node is (1–3); drives priority weighting */
  criticality:   1 | 2 | 3
}

export interface NeuronState {
  id:                  NeuronId
  circuit:             CircuitState
  consecutiveFailures: number
  lastHealAttemptMs:   number    // epoch ms of last heal attempt (0 = never)
  lastSuccessMs:       number    // epoch ms of last confirmed success (0 = never)
  healCount:           number    // total heal attempts ever
  priorityScore:       number    // 0–100, recomputed each cycle
}

export interface HealAction {
  neuronId:    NeuronId
  label:       string
  healPath:    string
  reason:      string
  priority:    number
}

// ---------------------------------------------------------------------------
// Static neuron registry (topology)
// ---------------------------------------------------------------------------

export const NEURON_CONFIG: Record<NeuronId, NeuronConfig> = {
  rss: {
    id:            'rss',
    label:         'RSS News Pipeline',
    upstreamDeps:  [],
    failThreshold: 2,
    cooldownMs:    90_000,   // 90 s
    healPath:      '/api/news',
    criticality:   2,
  },
  herald: {
    id:            'herald',
    label:         'HERALD-3 Ingest',
    upstreamDeps:  ['rss'],
    failThreshold: 3,
    cooldownMs:    120_000,  // 2 min
    healPath:      '/api/ingest',
    criticality:   3,
  },
  'nexus-batch': {
    id:            'nexus-batch',
    label:         'NEXUS Batch Analysis',
    upstreamDeps:  ['herald', 'database'],
    failThreshold: 3,
    cooldownMs:    300_000,  // 5 min
    healPath:      '/api/analyze-batch',
    criticality:   2,
  },
  database: {
    id:            'database',
    label:         'Intel Database',
    upstreamDeps:  [],
    failThreshold: 2,
    cooldownMs:    60_000,
    healPath:      null,     // Supabase — can't self-heal, only monitor
    criticality:   3,
  },
  oracle: {
    id:            'oracle',
    label:         'ORACLE-9 Threat Model',
    upstreamDeps:  ['database'],
    failThreshold: 2,
    cooldownMs:    60_000,
    healPath:      '/api/oracle',
    criticality:   3,
  },
  compass: {
    id:            'compass',
    label:         'COMPASS Economic Model',
    upstreamDeps:  ['database'],
    failThreshold: 2,
    cooldownMs:    60_000,
    healPath:      '/api/compass',
    criticality:   2,
  },
  'nexus-ai': {
    id:            'nexus-ai',
    label:         'NEXUS-AI Engine',
    upstreamDeps:  [],
    failThreshold: 4,        // AI being offline is expected in fallback mode
    cooldownMs:    300_000,  // 5 min
    healPath:      null,     // env-key driven — can't restart
    criticality:   1,
  },
}

/** Maps platform/status system names → NeuronId */
export const STATUS_NAME_TO_NEURON: Record<string, NeuronId> = {
  'HERALD-3 Ingest Cron':     'herald',
  'NEXUS Batch Analysis':     'nexus-batch',
  'ORACLE-9 Threat Model':    'oracle',
  'COMPASS Economic Model':   'compass',
  'RSS News Pipeline':        'rss',
  'Intel Database':           'database',
  'NEXUS-AI Engine':          'nexus-ai',
}

// ---------------------------------------------------------------------------
// How many neurons depend (directly or transitively) on a given neuron?
// Used for priority scoring.
// ---------------------------------------------------------------------------

function countDownstreamDependents(id: NeuronId): number {
  const all = Object.values(NEURON_CONFIG)
  let count = 0
  const visited = new Set<NeuronId>()
  const queue: NeuronId[] = [id]
  while (queue.length > 0) {
    const cur = queue.shift()!
    if (visited.has(cur)) continue
    visited.add(cur)
    for (const cfg of all) {
      if (cfg.upstreamDeps.includes(cur) && !visited.has(cfg.id)) {
        count++
        queue.push(cfg.id)
      }
    }
  }
  return count
}

const DOWNSTREAM_MAP: Record<NeuronId, number> = (() => {
  const map = {} as Record<NeuronId, number>
  for (const id of Object.keys(NEURON_CONFIG) as NeuronId[]) {
    map[id] = countDownstreamDependents(id)
  }
  return map
})()

const MAX_DOWNSTREAM = Math.max(...Object.values(DOWNSTREAM_MAP), 1)

// ---------------------------------------------------------------------------
// Priority score computation
// ─────────────────────────────────────────────────────────────────────────────
// High score → heal this neuron first.
//
// Weights:
//   40% — criticality (1=low → 3=critical)
//   30% — downstream fan-out
//   20% — age of failure (normalised to 1h max)
//   10% — penalty for recent repeated failures (exponential backoff)
// ---------------------------------------------------------------------------

export function computePriorityScore(
  id:                NeuronId,
  msSinceLastSeen:   number,
  consecutiveFailures: number,
): number {
  const cfg          = NEURON_CONFIG[id]
  const criticality  = (cfg.criticality / 3) * 40
  const fanout       = (DOWNSTREAM_MAP[id] / MAX_DOWNSTREAM) * 30
  const ageScore     = Math.min(msSinceLastSeen / (3_600_000), 1) * 20
  const backoffPenalty = Math.min(consecutiveFailures * 3, 10)

  return Math.max(0, Math.round(criticality + fanout + ageScore - backoffPenalty))
}

// ---------------------------------------------------------------------------
// Circuit breaker state machine
// ---------------------------------------------------------------------------

export function shouldAttemptHeal(
  state:  NeuronState,
  nowMs:  number = Date.now(),
): boolean {
  const cfg = NEURON_CONFIG[state.id]
  if (state.circuit === 'CLOSED') return false
  if (state.circuit === 'HALF_OPEN') return false // probe already in flight

  // OPEN — check if cooldown has elapsed (exponential backoff factor)
  const backoffFactor  = Math.min(Math.pow(2, state.consecutiveFailures), 16)
  const effectiveCooldown = cfg.cooldownMs * backoffFactor
  return (nowMs - state.lastHealAttemptMs) >= effectiveCooldown
}

export function applyHealResult(
  state:   NeuronState,
  success: boolean,
  nowMs:   number = Date.now(),
): NeuronState {
  if (success) {
    return {
      ...state,
      circuit:             'CLOSED',
      consecutiveFailures: 0,
      lastSuccessMs:       nowMs,
      healCount:           state.healCount + 1,
    }
  }
  const newFailures = state.consecutiveFailures + 1
  const cfg         = NEURON_CONFIG[state.id]
  return {
    ...state,
    circuit:             newFailures >= cfg.failThreshold ? 'OPEN' : 'HALF_OPEN',
    consecutiveFailures: newFailures,
    lastHealAttemptMs:   nowMs,
    healCount:           state.healCount + 1,
  }
}

export function openCircuit(state: NeuronState, nowMs = Date.now()): NeuronState {
  return {
    ...state,
    circuit:             'OPEN',
    consecutiveFailures: state.consecutiveFailures + 1,
    lastHealAttemptMs:   nowMs,
  }
}

// ---------------------------------------------------------------------------
// Build initial state from platform/status API response
// ---------------------------------------------------------------------------
export function buildNeuralState(systems: {
  name:     string
  status:   string
  lastSeen: string | null
}[]): NeuronState[] {
  const nowMs = Date.now()
  return (Object.keys(NEURON_CONFIG) as NeuronId[]).map(id => {
    const sysName = Object.entries(STATUS_NAME_TO_NEURON).find(([, v]) => v === id)?.[0]
    const sys     = systems.find(s => s.name === sysName)
    const isOk    = sys?.status === 'ONLINE'
    const isDeg   = sys?.status === 'DEGRADED'
    const msSince = sys?.lastSeen ? nowMs - new Date(sys.lastSeen).getTime() : Infinity

    const circuit: CircuitState = isOk ? 'CLOSED' : isDeg ? 'HALF_OPEN' : 'OPEN'

    return {
      id,
      circuit,
      consecutiveFailures: isOk ? 0 : isDeg ? 1 : 2,
      lastHealAttemptMs:   0,
      lastSuccessMs:       sys?.lastSeen ? new Date(sys.lastSeen).getTime() : 0,
      healCount:           0,
      priorityScore:       computePriorityScore(id, msSince, isOk ? 0 : isDeg ? 1 : 2),
    }
  })
}

// ---------------------------------------------------------------------------
// Select heal actions for the current cycle
// ---------------------------------------------------------------------------
export function selectHealActions(states: NeuronState[], nowMs = Date.now()): HealAction[] {
  const actions: HealAction[] = []

  // Sort by priority score descending
  const sorted = [...states].sort((a, b) => b.priorityScore - a.priorityScore)

  for (const state of sorted) {
    const cfg = NEURON_CONFIG[state.id]
    if (!cfg.healPath) continue                    // can't self-heal
    if (!shouldAttemptHeal(state, nowMs)) continue // circuit still cooling off

    // Check upstream deps: if a dep is OPEN, fix that first instead
    const blockedByUpstream = cfg.upstreamDeps.some(depId => {
      const depState = states.find(s => s.id === depId)
      return depState?.circuit === 'OPEN'
    })

    if (blockedByUpstream) {
      // Still add with lower priority note — upstream must be fixed first
      continue
    }

    actions.push({
      neuronId: state.id,
      label:    cfg.label,
      healPath: cfg.healPath,
      reason:   state.circuit === 'OPEN'
        ? `Circuit OPEN — ${state.consecutiveFailures} consecutive failures`
        : `Circuit HALF_OPEN — degraded, probing recovery`,
      priority: state.priorityScore,
    })
  }

  return actions
}

// ---------------------------------------------------------------------------
// Overall neural health score (0–100) — weighted across all neurons
// ---------------------------------------------------------------------------
export function computeNeuralHealthScore(states: NeuronState[]): number {
  if (states.length === 0) return 100

  let weightedSum = 0
  let totalWeight = 0

  for (const state of states) {
    const cfg    = NEURON_CONFIG[state.id]
    const weight = cfg.criticality * (1 + DOWNSTREAM_MAP[state.id])
    const score  = state.circuit === 'CLOSED' ? 100
                 : state.circuit === 'HALF_OPEN' ? 50
                 : 0
    weightedSum += score * weight
    totalWeight += weight
  }

  return totalWeight === 0 ? 100 : Math.round(weightedSum / totalWeight)
}

// ---------------------------------------------------------------------------
// Derive a human-readable reason code for each OPEN/HALF_OPEN neuron
// ---------------------------------------------------------------------------
export function getNeuronDiagnosis(state: NeuronState): string {
  const cfg = NEURON_CONFIG[state.id]
  if (state.circuit === 'CLOSED') return 'Nominal'

  const nowMs = Date.now()
  const ageMins = state.lastSuccessMs
    ? Math.round((nowMs - state.lastSuccessMs) / 60_000)
    : null

  const ageStr = ageMins !== null ? `Last seen ${ageMins}m ago.` : 'Never seen.'

  if (state.circuit === 'HALF_OPEN') {
    return `Degraded — HALF_OPEN probe active. ${ageStr}`
  }

  // OPEN
  const backoffFactor   = Math.min(Math.pow(2, state.consecutiveFailures), 16)
  const cooldownSecs    = Math.round((cfg.cooldownMs * backoffFactor) / 1_000)
  const sinceAttemptMs  = state.lastHealAttemptMs ? nowMs - state.lastHealAttemptMs : 0
  const remainingSecs   = Math.max(0, cooldownSecs - Math.round(sinceAttemptMs / 1_000))

  return `OPEN — ${state.consecutiveFailures}× failed. ${ageStr} Retry in ${remainingSecs}s.`
}
