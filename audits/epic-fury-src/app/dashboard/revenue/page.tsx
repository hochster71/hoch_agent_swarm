/**
 * app/dashboard/revenue/page.tsx — Layer 8 Wealth & Revenue Autonomy Dashboard
 *
 * Displays the DGM/GEA-powered revenue optimization engine:
 * active revenue streams, proposed monetization strategies,
 * revenue ledger stats, and compliance status.
 *
 * ACCESS: Admin only — server-side redirect guard + middleware layer
 */

import { redirect } from 'next/navigation'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { DollarSign } from 'lucide-react'
import RevenuePanel   from '@/components/RevenuePanel'

export const dynamic    = 'force-dynamic'
export const revalidate = 0

async function requireAdmin() {
  const cookieStore = await cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: () => {},
      },
    }
  )
  const { data: { user } } = await supabase.auth.getUser()
  const metaRole = user?.app_metadata?.role as string | undefined
  const isAdmin = metaRole === 'admin' || user?.email === process.env.ADMIN_EMAIL
  if (!isAdmin) redirect('/dashboard')
}

export default async function RevenueDashboardPage() {
  await requireAdmin()

  return (
    <div className="space-y-6 p-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <DollarSign className="w-6 h-6 text-emerald-400" />
        <div>
          <h1 className="text-lg font-bold text-zinc-100 tracking-tight">
            Wealth & Revenue Autonomy Engine
          </h1>
          <p className="text-xs text-zinc-500">
            Layer 8 · DGM/GEA monetization optimization · 24/7 parallel compounding
          </p>
        </div>
      </div>

      {/* Ethics notice */}
      <div className="rounded border border-emerald-900/40 bg-emerald-950/10 p-3">
        <div className="flex items-start gap-2">
          <DollarSign className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
          <p className="text-[10px] text-emerald-400 leading-relaxed">
            <strong>Truth-First Revenue Policy:</strong> All strategies are AI-proposed by Governor Layer 8
            using DGM/GEA pattern evolution. Every strategy requires compliance review before activation.
            No automated spend, withdrawal, or high-risk instruments. Editorial independence maintained
            from all sponsors and advertisers. All financial signals carry mandatory &quot;Not Investment Advice&quot;
            disclaimers. Revenue compounds into owner-controlled accounts only after human authorization.
          </p>
        </div>
      </div>

      {/* Full revenue panel */}
      <RevenuePanel compact={false} />
    </div>
  )
}
