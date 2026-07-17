'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Radio, Cpu, Map, Zap, Menu, X,
  Newspaper, Clock, FileText, Target, LayoutDashboard, ShieldAlert, Home,
  Globe2, Skull, Activity, Scale, Satellite, Package, TrendingUp, Mic2, MonitorDot,
  BarChart3, Globe, Film, DollarSign, Brain, GitBranch, Telescope, Bot, Terminal,
  ChevronRight,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { createBrowserClient } from '@/lib/supabase'

// ── Access tier types ──────────────────────────────────────────────────────
type Role = 'admin' | 'subscriber' | 'free' | 'loading'

type NavItem = {
  label:     string
  href:      string
  icon:      React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>
  tier:      'admin' | 'subscriber' | 'public'
  sublabel?: string
}

type NavGroup = { group: string; items: NavItem[]; adminOnly?: boolean }

/* ── Navigation structure ─────────────────────────────────────────────────── */
// tier: 'admin' = admin-only (hidden from everyone else)
//       'subscriber' = locked behind upgrade prompt for free users
//       'public' = visible to all

const NAV_GROUPS: NavGroup[] = [
  {
    group: 'Command',
    items: [
      { label: 'OPS CENTER',   href: '/dashboard/command', icon: Terminal,       tier: 'public' },
      { label: 'Hub',          href: '/dashboard',         icon: LayoutDashboard, tier: 'public' },
      { label: 'NEXUS CMD',    href: '/dashboard/nexus',   icon: MonitorDot,     tier: 'admin' },
      { label: 'Brief',        href: '/dashboard/brief',   icon: BarChart3,      tier: 'subscriber' },
    ],
  },
  {
    group: 'Live News',
    items: [
      { label: 'Live Feed',   href: '/dashboard/feed',     icon: Radio,    tier: 'public' },
      { label: 'SITREP',      href: '/dashboard/sitrep',   icon: FileText, tier: 'public' },
      { label: 'Newsroom',    href: '/dashboard/newsroom', icon: Mic2,     tier: 'public' },
      { label: 'Homeland',    href: '/dashboard/homeland', icon: Home,     tier: 'public' },
      { label: 'Timeline',    href: '/dashboard/timeline', icon: Clock,    tier: 'subscriber' },
      { label: 'World Intel', href: '/dashboard/world',    icon: Globe,    tier: 'subscriber' },
    ],
  },
  {
    group: 'Analysis',
    items: [
      { label: 'ORACLE-9',  href: '/dashboard/oracle',    icon: Target,     tier: 'subscriber' },
      { label: 'Threats',   href: '/dashboard/threats',   icon: Activity,   tier: 'subscriber' },
      { label: 'ORBAT',     href: '/dashboard/orbat',     icon: Target,     tier: 'subscriber' },
      { label: 'BDA',       href: '/dashboard/bda',       icon: ShieldAlert, tier: 'subscriber' },
      { label: 'HVA',       href: '/dashboard/hva',       icon: Skull,      tier: 'subscriber' },
      { label: 'Ceasefire', href: '/dashboard/ceasefire', icon: Scale,      tier: 'subscriber' },
      { label: 'Intel',     href: '/dashboard/intel',     icon: Satellite,  tier: 'public' },
      { label: 'Logistics', href: '/dashboard/logistics', icon: Package,    tier: 'subscriber' },
      { label: 'Econ War',  href: '/dashboard/econ',      icon: TrendingUp, tier: 'subscriber' },
      { label: 'News Srcs', href: '/dashboard/news',      icon: Newspaper,  tier: 'public' },
    ],
  },
  {
    group: 'Ops',
    items: [
      { label: 'AIS · COP',     href: '/dashboard/cop', icon: Globe2, tier: 'subscriber', sublabel: 'Vessel Tracking' },
      { label: 'JADC2 · DMO',    href: '/dashboard/dmo', icon: Map,    tier: 'subscriber', sublabel: 'Kill Chain' },
    ],
  },
  {
    // This entire group is admin-only — hidden from all other users
    group: 'Platform',
    adminOnly: true,
    items: [
      { label: 'Revenue',    href: '/dashboard/revenue',    icon: DollarSign, tier: 'admin' },
      { label: 'Workflows',  href: '/dashboard/workflows',  icon: GitBranch,  tier: 'admin' },
      { label: 'Autonomous', href: '/dashboard/autonomous', icon: Bot,        tier: 'admin' },
      { label: 'Agents',     href: '/dashboard/agents',     icon: Cpu,        tier: 'admin' },
      { label: 'CMD AUTH',   href: '/dashboard/settings',   icon: ShieldAlert, tier: 'admin' },
      { label: 'DELETE ACCOUNT', href: '/account/delete', icon: ShieldAlert, tier: 'subscriber' },
    ],
  },
  {
    group: 'Intel Tools',
    items: [
      { label: 'Foresight',  href: '/dashboard/foresight',  icon: Telescope, tier: 'subscriber' },
      { label: 'Truth',      href: '/dashboard/debate',     icon: Brain,     tier: 'subscriber' },
      { label: 'Visuals',    href: '/dashboard/visuals',    icon: Film,      tier: 'subscriber' },
    ],
  },
]

/* ── Sidebar component ────────────────────────────────────────────────────── */

export function Sidebar() {
  const pathname = usePathname()
  const [role, setRole] = useState<Role>('loading')

  useEffect(() => {
    const supabase = createBrowserClient()
    supabase.auth.getSession().then(({ data }) => {
      const user = data.session?.user
      if (!user) { setRole('free'); return }
      const metaRole = user.app_metadata?.role as string | undefined
      if (metaRole === 'admin') { setRole('admin'); return }
      if (metaRole === 'subscriber') { setRole('subscriber'); return }
      // Email fallback for admin
      if (user.email === process.env.NEXT_PUBLIC_ADMIN_EMAIL) { setRole('admin'); return }
      setRole('free')
    })
  }, [])
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <>
      {/* ── Mobile hamburger ──────────────────────────────────────────── */}
      <button
        className={cn(
          'fixed z-50 md:hidden flex items-center justify-center',
          'w-11 h-11 rounded-xl',
          'bg-zinc-900/90 backdrop-blur-md border border-zinc-800/60',
          'text-emerald-400 active:scale-95 transition-all duration-150',
          'top-[max(0.75rem,env(safe-area-inset-top))] left-3',
        )}
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="Toggle navigation"
      >
        {mobileOpen ? <X size={20} strokeWidth={2.5} /> : <Menu size={20} strokeWidth={2.5} />}
      </button>

      {/* ── Mobile backdrop ───────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm md:hidden transition-opacity duration-200"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar panel ─────────────────────────────────────────────── */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex flex-col w-60',
          'bg-zinc-950/95 backdrop-blur-xl',
          'border-r border-zinc-800/50',
          'transition-transform duration-300 ease-out',
          'md:relative md:translate-x-0 md:w-56',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo / op title */}
        <div className="flex items-center gap-3 px-5 pt-5 pb-4">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-emerald-950/60 border border-emerald-800/40">
            <Zap size={16} className="text-emerald-400" />
          </div>
          <div className="min-w-0">
            <p className="text-[9px] tracking-[0.3em] text-zinc-600 uppercase leading-none mb-0.5">Operation</p>
            <p className="text-sm font-bold text-emerald-300 tracking-wider uppercase leading-none glow-green">
              Epic Fury
            </p>
          </div>
        </div>

        {/* Classification */}
        <div className="mx-4 mb-3 px-3 py-1.5 rounded-md bg-red-950/30 border border-red-900/20">
          <p className="text-[8px] text-red-400/80 tracking-[0.2em] text-center uppercase font-medium">
            UNCLASSIFIED // AI LIVE FEED
          </p>
        </div>

        {/* ── Navigation ──────────────────────────────────────────────── */}
        <nav className="flex-1 overflow-y-auto px-3 pb-3 space-y-4 scrollbar-thin" aria-label="Primary navigation">
          {NAV_GROUPS.map((navGroup) => {
            // Hide the entire admin-only group from non-admins
            if ('adminOnly' in navGroup && navGroup.adminOnly && role !== 'admin') return null

            // Filter items by role — hide subscriber items entirely from free/loading users
            const visibleItems = navGroup.items.filter((item) => {
              if (item.tier === 'admin') return role === 'admin'
              if (item.tier === 'subscriber') return role === 'admin' || role === 'subscriber'
              return true // public items always visible
            })
            if (visibleItems.length === 0) return null

            const isAdminGroup = 'adminOnly' in navGroup && navGroup.adminOnly

            return (
              <div key={navGroup.group}>
                {/* Group heading */}
                <p className={cn(
                  'px-2 pb-2 text-[10px] font-semibold tracking-[0.25em] uppercase select-none',
                  isAdminGroup ? 'text-red-600/70' : 'text-zinc-600'
                )}>
                  {navGroup.group}
                </p>

                {/* Nav items — 44px min touch target */}
                <div className="space-y-1">
                  {visibleItems.map(({ label, href, icon: Icon, sublabel }) => {
                    const active =
                      href === '/dashboard'
                        ? pathname === '/dashboard'
                        : pathname.startsWith(href)
                    const isCommandLink = href === '/dashboard/command'

                    return (
                      <Link
                        key={href}
                        href={href}
                        prefetch={false}
                        onClick={() => setMobileOpen(false)}
                        className={cn(
                          'group flex items-center gap-3 px-3 min-h-[44px] rounded-lg',
                          'text-[11px] font-medium tracking-[0.15em] uppercase',
                          'transition-all duration-200 ease-out',
                          'active:scale-[0.98]',
                          active && isCommandLink
                            ? 'bg-red-950/50 text-red-300 ring-1 ring-red-800/60 shadow-sm shadow-red-900/20'
                            : active
                            ? 'bg-emerald-950/50 text-emerald-300 ring-1 ring-emerald-800/50 shadow-sm shadow-emerald-900/20'
                            : isCommandLink
                            ? 'text-red-500/70 hover:text-red-300 hover:bg-red-950/30'
                            : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50'
                        )}
                      >
                        <Icon
                          size={16}
                          strokeWidth={active ? 2.5 : 1.75}
                          className={cn(
                            'shrink-0 transition-colors duration-200',
                            active && isCommandLink ? 'text-red-400' :
                            active ? 'text-emerald-400' :
                            isCommandLink ? 'text-red-700/60 group-hover:text-red-400' :
                            'text-zinc-600 group-hover:text-zinc-400'
                          )}
                        />
                        <span className="flex-1 truncate">
                          {label}
                          {sublabel && (
                            <span className="block text-[9px] font-mono tracking-widest text-zinc-600 group-hover:text-zinc-500 uppercase leading-tight -mt-0.5">
                              {sublabel}
                            </span>
                          )}
                        </span>
                        {active && (
                          <ChevronRight
                            size={12}
                            className={cn(
                              'shrink-0 opacity-60',
                              isCommandLink ? 'text-red-500' : 'text-emerald-500'
                            )}
                          />
                        )}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </nav>

        {/* Footer — role badge + status + faith */}
        <div className="px-5 py-4 border-t border-zinc-800/40 space-y-2">
          {role === 'admin' && (
            <div className="px-2 py-1 rounded bg-red-950/40 border border-red-900/30 text-center">
              <span className="text-[8px] text-red-400 tracking-[0.2em] uppercase font-bold">⚡ ADMIN</span>
            </div>
          )}
          {role === 'free' && (
            <Link href="/dashboard?upgrade=1" className="block px-2 py-1 rounded bg-amber-950/30 border border-amber-900/30 text-center hover:bg-amber-950/50 transition-colors">
              <span className="text-[8px] text-amber-500 tracking-[0.15em] uppercase">🔒 Upgrade to Pro</span>
            </Link>
          )}
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50" />
            <span className="text-[10px] text-zinc-500 tracking-widest uppercase">Systems Nominal</span>
          </div>
          <p className="text-[8px] text-amber-700/40 tracking-[0.15em] italic text-center leading-relaxed">
            ✝ &ldquo;God is our refuge&rdquo; — Ps 46:1
          </p>
        </div>
      </aside>
    </>
  )
}
