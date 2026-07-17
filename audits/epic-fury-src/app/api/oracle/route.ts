import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { computeAllThreats } from '@/lib/oracle-engine'
import { getConflictDay } from '@/lib/conflict-day'
import { requireSubscriber } from '@/lib/api-auth'

// Force dynamic — needs live Supabase intel for signal resolution
export const revalidate = 0

export async function GET(req: NextRequest) {
  const deny = await requireSubscriber(req)
  if (deny) return deny
  try {
    const day = getConflictDay()

    // Pull recent intel text for dynamic signal resolution
    let recentIntelText = ''
    try {
      const url    = process.env.NEXT_PUBLIC_SUPABASE_URL
      const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
      if (url && anonKey) {
        const sb = createClient(url, anonKey, { auth: { persistSession: false } })
        const since = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString()
        const { data } = await sb
          .from('intel')
          .select('title, summary')
          .gte('created_at', since)
          .order('created_at', { ascending: false })
          .limit(80)
        recentIntelText = (data ?? [])
          .map((r: { title: string; summary: string }) => `${r.title} ${r.summary}`)
          .join(' ')
      }
    } catch { /* non-fatal — fall back to hardcoded signal states */ }

    const threats = computeAllThreats(day, recentIntelText)

    return NextResponse.json(
      {
        threats,
        conflictDay: day,
        generatedAt: new Date().toISOString(),
        modelVersion: 'ORACLE-9.3',
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=60',
        },
      },
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Oracle engine error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
