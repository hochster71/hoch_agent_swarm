'use client'

import { useCallback, useState } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import type { EconomicCascade, ClosureSeverity } from '@/lib/compass-engine'

interface CompassResponse {
  cascade:      EconomicCascade
  conflictDay:  number
  generatedAt:  string
  modelVersion: string
}

interface MetricRowProps {
  label:    string
  value:    string | number
  sub?:     string
  color?:   string
  delta?:   string
  deltaDir?: 'up' | 'down' | 'neutral'
}

function MetricRow({ label, value, sub, color = 'text-slate-100', delta, deltaDir }: MetricRowProps) {
  const dirColor =
    deltaDir === 'up'   ? 'text-red-400' :
    deltaDir === 'down' ? 'text-green-400' :
                          'text-slate-500'
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-slate-800/60 last:border-0">
      <span className="text-xs font-mono text-slate-500 truncate pr-2">{label}</span>
      <div className="flex items-center gap-2 shrink-0">
        {delta && (
          <span className={`text-xs font-mono ${dirColor}`}>{delta}</span>
        )}
        <div className="text-right">
          <span className={`text-sm font-mono font-bold ${color}`}>{value}</span>
          {sub && <span className="text-xs font-mono text-slate-600 ml-1">{sub}</span>}
        </div>
      </div>
    </div>
  )
}

const SEVERITY_LABELS: Record<ClosureSeverity, string> = {
  PARTIAL:    'Partial',
  CONTESTED:  'Contested',
  CLOSED:     'Closed',
}

const SEVERITY_COLOR: Record<ClosureSeverity, string> = {
  PARTIAL:    'border-yellow-700 text-yellow-400 bg-yellow-950/30',
  CONTESTED:  'border-orange-700 text-orange-400 bg-orange-950/30',
  CLOSED:     'border-red-700 text-red-400 bg-red-950/30',
}

export function CompassPanel() {
  const [data,     setData]     = useState<CompassResponse | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)
  const [severity, setSeverity] = useState<ClosureSeverity>('CONTESTED')
  const [lastRefresh, setLastRefresh] = useState('')

  const fetchData = useCallback(async (sev?: ClosureSeverity) => {
    try {
      const s   = sev ?? severity
      const res = await fetch(`/api/compass?severity=${s}`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json() as CompassResponse
      setData(json)
      setError(null)
      setLastRefresh(new Date().toLocaleTimeString('en-US', { hour12: false }) + 'Z')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fetch error')
    } finally {
      setLoading(false)
    }
  }, [severity])

  useSmartPoll(fetchData, 60_000)

  function changeSeverity(sev: ClosureSeverity) {
    setSeverity(sev)
    setLoading(true)
    void fetchData(sev)
  }

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-700/50 rounded-sm p-4 animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-48 mb-3" />
        {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-6 bg-slate-800 rounded mb-1.5" />)}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900/60 border border-red-900/40 rounded-sm p-4">
        <p className="text-red-400 text-xs font-mono">COMPASS OFFLINE — {error ?? 'No data'}</p>
      </div>
    )
  }

  const { cascade } = data

  return (
    <div className="bg-slate-950/80 border border-slate-700/40 rounded-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/40">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-lime-500" />
          <span className="text-xs font-mono font-bold text-slate-200 tracking-widest">COMPASS</span>
          <span className="text-xs font-mono text-slate-500">{data.modelVersion}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-600">DAY {data.conflictDay}</span>
          <span className="text-xs font-mono text-slate-600">{lastRefresh}</span>
        </div>
      </div>

      {/* Scenario selector */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800/60">
        <span className="text-xs font-mono text-slate-500 mr-1">HORMUZ:</span>
        {(['PARTIAL', 'CONTESTED', 'CLOSED'] as ClosureSeverity[]).map(s => (
          <button
            key={s}
            onClick={() => changeSeverity(s)}
            className={`text-xs font-mono px-3 min-h-[36px] border rounded-lg transition-all duration-150 active:scale-95 ${
              severity === s
                ? SEVERITY_COLOR[s]
                : 'border-slate-700 text-slate-500 hover:text-slate-300 hover:bg-slate-800/30'
            }`}
          >
            {SEVERITY_LABELS[s]}
          </button>
        ))}
      </div>

      {/* Scenario label */}
      <div className="px-4 py-1.5 bg-slate-900/40 border-b border-slate-800/40">
        <p className="text-xs font-mono text-slate-600 line-clamp-1">{cascade.inputs.scenarioLabel}</p>
      </div>

      {/* Energy metrics */}
      <div className="px-4 py-2 border-b border-slate-800/60">
        <p className="text-xs font-mono text-slate-500 tracking-widest mb-1">ENERGY</p>
        <MetricRow
          label="Brent Crude"
          value={`$${cascade.brentUsd}/bbl`}
          delta={`+$${Math.round(cascade.brentUsd - cascade.inputs.oilBaseline)}`}
          deltaDir="up"
          color="text-red-400"
        />
        <MetricRow
          label="WTI (discount)"
          value={`$${(cascade.brentUsd - cascade.wtiDiscount).toFixed(1)}/bbl`}
          sub={`-$${cascade.wtiDiscount} disc.`}
          color="text-orange-300"
        />
        <MetricRow
          label="LNG Spot"
          value={`$${cascade.lngSpotUsd}/MMBtu`}
          color="text-amber-400"
        />
        <MetricRow
          label="Hormuz Throughput"
          value={`${cascade.hormuzThroughputMbpd} mb/d`}
          sub={`of 18.9 mb/d`}
          deltaDir={cascade.hormuzThroughputMbpd < 18.9 ? 'down' : 'neutral'}
          delta={`${Math.round((1 - cascade.hormuzThroughputMbpd / 18.9) * 100)}% cut`}
          color="text-yellow-400"
        />
      </div>

      {/* Shipping + insurance */}
      <div className="px-4 py-2 border-b border-slate-800/60">
        <p className="text-xs font-mono text-slate-500 tracking-widest mb-1">SHIPPING</p>
        <MetricRow
          label="Lloyd's War-Risk"
          value={`${cascade.lloydWarRiskPct}% CIF`}
          deltaDir="up"
          color="text-orange-400"
        />
        <MetricRow
          label="VLCC Charter Rate"
          value={`$${cascade.vllcCharterKusd}k/day`}
          color="text-slate-300"
        />
        <MetricRow
          label="Cape Reroute Cost"
          value={`$${cascade.capeReroutingCostKusd}k/voyage`}
          sub="+18 days"
          color="text-slate-300"
        />
      </div>

      {/* Macro / sovereign */}
      <div className="px-4 py-2 border-b border-slate-800/60">
        <p className="text-xs font-mono text-slate-500 tracking-widest mb-1">MACRO / SOVEREIGN</p>
        <MetricRow
          label="UAE CDS Spread"
          value={`+${cascade.uaeCdsBps} bps`}
          deltaDir="up"
          color="text-amber-300"
        />
        <MetricRow
          label="Aramco Equity Disc."
          value={`-${cascade.aramcoDiscountPct}%`}
          deltaDir="down"
          color="text-red-300"
        />
        <MetricRow
          label="GCC SWF Outflows"
          value={`$${cascade.gccSwfOutflowBn}bn`}
          sub="cumul."
          color="text-slate-400"
        />
        <MetricRow
          label="DXY (flight-to-safety)"
          value={`+${cascade.dxyMovePp}pp`}
          deltaDir="up"
          color="text-blue-400"
        />
      </div>

      {/* CPI impulse */}
      <div className="px-4 py-2">
        <p className="text-xs font-mono text-slate-500 tracking-widest mb-1">CPI IMPULSE (ANNUALISED)</p>
        <MetricRow label="Global"   value={`+${cascade.globalCpiImpulsePp}pp`} deltaDir="up" color="text-orange-400" />
        <MetricRow label="US"       value={`+${cascade.usCpiImpulsePp}pp`}     deltaDir="up" color="text-slate-300" />
        <MetricRow label="Euro Area" value={`+${cascade.euCpiImpulsePp}pp`}    deltaDir="up" color="text-red-300" />
      </div>
    </div>
  )
}
