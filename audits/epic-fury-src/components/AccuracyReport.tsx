'use client'

import { useEffect, useState } from 'react'
import { Award, TrendingUp } from 'lucide-react'
import { getConflictDay } from '@/lib/conflict-day'

interface AccuracyData {
  accuracyPct: number
  conflictDay?: number
  report?: { gradeLetter?: string; overallPct?: number; narrative?: string }
}

const CONFLICT_DAY = getConflictDay()

export function AccuracyReport() {
  const [accuracy, setAccuracy] = useState<AccuracyData | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/intel/accuracy', { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setAccuracy(d) })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  if (!accuracy) return null

  const pct = accuracy.accuracyPct ?? null
  const grade = accuracy.report?.gradeLetter ?? null
  const narrative = accuracy.report?.narrative ?? null

  return (
    <section className="mb-4">
      <div className="video-feed-frame border border-emerald-900/50 rounded-sm bg-emerald-950/10 p-4 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">NEXUS AI</span>
        </div>
        <div className="flex items-center gap-2 mb-3 relative z-[1]">
          <Award size={14} className="text-emerald-400 drop-shadow-[0_0_4px_rgba(16,185,129,0.5)]" />
          <span className="text-[9px] font-mono text-emerald-500 tracking-widest uppercase glow-green">NEXUS-AI Accuracy Report — Day {accuracy.conflictDay ?? CONFLICT_DAY}</span>
          <span className="ml-auto text-[8px] font-mono text-zinc-600">LIVE ▸ /api/intel/accuracy</span>
        </div>
        <div className="flex items-end gap-6 flex-wrap">
          {/* Score */}
          <div className="flex-shrink-0">
            <div className="text-[40px] font-black font-mono leading-none text-emerald-300">
              {pct !== null ? `${pct.toFixed(1)}%` : '--'}
            </div>
            <div className="text-[9px] font-mono text-zinc-500 mt-1 tracking-widest">FORECAST ACCURACY</div>
          </div>
          {/* Grade */}
          {grade && (
            <div className="flex-shrink-0 pb-1">
              <div className="text-[32px] font-black font-mono leading-none text-amber-400">{grade}</div>
              <div className="text-[9px] font-mono text-zinc-500 mt-1 tracking-widest">GRADE</div>
            </div>
          )}
          {/* Bar */}
          {pct !== null && (
            <div className="flex-1 min-w-[160px] pb-2">
              <div className="h-2 bg-zinc-900 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${Math.min(pct, 100)}%`,
                    background: pct >= 80 ? '#10b981' : pct >= 60 ? '#f59e0b' : '#ef4444',
                  }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-[8px] font-mono text-zinc-700">0%</span>
                <span className="text-[8px] font-mono text-zinc-700">100%</span>
              </div>
            </div>
          )}
          <div className="flex-shrink-0 pb-2">
            <TrendingUp size={22} className={pct !== null && pct >= 70 ? 'text-emerald-400' : 'text-zinc-600'} />
          </div>
        </div>
        {narrative && (
          <p className="text-[10px] text-zinc-400 leading-relaxed mt-3 border-t border-zinc-800/60 pt-3 font-mono">
            {narrative}
          </p>
        )}
      </div>
    </section>
  )
}
