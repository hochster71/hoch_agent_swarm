import type { Intel } from '@/lib/types'
import { ExternalLink, ShieldCheck, ShieldAlert, Tag, AlertTriangle, AlertOctagon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface IntelCardProps {
  intel: Intel
}

// Special tags that get colored warning badges instead of default zinc
const SPECIAL_TAG_STYLES: Record<string, string> = {
  'contradiction-flagged': 'bg-red-950/60 border-red-700 text-red-400',
  'contradiction:HARD':    'bg-red-950/60 border-red-700 text-red-300',
  'contradiction:SOFT':    'bg-orange-950/60 border-orange-700 text-orange-400',
  'source-disagreement':   'bg-amber-950/60 border-amber-700 text-amber-400',
  'confidence-decayed':    'bg-yellow-950/60 border-yellow-800 text-yellow-500',
  'kinetic-contradiction': 'bg-rose-950/60 border-rose-600 text-rose-300',
}

function isSpecialTag(tag: string): boolean {
  return tag in SPECIAL_TAG_STYLES ||
    tag.startsWith('disagrees-with:') ||
    tag.startsWith('contradiction:')
}

function getTagStyle(tag: string): string {
  if (SPECIAL_TAG_STYLES[tag]) return SPECIAL_TAG_STYLES[tag]
  if (tag.startsWith('disagrees-with:')) return 'bg-amber-950/60 border-amber-700 text-amber-400'
  if (tag.startsWith('contradiction:'))  return 'bg-red-950/60 border-red-700 text-red-400'
  return 'bg-zinc-900 border border-zinc-800 text-zinc-500'
}

/** Confidence badge color: ≥70 green, 40-69 amber, <40 red */
function ConfidenceBadge({ pct }: { pct: number }) {
  const color =
    pct >= 70
      ? 'border-emerald-700 text-emerald-400 bg-emerald-950/50'
      : pct >= 40
      ? 'border-amber-700 text-amber-400 bg-amber-950/50'
      : 'border-red-700 text-red-400 bg-red-950/50'

  return (
    <span className={cn('status-badge border tracking-widest', color)}>
      {pct}% CONF
    </span>
  )
}

const THEATER_COLORS: Record<string, string> = {
  Hormuz:     'text-red-400',
  Gulf:       'text-amber-400',
  Cyber:      'text-purple-400',
  Air:        'text-sky-400',
  Land:       'text-orange-400',
  Diplomatic: 'text-blue-400',
  Nuclear:    'text-yellow-400',
  Maritime:   'text-cyan-400',
  Economic:   'text-lime-400',
}

const SOURCE_TYPE_COLORS: Record<string, string> = {
  Official:  'text-blue-300 bg-blue-950/40 border-blue-800',
  Wire:      'text-amber-300 bg-amber-950/40 border-amber-800',
  Analysis:  'text-violet-300 bg-violet-950/40 border-violet-800',
  Media:     'text-cyan-300 bg-cyan-950/40 border-cyan-800',
  OSINT:     'text-lime-300 bg-lime-950/40 border-lime-800',
  SIGINT:    'text-rose-300 bg-rose-950/40 border-rose-800',
}

export function IntelCard({ intel }: IntelCardProps) {
  const theaterColor = THEATER_COLORS[intel.theater] ?? 'text-zinc-400'
  const sourceTypeClass = intel.source_type
    ? (SOURCE_TYPE_COLORS[intel.source_type] ?? 'text-zinc-400 bg-zinc-900 border-zinc-700')
    : null

  const ts = new Date(intel.created_at).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  })
  const dateStr = new Date(intel.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })

  return (
    <article className="tac-card rounded-sm p-4 space-y-2.5">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {intel.verified ? (
            <ShieldCheck size={11} className="text-emerald-400 shrink-0" />
          ) : (
            <ShieldAlert size={11} className="text-amber-600 shrink-0" />
          )}
          <h3 className="text-xs font-bold text-emerald-300 tracking-wider uppercase leading-snug">
            {intel.title}
          </h3>
        </div>
        <ConfidenceBadge pct={intel.confidence} />
      </div>

      {/* Summary */}
      <p className="text-xs text-zinc-400 leading-relaxed">{intel.summary}</p>

      {/* Tags row */}
      {intel.tags && intel.tags.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <Tag size={9} className="text-zinc-600" />
          {/* Render special credibility warning tags first with colored badges */}
          {intel.tags.filter(t => isSpecialTag(t)).map((tag) => (
            <span
              key={tag}
              className={cn('text-[9px] px-1.5 py-0.5 rounded-sm border tracking-wider uppercase font-semibold flex items-center gap-0.5', getTagStyle(tag))}
            >
              {(tag.includes('contradiction') || tag.includes('kinetic')) && <AlertOctagon size={8} className="shrink-0" />}
              {tag.includes('disagreement') && <AlertTriangle size={8} className="shrink-0" />}
              {tag.startsWith('disagrees-with:') ? `⚡ ${tag.replace('disagrees-with:', '')}` : tag}
            </span>
          ))}
          {/* Regular tags */}
          {intel.tags.filter(t => !isSpecialTag(t) && !t.startsWith('kf') && !t.startsWith('cite:')).map((tag) => (
            <span
              key={tag}
              className="text-[9px] px-1.5 py-0.5 rounded-sm bg-zinc-900 border border-zinc-800 text-zinc-500 tracking-wider uppercase"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer row */}
      <div className="flex items-center justify-between pt-1 border-t border-zinc-900">
        {/* Left: theater + timestamp */}
        <div className="flex items-center gap-3">
          <span className={cn('text-[10px] tracking-widest uppercase font-bold', theaterColor)}>
            ▸ {intel.theater}
          </span>
          <span className="text-[10px] text-zinc-600 tracking-widest">
            {dateStr} {ts}Z
          </span>
        </div>

        {/* Right: source name + type + link */}
        <div className="flex items-center gap-2">
          {intel.source_name && (
            <span className={cn('text-[9px] px-1.5 py-0.5 rounded-sm border tracking-widest uppercase', sourceTypeClass)}>
              {intel.source_name}
            </span>
          )}
          {intel.author && (
            <span className="text-[9px] text-zinc-600 tracking-wider">/ {intel.author}</span>
          )}
          {intel.source_url && (
            <a
              href={intel.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-1 text-[10px] text-zinc-500 hover:text-emerald-400 min-h-[36px] px-2.5 rounded-md hover:bg-emerald-950/30 active:scale-95 transition-all"
            >
              CITE <ExternalLink size={10} />
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
