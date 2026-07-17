/**
 * components/SubscriberGate.tsx  — SERVER COMPONENT
 *
 * Wraps subscriber-route page content. Free / unauthenticated users see
 * a blurred preview of the page content with an in-page upgrade overlay;
 * subscribers and admins see the full content unobstructed.
 *
 * Reads the current route from the x-pathname request header injected by
 * middleware.ts so the gate can be wired once in DashboardLayout.
 */
import { headers } from 'next/headers'
import Link from 'next/link'
import { Lock, Shield, Zap, Globe2, BarChart3, Target } from 'lucide-react'
import { createServerClient } from '@/lib/supabase-server'
import { SUBSCRIBER_ROUTES } from '@/lib/access-control'
import { getEntitlement } from '@/lib/entitlements'
import { InternalAccessBanner } from '@/components/InternalAccessBanner'

export async function SubscriberGate({ children }: { children: React.ReactNode }) {
  // ── 1. Determine current route ──────────────────────────────────────────
  const hdrs = await headers()
  const pathname = hdrs.get('x-pathname') ?? ''

  // When route header is unavailable (some edge/runtime contexts), fail closed.
  // This component is only used in dashboard layout, so default to gated.
  if (!pathname) {
    const supabase = await createServerClient()
    const { data: { session } } = await supabase.auth.getSession()
    const entitlement = getEntitlement(session?.user ?? null)
    if (entitlement.hasAccess) {
      return (
        <>
          <InternalAccessBanner mode={entitlement.mode} />
          {children}
        </>
      )
    }

    return (
      <div className="relative min-h-[60vh]" aria-label="Subscriber-only content preview">
        <div className="pointer-events-none select-none p-4 sm:p-6" aria-hidden="true">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 opacity-60">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
                <div className="h-3 w-24 bg-zinc-800 rounded mb-3" />
                <div className="space-y-2">
                  <div className="h-2 w-full bg-zinc-800 rounded" />
                  <div className="h-2 w-5/6 bg-zinc-800 rounded" />
                  <div className="h-2 w-2/3 bg-zinc-800 rounded" />
                </div>
                <div className="mt-4 h-20 bg-zinc-800/70 rounded" />
              </div>
            ))}
          </div>
        </div>

        <div className="absolute inset-0 z-40 flex flex-col items-center justify-center gap-6 px-4 py-12">
          <div className="w-full max-w-md border border-zinc-700 bg-zinc-900/95 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl shadow-black">
            <div className="bg-gradient-to-r from-red-950/60 via-zinc-900 to-zinc-900 px-6 py-5 text-center border-b border-zinc-800">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Lock className="w-4 h-4 text-red-400" />
                <span className="font-mono text-[10px] tracking-widest text-red-400 uppercase">PRO ACCESS REQUIRED</span>
              </div>
              <p className="text-white font-semibold text-base leading-tight">Unlock Full Intelligence Access</p>
              <p className="text-zinc-400 text-xs mt-1">This section is restricted to Operation Epic Fury subscribers.</p>
            </div>
            <div className="px-6 pb-6 pt-4 space-y-2">
              <Link
                href="/upgrade"
                className="block w-full text-center bg-cyan-500 hover:bg-cyan-400 active:bg-cyan-600 text-black text-sm font-bold px-4 py-2.5 rounded-lg transition-colors"
              >
                Subscribe — Unlock Now →
              </Link>
              <Link
                href="/login?next=/dashboard"
                className="block w-full text-center bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium px-4 py-2 rounded-lg transition-colors border border-zinc-700"
              >
                Already a subscriber? Sign in
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const isSubscriberRoute = SUBSCRIBER_ROUTES.some(
    r => pathname === r || pathname.startsWith(r + '/')
  )

  // Public route — render as-is, no gating needed
  if (!isSubscriberRoute) return <>{children}</>

  // ── 2. Check session role ───────────────────────────────────────────────
  const supabase = await createServerClient()
  const { data: { session } } = await supabase.auth.getSession()
  const entitlement = getEntitlement(session?.user ?? null)

  if (entitlement.hasAccess) {
    return (
      <>
        <InternalAccessBanner mode={entitlement.mode} />
        {children}
      </>
    )
  }

  // ── 3. Free / unauthenticated — static preview + upgrade overlay ─────────
  // Use a static skeleton preview instead of rendering live children so
  // subscriber-only API polling does not fire and spam 401/403/502 logs.
  return (
    <div className="relative min-h-[60vh]" aria-label="Subscriber-only content preview">
      {/* Static, non-interactive mock preview */}
      <div className="pointer-events-none select-none p-4 sm:p-6" aria-hidden="true">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 opacity-60">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
              <div className="h-3 w-24 bg-zinc-800 rounded mb-3" />
              <div className="space-y-2">
                <div className="h-2 w-full bg-zinc-800 rounded" />
                <div className="h-2 w-5/6 bg-zinc-800 rounded" />
                <div className="h-2 w-2/3 bg-zinc-800 rounded" />
              </div>
              <div className="mt-4 h-20 bg-zinc-800/70 rounded" />
            </div>
          ))}
        </div>
      </div>

      {/* Upgrade overlay */}
      <div className="absolute inset-0 z-40 flex flex-col items-center justify-center gap-6 px-4 py-12">
        {/* Backdrop panel */}
        <div className="w-full max-w-md border border-zinc-700 bg-zinc-900/95 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl shadow-black">

          {/* Header strip */}
          <div className="bg-gradient-to-r from-red-950/60 via-zinc-900 to-zinc-900 px-6 py-5 text-center border-b border-zinc-800">
            <div className="flex items-center justify-center gap-2 mb-1">
              <Lock className="w-4 h-4 text-red-400" />
              <span className="font-mono text-[10px] tracking-widest text-red-400 uppercase">
                PRO ACCESS REQUIRED
              </span>
            </div>
            <p className="text-white font-semibold text-base leading-tight">
              Unlock Full Intelligence Access
            </p>
            <p className="text-zinc-400 text-xs mt-1">
              This section is restricted to Operation Epic Fury subscribers.
            </p>
          </div>

          {/* Feature highlights */}
          <div className="px-6 py-4 space-y-2.5">
            {[
              { icon: Shield,   text: 'BDA · HVA · ORBAT — live target intelligence' },
              { icon: Globe2,   text: 'AIS vessel tracking + JADC2 kill-chain view' },
              { icon: Target,   text: 'ORACLE-9 threat assessments + ceasefire models' },
              { icon: Zap,      text: 'Real-time NEXUS AI synthesis — updated every 6 h' },
              { icon: BarChart3, text: 'Foresight probabilistic forecasting + debate engine' },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-start gap-2.5">
                <Icon className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0" />
                <span className="text-zinc-300 text-xs leading-relaxed">{text}</span>
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="px-6 pb-6 pt-2 space-y-2">
            <Link
              href="/upgrade"
              className="block w-full text-center bg-cyan-500 hover:bg-cyan-400 active:bg-cyan-600 text-black text-sm font-bold px-4 py-2.5 rounded-lg transition-colors"
            >
              Subscribe — Unlock Now →
            </Link>
            <Link
              href={`/login?next=${encodeURIComponent(pathname || '/dashboard')}`}
              className="block w-full text-center bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium px-4 py-2 rounded-lg transition-colors border border-zinc-700"
            >
              Already a subscriber? Sign in
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
