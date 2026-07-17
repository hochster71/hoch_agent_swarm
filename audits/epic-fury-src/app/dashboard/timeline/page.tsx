import { createServerClient } from '@/lib/supabase-server'
import { STATIC_INTEL } from '@/lib/static-intel'
import type { Intel } from '@/lib/types'
import { Clock, ExternalLink, ShieldCheck, ShieldAlert, DatabaseZap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'

export const revalidate = 0

const THEATER_COLORS: Record<string, string> = {
  Hormuz:     'border-l-red-600    bg-red-950/10',
  Gulf:       'border-l-amber-600  bg-amber-950/10',
  Maritime:   'border-l-cyan-600   bg-cyan-950/10',
  Air:        'border-l-sky-600    bg-sky-950/10',
  Land:       'border-l-orange-600 bg-orange-950/10',
  Cyber:      'border-l-purple-600 bg-purple-950/10',
  Nuclear:    'border-l-yellow-600 bg-yellow-950/10',
  Diplomatic: 'border-l-blue-600   bg-blue-950/10',
  Economic:   'border-l-lime-600   bg-lime-950/10',
}

const THEATER_DOT: Record<string, string> = {
  Hormuz:     'bg-red-500',
  Gulf:       'bg-amber-500',
  Maritime:   'bg-cyan-500',
  Air:        'bg-sky-500',
  Land:       'bg-orange-500',
  Cyber:      'bg-purple-500',
  Nuclear:    'bg-yellow-400',
  Diplomatic: 'bg-blue-500',
  Economic:   'bg-lime-500',
}

function TimelineEntry({ intel, isLast }: { intel: Intel; isLast: boolean }) {
  const cardStyle = THEATER_COLORS[intel.theater] ?? 'border-l-zinc-700 bg-zinc-900/20'
  const dotColor = THEATER_DOT[intel.theater] ?? 'bg-zinc-600'

  const dt = new Date(intel.created_at)
  const dateStr = dt.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
  const timeStr = dt.toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
  })

  return (
    <div className="flex gap-4">
      {/* Timeline spine */}
      <div className="flex flex-col items-center">
        <div className={cn('w-2.5 h-2.5 rounded-full shrink-0 mt-2.5', dotColor)} />
        {!isLast && <div className="w-px flex-1 bg-zinc-800 mt-1" />}
      </div>

      {/* Entry card */}
      <div className={cn('tac-card rounded-sm p-3 mb-4 w-full border-l-2 space-y-1.5', cardStyle)}>
        {/* Timestamp row */}
        <div className="flex items-center gap-2">
          <Clock size={9} className="text-zinc-600 shrink-0" />
          <span className="text-[10px] text-zinc-500 tracking-widest">
            {dateStr} · {timeStr}Z
          </span>
          <span className="text-[10px] font-bold tracking-widest uppercase text-zinc-400 ml-1">
            ▸ {intel.theater}
          </span>
          {intel.verified ? (
            <ShieldCheck size={9} className="text-emerald-500 ml-auto" />
          ) : (
            <ShieldAlert size={9} className="text-amber-700 ml-auto" />
          )}
          <span
            className={cn(
              'text-[9px] tracking-widest px-1.5 py-0.5 rounded-sm border',
              intel.confidence >= 70
                ? 'text-emerald-400 border-emerald-800 bg-emerald-950/30'
                : intel.confidence >= 40
                ? 'text-amber-400 border-amber-800 bg-amber-950/30'
                : 'text-red-400 border-red-900 bg-red-950/30'
            )}
          >
            {intel.confidence}%
          </span>
        </div>

        {/* Title */}
        <h3 className="text-xs font-bold text-emerald-200 tracking-wider uppercase leading-snug">
          {intel.title}
        </h3>

        {/* Summary */}
        <p className="text-[10px] text-zinc-500 leading-relaxed">{intel.summary}</p>

        {/* Citation footer */}
        <div className="flex items-center gap-2 pt-1">
          {intel.source_name && (
            <span className="text-[9px] text-zinc-600 tracking-wider uppercase">
              via {intel.source_name}
            </span>
          )}
          {intel.author && (
            <span className="text-[9px] text-zinc-700">/ {intel.author}</span>
          )}
          {intel.tags && intel.tags.length > 0 && (
            <div className="flex gap-1 ml-auto">
              {intel.tags.slice(0, 4).map((t) => (
                <span
                  key={t}
                  className="text-[8px] px-1 py-0.5 rounded-sm bg-zinc-900 border border-zinc-800 text-zinc-600 tracking-wider uppercase"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
          {intel.source_url && (
            <a
              href={intel.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-0.5 text-[9px] text-zinc-600 hover:text-emerald-400 transition-colors ml-auto tracking-widest"
            >
              CITE <ExternalLink size={8} />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

function groupByDate(items: Intel[]): Map<string, Intel[]> {
  const map = new Map<string, Intel[]>()
  for (const item of items) {
    const key = new Date(item.created_at).toLocaleDateString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
    })
    const existing = map.get(key) ?? []
    existing.push(item)
    map.set(key, existing)
  }
  return map
}

export default async function TimelinePage() {
  const supabase = await createServerClient()

  let events: Intel[] = []
  let dbError = false
  let usingFallback = false

  try {
    const { data, error } = await supabase
      .from('intel')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(200)
    if (!error) events = data ?? []
    else dbError = true
  } catch {
    dbError = true
  }

  if (events.length === 0) {
    events = [...STATIC_INTEL].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    usingFallback = true
  }

  const grouped = groupByDate(events)
  const dateKeys = [...grouped.keys()]

  return (
    <section className="space-y-4 max-w-3xl">
      {/* Live news — new events as they break */}
      <LiveNewsBoard limit={10} warFilter={true} compact={false} />

      {/* Header */}
      <div className="tac-section-header mb-4">
        <Clock size={16} className="text-emerald-400" />
        <span>Conflict Timeline</span>
        {dbError && (
          <span className="ml-2 text-[10px] text-red-500 tracking-wider">⚠ DB ERROR</span>
        )}
        {usingFallback && (
          <span className="ml-2 flex items-center gap-1 text-[10px] text-amber-500/70 tracking-wider">
            <DatabaseZap size={10} /> STATIC CACHE
          </span>
        )}
        <span className="ml-auto text-[10px] text-zinc-600 tracking-widest normal-case font-normal">
          {events.length} EVENTS
        </span>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 pb-2 border-b border-zinc-900">
        {Object.entries(THEATER_DOT).map(([theater, dotClass]) => (
          <div key={theater} className="flex items-center gap-1.5">
            <div className={cn('w-1.5 h-1.5 rounded-full', dotClass)} />
            <span className="text-[9px] text-zinc-600 tracking-widest uppercase">{theater}</span>
          </div>
        ))}
      </div>

      {/* Empty state — should never render now that STATIC_INTEL is the fallback */}
      {events.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-zinc-600">
          <p className="text-xs tracking-widest uppercase">No events recorded yet.</p>
        </div>
      )}

      {/* Timeline grouped by date */}
      {dateKeys.map((dateKey) => {
        const dayEvents = grouped.get(dateKey) ?? []
        return (
          <div key={dateKey} className="space-y-0">
            {/* Date separator */}
            <div className="flex items-center gap-3 mb-3">
              <div className="h-px flex-1 bg-zinc-900" />
              <span className="text-[9px] text-zinc-500 tracking-widest uppercase px-2 py-1 border border-zinc-800 rounded-sm bg-zinc-950">
                {dateKey}
              </span>
              <div className="h-px flex-1 bg-zinc-900" />
            </div>

            {/* Events for this date */}
            {dayEvents.map((ev, idx) => (
              <TimelineEntry
                key={ev.id}
                intel={ev}
                isLast={idx === dayEvents.length - 1 && dateKey === dateKeys[dateKeys.length - 1]}
              />
            ))}
          </div>
        )
      })}
    </section>
  )
}
