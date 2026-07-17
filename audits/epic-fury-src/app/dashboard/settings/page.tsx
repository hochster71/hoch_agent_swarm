import type { ReactNode } from 'react'
import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import {
  ShieldAlert, CheckCircle2, XCircle,
  Activity, GitBranch, Cpu, Database, Eye,
} from 'lucide-react'
import { createServerClient as createSSRClient } from '@supabase/ssr'
import { createServerClient } from '@/lib/supabase-server'
import { PlatformHealth }   from '@/components/PlatformHealth'
import { IntelStatsBanner } from '@/components/IntelStatsBanner'
import { CmdIntelAudit }    from '@/components/CmdIntelAudit'
import { CmdOpsCenter }     from '@/components/CmdOpsCenter'
import { getConflictDay }   from '@/lib/conflict-day'

export const revalidate = 0

async function requireAdmin() {
  const cookieStore = await cookies()
  const supabase = createSSRClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => cookieStore.getAll(), setAll: () => {} } }
  )
  const { data: { user } } = await supabase.auth.getUser()
  const isAdmin = (user?.app_metadata?.role as string) === 'admin' || user?.email === process.env.ADMIN_EMAIL
  if (!isAdmin) redirect('/dashboard')
}

export default async function CommandAuthorityPage() {
  await requireAdmin()

  const day      = getConflictDay()
  const nowUtc   = new Date().toLocaleString('en-US', {
    timeZone: 'UTC', month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }) + 'Z'
  const buildDate = new Date().toISOString().split('T')[0]

  // ── Supabase connectivity + quick stats ────────────────────────────────────
  let supabaseOk   = false
  let intelCount   = 0
  let autoMerge    = 'unknown'
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? ''

  if (supabaseUrl) {
    try {
      const supabase = await createServerClient()

      const [intelRes, cfgRes] = await Promise.allSettled([
        supabase.from('intel').select('id', { count: 'exact', head: true }),
        supabase.from('platform_config').select('key,value').in('key', ['auto_merge_enabled', 'aec_enabled']),
      ])

      if (intelRes.status === 'fulfilled' && !intelRes.value.error) {
        supabaseOk = true
        intelCount = intelRes.value.count ?? 0
      }
      if (cfgRes.status === 'fulfilled' && cfgRes.value.data) {
        const rows = cfgRes.value.data as { key: string; value: string }[]
        const am = rows.find(r => r.key === 'auto_merge_enabled')
        if (am) autoMerge = am.value === 'true' ? 'ENABLED' : 'DISABLED'
      }
    } catch { /* probe failed; surface in UI */ }
  }

  const githubWired = !!(process.env.GITHUB_PAT && process.env.GITHUB_REPO_OWNER && process.env.GITHUB_REPO_NAME)

  return (
    <section className="space-y-6">

      {/* ── PAGE HEADER ── */}
      <div className="flex items-center gap-3 border-b border-zinc-800/60 pb-4">
        <ShieldAlert size={18} className="text-red-400" />
        <div>
          <h1 className="text-[11px] font-bold tracking-[0.2em] text-zinc-100 uppercase">
            Command Authority Center
          </h1>
          <p className="text-[9px] text-zinc-500 mt-0.5 tracking-widest">
            EPIC FURY / DAY {day} / {nowUtc} — full intelligence visibility + autonomous ops control
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <StatusPill ok={supabaseOk} label="SUPABASE" />
          <StatusPill ok={githubWired} label="GITHUB AEC" />
        </div>
      </div>

      {/* ── INTEL STATS BANNER ── */}
      <div className="tac-card px-3 py-2">
        <IntelStatsBanner />
      </div>

      {/* ── QUICK STATS STRIP ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatTile
          icon={<Database size={12} className="text-emerald-400" />}
          label="Intel Rows (DB)"
          value={supabaseOk ? intelCount.toLocaleString() : '–'}
          accent={intelCount > 0 ? 'green' : 'amber'}
        />
        <StatTile
          icon={<Activity size={12} className="text-purple-400" />}
          label="Op Day"
          value={`D${day}`}
          accent="amber"
        />
        <StatTile
          icon={<GitBranch size={12} className="text-sky-400" />}
          label="Auto Merge"
          value={autoMerge}
          accent={autoMerge === 'ENABLED' ? 'green' : 'red'}
        />
        <StatTile
          icon={<Cpu size={12} className="text-zinc-400" />}
          label="AEC / GitHub"
          value={githubWired ? 'WIRED' : 'NO TOKEN'}
          accent={githubWired ? 'green' : 'red'}
          hint={githubWired ? undefined : 'Set GITHUB_TOKEN + GITHUB_REPO in Vercel env vars'}
        />
      </div>

      {/* ── PLATFORM HEALTH (existing component) ── */}
      <div>
        <SectionHeading icon={<Activity size={12} className="text-purple-400" />} label="Platform Neural Health" />
        <PlatformHealth compact={false} />
      </div>

      {/* ── LIVE INTEL AUDIT STREAM ── */}
      <div>
        <SectionHeading icon={<Eye size={12} className="text-emerald-400" />} label="Live Intel Audit Stream — Every Item, Fully Cited" />
        <CmdIntelAudit limit={40} compact={false} />
      </div>

      {/* ── AUTONOMOUS OPERATIONS CENTER ── */}
      <div>
        <SectionHeading icon={<Cpu size={12} className="text-sky-400" />} label="Autonomous Ops Center — Governor · AEC · Workflows · Ingest" />
        <CmdOpsCenter />
      </div>

      {/* ── SYSTEM REFERENCE ── */}
      <details className="tac-card p-4 group">
        <summary className="text-[10px] font-mono tracking-widest text-zinc-500 uppercase cursor-pointer list-none
          flex items-center gap-2 hover:text-zinc-300 transition-colors">
          <GitBranch size={10} /> System Reference / Env Status
          <span className="ml-auto text-zinc-700 group-open:hidden">▸ expand</span>
          <span className="ml-auto text-zinc-500 hidden group-open:inline">▾ collapse</span>
        </summary>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <RefCard title="Supabase">
            <RefRow label="Status"     value={supabaseOk ? 'CONNECTED' : 'ERROR'} accent={supabaseOk ? 'green' : 'red'} />
            <RefRow label="URL"        value={supabaseUrl ? supabaseUrl.replace('https://', '').slice(0, 28) + '…' : '(not set)'} />
            <RefRow label="Anon Key"   value="••••••••••••••••" />
            <RefRow label="Intel Rows" value={supabaseOk ? String(intelCount) : '–'} accent={intelCount > 0 ? 'green' : undefined} />
            <RefRow label="Realtime"   value="ENABLED" accent="green" />
          </RefCard>
          <RefCard title="AEC / Autonomy">
            <RefRow label="GITHUB_PAT"        value={process.env.GITHUB_PAT        ? 'SET ✓' : 'MISSING ✗'} accent={process.env.GITHUB_PAT        ? 'green' : 'red'} />
            <RefRow label="GITHUB_REPO_OWNER" value={process.env.GITHUB_REPO_OWNER ?? '(not set)'}          accent={process.env.GITHUB_REPO_OWNER ? 'green' : 'red'} />
            <RefRow label="GITHUB_REPO_NAME"  value={process.env.GITHUB_REPO_NAME  ?? '(not set)'}          accent={process.env.GITHUB_REPO_NAME  ? 'green' : 'red'} />
            <RefRow label="Auto Merge"   value={autoMerge}                                            accent={autoMerge === 'ENABLED'  ? 'green' : 'red'} />
            <RefRow label="CRON_SECRET"  value={process.env.CRON_SECRET     ? 'SET ✓' : 'MISSING ✗'} accent={process.env.CRON_SECRET     ? 'green' : 'red'} />
            <RefRow label="OPENAI_KEY"   value={process.env.OPENAI_API_KEY  ? 'SET ✓' : 'MISSING ✗'} accent={process.env.OPENAI_API_KEY  ? 'green' : 'red'} />
          </RefCard>
          <RefCard title="Dashboard">
            <RefRow label="Operation"      value="EPIC FURY" accent="amber" />
            <RefRow label="Theatre"        value="Strait of Hormuz" />
            <RefRow label="Conflict Start" value="01 MAR 2026 00:00Z" />
            <RefRow label="Current UTC"    value={nowUtc} />
            <RefRow label="Classification" value="UNCLASSIFIED // AI LIVE SYNTHESIS" accent="green" />
          </RefCard>
          <RefCard title="Build">
            <RefRow label="Framework"    value="Next.js 15.x (App Router)" />
            <RefRow label="Supabase SDK" value="2.x (SSR)" />
            <RefRow label="Build Date"   value={buildDate} />
            <RefRow label="Node Env"     value={process.env.NODE_ENV ?? 'development'} />
            <RefRow label="Vercel Crons" value="14 active" accent="green" />
          </RefCard>
        </div>
      </details>

    </section>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionHeading({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      {icon}
      <span className="text-[10px] font-mono tracking-[0.18em] text-zinc-400 uppercase">{label}</span>
    </div>
  )
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`flex items-center gap-1 text-[8px] font-mono tracking-widest px-2 py-1 rounded border
      ${ok ? 'text-emerald-400 border-emerald-800/40 bg-emerald-950/20' : 'text-red-400 border-red-800/40 bg-red-950/20'}`}>
      {ok ? <CheckCircle2 size={8} /> : <XCircle size={8} />}
      {label}
    </span>
  )
}

function StatTile({
  icon, label, value, accent, hint,
}: {
  icon: ReactNode
  label: string
  value: string
  accent?: 'green' | 'amber' | 'red'
  hint?: string
}) {
  const valClass =
    accent === 'green' ? 'text-emerald-400' :
    accent === 'amber' ? 'text-amber-400'   :
    accent === 'red'   ? 'text-red-400'     :
    'text-zinc-100'

  return (
    <div className="tac-card p-3 space-y-1" title={hint}>
      <div className="flex items-center gap-1.5 text-[9px] text-zinc-600 font-mono tracking-widest">
        {icon} {label}
      </div>
      <div className={`text-lg font-bold font-mono tabular-nums ${valClass}`}>{value}</div>
      {hint && <div className="text-[8px] text-zinc-700 leading-tight">{hint}</div>}
    </div>
  )
}

function RefCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="tac-card rounded-sm p-4 space-y-2">
      <p className="text-[10px] tracking-widest text-emerald-600 uppercase mb-3">{title}</p>
      {children}
    </div>
  )
}

function RefRow({
  label, value, accent,
}: {
  label: string
  value: string
  accent?: 'green' | 'amber' | 'red'
}) {
  const cls =
    accent === 'green' ? 'text-emerald-400' :
    accent === 'amber' ? 'text-amber-400'   :
    accent === 'red'   ? 'text-red-400'     :
    'text-zinc-300'

  return (
    <div className="flex justify-between items-center text-xs border-b border-zinc-800 pb-1.5">
      <span className="text-zinc-500 tracking-widest">{label}</span>
      <span className={`${cls} font-medium`}>{value}</span>
    </div>
  )
}
