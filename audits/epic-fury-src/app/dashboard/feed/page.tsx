import { createServerClient } from '@/lib/supabase-server'
import { FeedRealtimeWrapper } from '@/components/FeedRealtimeWrapper'
import { IntelStatsBanner } from '@/components/IntelStatsBanner'
import { STATIC_INTEL } from '@/lib/static-intel'
import type { Intel } from '@/lib/types'
import { Radio, DatabaseZap } from 'lucide-react'

/**
 * /dashboard/feed
 * Server-renders the initial intel list; client wrapper adds realtime updates.
 * Falls back to STATIC_INTEL when the DB table is empty or unavailable.
 */
export const revalidate = 0 // always fresh on navigation

export default async function FeedPage() {
  const supabase = await createServerClient()

  let initialIntel: Intel[] = []
  let usingFallback = false
  let dbError = false

  try {
    const result = await supabase
      .from('intel')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(50)
    if (result.error) {
      dbError = true
    } else {
      initialIntel = result.data ?? []
    }
  } catch {
    dbError = true
  }

  if (initialIntel.length === 0) {
    initialIntel = STATIC_INTEL
    usingFallback = true
  }

  return (
    <section className="space-y-4">
      {/* Intel DB stats strip */}
      <div className="tac-card px-3 py-2">
        <IntelStatsBanner />
      </div>

      {/* Section header */}
      <div className="tac-section-header mb-4">
        <Radio size={16} className="text-emerald-400 animate-pulse" />
        <span>Live Intel Feed</span>
        {dbError && (
          <span className="ml-2 flex items-center gap-1 text-[10px] text-red-500 tracking-wider">
            ⚠ DB ERROR
          </span>
        )}
        {usingFallback && (
          <span className="ml-2 flex items-center gap-1 text-[10px] text-amber-500/70 tracking-wider">
            <DatabaseZap size={10} /> STATIC CACHE
          </span>
        )}
        <span className="ml-auto text-xs text-zinc-500 tracking-widest normal-case font-normal">
          {initialIntel.length} REPORTS LOADED
        </span>
      </div>

      {/* Realtime client wrapper injects new cards without full reload */}
      <FeedRealtimeWrapper initialIntel={initialIntel} />
    </section>
  )
}
