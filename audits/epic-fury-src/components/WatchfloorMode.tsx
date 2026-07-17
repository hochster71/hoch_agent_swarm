'use client'

/**
 * WatchfloorModeSelector — Operator role-based dashboard lens
 *
 * Allows the operator to select their watchfloor role, which gates and
 * highlights specific dashboard panels.  Persisted in localStorage.
 *
 * Roles:
 *   CITIZEN         — Public briefing view (basic intel, ticker)
 *   ANALYST         — Full intel fusion, provenance, ORACLE-9 access
 *   J2/J3           — All-source fusion + targeting + BDA + ORBAT
 *   MARITIME CMD    — NAVCENT focus: DMO, Hormuz, MCM, ZB-Alpha, Logistics
 *
 * Naval doctrine: E-1→E-9 Master Chief Ops Specialist / LDO Surface Line 6120
 */

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'

export type WatchfloorMode = 'CITIZEN' | 'ANALYST' | 'J2-J3' | 'MARITIME-CMD'

export interface WatchfloorConfig {
  mode:          WatchfloorMode
  label:         string
  shortLabel:    string
  color:         string          // Tailwind text class
  borderColor:   string          // Tailwind border class
  bgColor:       string          // Tailwind bg class
  badgeColor:    string          // for the pill
  icon:          string          // emoji
  description:   string
  /** Panel IDs shown at full prominence */
  highlight:     string[]
  /** Panel IDs hidden entirely */
  hidden:        string[]
}

export const WATCHFLOOR_MODES: Record<WatchfloorMode, WatchfloorConfig> = {
  'CITIZEN': {
    mode:        'CITIZEN',
    label:       'Citizen Briefing',
    shortLabel:  'CITIZEN',
    color:       'text-zinc-300',
    borderColor: 'border-zinc-700',
    bgColor:     'bg-zinc-900/40',
    badgeColor:  'bg-zinc-800 text-zinc-300',
    icon:        '🌐',
    description: 'Public open-source situation awareness',
    highlight:   ['ticker', 'threat-domain', 'herald', 'nexus-doctrine'],
    hidden:      ['governor', 'revenue', 'workflow', 'autonomous', 'debate', 'foresight', 'synthesis', 'bmd-battle', 'intel-provenance'],
  },
  'ANALYST': {
    mode:        'ANALYST',
    label:       'Intel Analyst',
    shortLabel:  'ANALYST',
    color:       'text-blue-300',
    borderColor: 'border-blue-800',
    bgColor:     'bg-blue-950/20',
    badgeColor:  'bg-blue-900/60 text-blue-300',
    icon:        '🔭',
    description: 'All-source fusion · ORACLE-9 · Provenance graph',
    highlight:   ['oracle', 'foresight', 'synthesis', 'debate', 'intel-provenance', 'provenance-pulse'],
    hidden:      ['governor', 'revenue', 'workflow', 'autonomous'],
  },
  'J2-J3': {
    mode:        'J2-J3',
    label:       'J2/J3 Operations',
    shortLabel:  'J2/J3',
    color:       'text-amber-300',
    borderColor: 'border-amber-800',
    bgColor:     'bg-amber-950/20',
    badgeColor:  'bg-amber-900/60 text-amber-300',
    icon:        '🎯',
    description: 'Joint Ops · BDA · ORBAT · JADC2 targeting',
    highlight:   ['bmd-battle', 'oracle', 'foresight', 'synthesis', 'bda', 'orbat', 'nexus-doctrine'],
    hidden:      ['governor', 'revenue', 'workflow', 'autonomous', 'herald'],
  },
  'MARITIME-CMD': {
    mode:        'MARITIME-CMD',
    label:       'Maritime Commander',
    shortLabel:  'NAVCENT',
    color:       'text-cyan-300',
    borderColor: 'border-cyan-800',
    bgColor:     'bg-cyan-950/20',
    badgeColor:  'bg-cyan-900/60 text-cyan-300',
    icon:        '⚓',
    description: 'NAVCENT · DMO · Hormuz / ZB-Alpha · Logistics',
    highlight:   ['bmd-battle', 'dmo', 'logistics', 'nexus-doctrine', 'oracle'],
    hidden:      ['governor', 'revenue', 'workflow', 'autonomous', 'debate', 'herald'],
  },
}

// ── Context ───────────────────────────────────────────────────────────────────
interface WatchfloorCtx {
  config:    WatchfloorConfig
  setMode:   (m: WatchfloorMode) => void
  isVisible: (panelId: string) => boolean
  isHighlit: (panelId: string) => boolean
}

const Ctx = createContext<WatchfloorCtx>({
  config:    WATCHFLOOR_MODES['CITIZEN'],
  setMode:   () => {},
  isVisible: () => true,
  isHighlit: () => false,
})

export function useWatchfloor() { return useContext(Ctx) }

// ── Provider ──────────────────────────────────────────────────────────────────
export function WatchfloorProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<WatchfloorMode>('CITIZEN')

  // Restore persisted mode
  useEffect(() => {
    try {
      const stored = localStorage.getItem('epic-fury-watchfloor') as WatchfloorMode | null
      if (stored && WATCHFLOOR_MODES[stored]) setModeState(stored)
    } catch { /* SSR safe */ }
  }, [])

  const setMode = useCallback((m: WatchfloorMode) => {
    setModeState(m)
    try { localStorage.setItem('epic-fury-watchfloor', m) } catch { /* SSR safe */ }
  }, [])

  const config = WATCHFLOOR_MODES[mode]

  const isVisible = useCallback(
    (panelId: string) => !config.hidden.includes(panelId),
    [config]
  )
  const isHighlit = useCallback(
    (panelId: string) => config.highlight.includes(panelId),
    [config]
  )

  return (
    <Ctx.Provider value={{ config, setMode, isVisible, isHighlit }}>
      {children}
    </Ctx.Provider>
  )
}

// ── Selector Widget (rendered in TopBar or Sidebar) ───────────────────────────
export function WatchfloorModeSelector({ compact = false }: { compact?: boolean }) {
  const { config, setMode } = useWatchfloor()
  const [open, setOpen] = useState(false)

  const modes = Object.values(WATCHFLOOR_MODES)

  return (
    <div className="relative">
      {/* Current mode pill — button */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-1.5 rounded-md px-2 py-1 border text-[9px] font-mono font-bold tracking-widest uppercase transition-all duration-150 hover:opacity-90 active:scale-95 ${config.borderColor} ${config.bgColor} ${config.color}`}
        aria-label={`Watchfloor mode: ${config.label}`}
        title="Switch watchfloor operator mode"
      >
        <span>{config.icon}</span>
        {!compact && <span className="hidden sm:inline">{config.shortLabel}</span>}
        <span className="text-zinc-600">▾</span>
      </button>

      {/* Dropdown */}
      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1.5 z-50 w-64 rounded-md border border-zinc-700 bg-zinc-950 shadow-2xl overflow-hidden">
            <div className="px-3 py-2 border-b border-zinc-800">
              <p className="text-[7px] font-mono font-bold text-zinc-600 tracking-[0.3em] uppercase">WATCHFLOOR OPERATOR MODE</p>
            </div>
            {modes.map(m => (
              <button
                key={m.mode}
                onClick={() => { setMode(m.mode); setOpen(false) }}
                className={`w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-zinc-900 transition-colors border-b border-zinc-900 last:border-0 ${config.mode === m.mode ? 'bg-zinc-900/60' : ''}`}
              >
                <span className="text-base leading-none mt-0.5 shrink-0">{m.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-[9px] font-mono font-bold tracking-widest uppercase ${m.color}`}>{m.label}</span>
                    {config.mode === m.mode && (
                      <span className={`text-[7px] font-mono px-1.5 py-0.5 rounded ${m.badgeColor}`}>ACTIVE</span>
                    )}
                  </div>
                  <p className="text-[8px] text-zinc-600 font-mono mt-0.5">{m.description}</p>
                </div>
              </button>
            ))}
            <div className="px-3 py-2 border-t border-zinc-800 bg-zinc-950/50">
              <p className="text-[7px] font-mono text-zinc-700">
                Role-based panel lens — persisted to local storage
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ── Panel wrapper that respects watchfloor gating ─────────────────────────────
export function WatchfloorPanel({
  panelId,
  children,
  className = '',
}: {
  panelId: string
  children: ReactNode
  className?: string
}) {
  const { isVisible, isHighlit } = useWatchfloor()

  if (!isVisible(panelId)) return null

  const highlighted = isHighlit(panelId)
  return (
    <div
      className={`transition-all duration-300 ${highlighted ? 'ring-1 ring-emerald-800/40 ring-offset-0' : ''} ${className}`}
    >
      {children}
    </div>
  )
}
