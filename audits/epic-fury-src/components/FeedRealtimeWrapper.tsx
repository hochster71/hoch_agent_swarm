'use client'

import { useEffect, useState, useMemo } from 'react'
import { Search, X } from 'lucide-react'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'
import { IntelCard } from '@/components/IntelCard'
import { FeedFilters, type FilterState } from '@/components/FeedFilters'
import type { Intel } from '@/lib/types'

interface FeedRealtimeWrapperProps {
  initialIntel: Intel[]
}

const DEFAULT_FILTERS: FilterState = {
  theater: 'ALL',
  confLevel: 'ALL',
  sourceType: 'ALL',
  verifiedOnly: false,
}

/**
 * Client component that manages the intel feed list.
 * Subscribes to Supabase Realtime for INSERT events on the 'intel' table.
 * Provides client-side filtering by theater, confidence, source type, and verified status.
 */
export function FeedRealtimeWrapper({ initialIntel }: FeedRealtimeWrapperProps) {
  const [intel, setIntel] = useState<Intel[]>(initialIntel)
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)
  const [search, setSearch] = useState('')

  useEffect(() => {
    // Guard: skip realtime when Supabase credentials are not configured
    if (!SUPABASE_CONFIGURED) return

    const supabase = createBrowserClient()

    const channel = supabase
      .channel('intel-feed')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'intel' },
        (payload) => {
          const newItem = payload.new as Intel
          setIntel((prev) => [newItem, ...prev].slice(0, 200))
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'intel' },
        (payload) => {
          const updated = payload.new as Intel
          setIntel((prev) => prev.map((item) => item.id === updated.id ? updated : item))
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  const filtered = useMemo(() => {
    return intel.filter((item) => {
      if (filters.theater !== 'ALL' && item.theater !== filters.theater) return false
      if (filters.verifiedOnly && !item.verified) return false
      if (filters.confLevel === 'HIGH' && item.confidence < 70) return false
      if (filters.confLevel === 'MED' && (item.confidence < 40 || item.confidence >= 70)) return false
      if (filters.confLevel === 'LOW' && item.confidence >= 40) return false
      if (filters.sourceType !== 'ALL' && item.source_type !== filters.sourceType) return false
      if (search.trim()) {
        const q = search.toLowerCase()
        const inTitle   = item.title.toLowerCase().includes(q)
        const inSummary = (item.summary ?? '').toLowerCase().includes(q)
        const inSource  = (item.source_name ?? '').toLowerCase().includes(q)
        const inTags    = (item.tags ?? []).some((t) => t.toLowerCase().includes(q))
        if (!inTitle && !inSummary && !inSource && !inTags) return false
      }
      return true
    })
  }, [intel, filters, search])

  if (intel.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-zinc-600">
        <p className="text-xs tracking-widest uppercase">No intel reports yet.</p>
        <p className="text-[10px] tracking-widest mt-1">
          Insert rows into the <span className="text-emerald-700">intel</span> table to populate this feed.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Search bar */}
      <div className="relative">
        <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search reports — title, summary, source, tags..."
          className="w-full bg-zinc-900 border border-zinc-800 rounded-sm pl-8 pr-8 py-2 text-xs text-zinc-300 placeholder-zinc-600 focus:outline-none focus:border-emerald-700 tracking-wide transition-colors"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            <X size={11} />
          </button>
        )}
      </div>

      <FeedFilters
        filters={filters}
        onChange={setFilters}
        total={intel.length}
        showing={filtered.length}
      />

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-zinc-600">
          <p className="text-xs tracking-widest uppercase">No reports match active filters.</p>
        </div>
      ) : (
        filtered.map((item) => <IntelCard key={item.id} intel={item} />)
      )}
    </div>
  )
}

