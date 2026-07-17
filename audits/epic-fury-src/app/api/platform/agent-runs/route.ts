import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { requireSubscriber } from '@/lib/api-auth'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'
export const revalidate = 0

export async function GET(req: NextRequest) {
  const deny = await requireSubscriber(req)
  if (deny) return deny

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_SERVICE_KEY
  if (!url || !key) {
    return NextResponse.json({ ok: false, error: 'Supabase not configured' }, { status: 503 })
  }

  const limitRaw = Number.parseInt(new URL(req.url).searchParams.get('limit') ?? '25', 10)
  const limit = Number.isFinite(limitRaw) ? Math.min(Math.max(limitRaw, 1), 100) : 25

  const sb = createClient(url, key)
  const { data, error } = await sb
    .from('agent_run_logs')
    .select('id,agent_name,route,trigger,status,conflict_day,duration_ms,error_message,detail,started_at,finished_at,created_at')
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) {
    return NextResponse.json({ ok: false, error: error.message }, { status: 500 })
  }

  const rows = data ?? []
  const total = rows.length
  const failed = rows.filter((r) => r.status === 'FAILED').length
  const success = rows.filter((r) => r.status === 'SUCCESS').length
  const skipped = rows.filter((r) => r.status === 'SKIPPED').length

  return NextResponse.json({
    ok: true,
    summary: {
      total,
      success,
      failed,
      skipped,
      successRate: total > 0 ? Number((success / total).toFixed(4)) : 1,
    },
    runs: rows,
  })
}
