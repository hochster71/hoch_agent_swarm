'use client'

import { cn } from '@/lib/utils'
import { ShieldCheck, SlidersHorizontal } from 'lucide-react'

export interface FilterState {
  theater: string      // 'ALL' or specific theater
  confLevel: string    // 'ALL' | 'HIGH' | 'MED' | 'LOW'
  sourceType: string   // 'ALL' or specific source type
  verifiedOnly: boolean
}

interface FeedFiltersProps {
  filters: FilterState
  onChange: (f: FilterState) => void
  total: number
  showing: number
}

const THEATERS = ['ALL', 'Hormuz', 'Gulf', 'Maritime', 'Air', 'Land', 'Cyber', 'Nuclear', 'Diplomatic', 'Economic']
const CONF_LEVELS = [
  { label: 'ALL CONF', value: 'ALL' },
  { label: '≥70% HIGH', value: 'HIGH' },
  { label: '40-69% MED', value: 'MED' },
  { label: '<40% LOW', value: 'LOW' },
]
const SOURCE_TYPES = ['ALL', 'Official', 'Wire', 'Analysis', 'OSINT', 'SIGINT', 'Media']

function FilterBtn({
  active,
  onClick,
  children,
  className,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
  className?: string
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'text-[10px] tracking-widest uppercase px-3 min-h-[36px] rounded-lg border transition-all duration-150 whitespace-nowrap active:scale-95',
        active
          ? 'bg-emerald-950/60 border-emerald-700/60 text-emerald-300 shadow-sm shadow-emerald-900/20'
          : 'bg-zinc-900/40 border-zinc-800/50 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300 hover:bg-zinc-800/50',
        className
      )}
    >
      {children}
    </button>
  )
}

export function FeedFilters({ filters, onChange, total, showing }: FeedFiltersProps) {
  const set = (partial: Partial<FilterState>) => onChange({ ...filters, ...partial })

  return (
    <div className="space-y-2 pb-3 border-b border-zinc-900">
      {/* Theater row */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[9px] text-zinc-600 tracking-widest uppercase w-14 shrink-0">Theater</span>
        {THEATERS.map((t) => (
          <FilterBtn
            key={t}
            active={filters.theater === t}
            onClick={() => set({ theater: t })}
          >
            {t === 'ALL' ? 'ALL' : t}
          </FilterBtn>
        ))}
      </div>

      {/* Confidence + Source Type row */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[9px] text-zinc-600 tracking-widest uppercase w-14 shrink-0">Conf</span>
        {CONF_LEVELS.map(({ label, value }) => (
          <FilterBtn
            key={value}
            active={filters.confLevel === value}
            onClick={() => set({ confLevel: value })}
          >
            {label}
          </FilterBtn>
        ))}
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[9px] text-zinc-600 tracking-widest uppercase w-14 shrink-0">Source</span>
        {SOURCE_TYPES.map((s) => (
          <FilterBtn
            key={s}
            active={filters.sourceType === s}
            onClick={() => set({ sourceType: s })}
          >
            {s}
          </FilterBtn>
        ))}

        {/* Verified toggle */}
        <button
          onClick={() => set({ verifiedOnly: !filters.verifiedOnly })}
          className={cn(
            'ml-2 flex items-center gap-1.5 text-[10px] tracking-widest uppercase px-3 min-h-[36px] rounded-lg border transition-all duration-150 active:scale-95',
            filters.verifiedOnly
              ? 'bg-emerald-950/60 border-emerald-700/60 text-emerald-300 shadow-sm shadow-emerald-900/20'
              : 'bg-zinc-900/40 border-zinc-800/50 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300 hover:bg-zinc-800/50'
          )}
        >
          <ShieldCheck size={11} />
          VERIFIED
        </button>
      </div>

      {/* Result count */}
      <div className="flex items-center gap-2 pt-0.5">
        <SlidersHorizontal size={9} className="text-zinc-700" />
        <span className="text-[9px] text-zinc-600 tracking-widest">
          {showing === total
            ? `${total} REPORTS`
            : `${showing} / ${total} REPORTS`}
        </span>
        {(filters.theater !== 'ALL' ||
          filters.confLevel !== 'ALL' ||
          filters.sourceType !== 'ALL' ||
          filters.verifiedOnly) && (
          <button
            onClick={() =>
              onChange({ theater: 'ALL', confLevel: 'ALL', sourceType: 'ALL', verifiedOnly: false })
            }
            className="text-[10px] text-red-600 hover:text-red-400 tracking-widest uppercase ml-auto px-3 min-h-[36px] flex items-center rounded-lg hover:bg-red-950/20 active:scale-95 transition-all"
          >
            CLEAR FILTERS
          </button>
        )}
      </div>
    </div>
  )
}
