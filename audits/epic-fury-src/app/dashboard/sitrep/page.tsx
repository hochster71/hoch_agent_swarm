import Link from 'next/link'
import { ArrowLeft, ExternalLink, AlertTriangle, Shield } from 'lucide-react'
import { getConflictDay, toDTG } from '@/lib/conflict-day'
import { getWarStats } from '@/lib/war-stats'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { IntelStatsBanner } from '@/components/IntelStatsBanner'
import { SitrepAutoFeed } from '@/components/SitrepAutoFeed'
import { ShareButton } from '@/components/ShareButton'
import { LiveSitrepDoc } from '@/components/LiveSitrepDoc'

const _SITREP_WS   = getWarStats()
const _SITREP_DAY  = _SITREP_WS.day
const _PHASE_LABEL = _SITREP_WS.armisticeActive
  ? 'PHASE IV ARMISTICE NEGOTIATIONS ACTIVE'
  : 'CEASEFIRE ACTIVE'
const _FORDOW_NOTE = _SITREP_WS.fordowAccessGranted ? ', Fordow Day 45' : ''

const _SITREP_BRIEF = `Operation Epic Fury Day ${_SITREP_DAY} SITREP. Status: ${_PHASE_LABEL} — COMPASS confidence ${_SITREP_WS.compassCeasefire} percent. Brent crude $${_SITREP_WS.brentUsd} per barrel. Strait of Hormuz fully open — MCM complete Day 44. IAEA access: Natanz Day 41${_FORDOW_NOTE}. Iran ballistic missile stockpile at ${_SITREP_WS.bmStockPct} percent of pre-conflict inventory. DEFCON 4, FPCON ${_SITREP_WS.fpconLevel}. UNSCR 2742 in effect. No major hostile activity in last 24 hours.`

export const revalidate = 0

export function generateMetadata() {
  return { title: `SITREP #${getConflictDay()} — Operation Epic Fury` }
}

const CONFLICT_DAY = getConflictDay()

interface CiteBadgeProps {
  source: string
  date: string
  url: string
  type?: 'official' | 'wire' | 'analysis' | 'osint'
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function Cite({ source, date, url, type = 'wire' }: CiteBadgeProps) {
  const colors: Record<string, string> = {
    official: 'bg-blue-950/50 text-blue-400 border-blue-800 hover:border-blue-600',
    wire:     'bg-amber-950/50 text-amber-400 border-amber-800 hover:border-amber-600',
    analysis: 'bg-violet-950/50 text-violet-400 border-violet-800 hover:border-violet-600',
    osint:    'bg-lime-950/50 text-lime-400 border-lime-800 hover:border-lime-600',
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm border text-[9px] tracking-widest uppercase ml-1 transition-colors ${colors[type]}`}
    >
      {source}&nbsp;{date}
      <ExternalLink size={8} />
    </a>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <div className="flex items-center gap-3 border-b border-emerald-900/60 pb-2 mb-4">
      <span className="text-[9px] font-bold text-emerald-700 tracking-widest uppercase bg-emerald-950/40 border border-emerald-900 px-2 py-0.5 rounded-sm">
        {num}
      </span>
      <h2 className="text-xs font-bold tracking-widest text-emerald-400 uppercase">{title}</h2>
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function AssessmentRow({
  label,
  children,
  conf,
}: {
  label: string
  children: React.ReactNode
  conf?: 'HIGH' | 'MOD' | 'LOW'
}) {
  const confColor =
    conf === 'HIGH'
      ? 'text-emerald-400 border-emerald-700 bg-emerald-950/40'
      : conf === 'MOD'
      ? 'text-amber-400 border-amber-700 bg-amber-950/40'
      : 'text-red-400 border-red-700 bg-red-950/40'

  return (
    <div className="flex gap-3 py-2 border-b border-zinc-900/60 last:border-0">
      <p className="text-[9px] font-bold text-zinc-500 tracking-widest uppercase w-28 shrink-0 mt-0.5">
        {label}
      </p>
      <div className="flex-1 text-xs text-zinc-400 leading-relaxed">
        {children}
      </div>
      {conf && (
        <span
          className={`self-start text-[8px] font-bold tracking-widest border px-1.5 py-0.5 rounded-sm uppercase shrink-0 ${confColor}`}
        >
          {conf}
        </span>
      )}
    </div>
  )
}

export default function SitrepPage() {
  return (
    <div className="max-w-4xl space-y-5">
      {/* Intel DB stats */}
      <div className="tac-card px-3 py-2">
        <IntelStatsBanner />
      </div>

      {/* AI SITREP — NEXUS Situation Report Digest */}
      <SitrepAutoFeed />

      {/* Live news feed */}
      <LiveNewsBoard limit={15} warFilter={true} compact={false} />

      {/* Back nav */}
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-[10px] text-zinc-500 hover:text-emerald-400 tracking-widest uppercase transition-colors"
      >
        <ArrowLeft size={11} /> Command Overview
      </Link>

      {/* Document header */}
      <div className="tac-card p-5 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[9px] tracking-[0.25em] text-red-400 uppercase mb-1 flex items-center gap-1.5">
              <AlertTriangle size={10} className="animate-pulse" />
              UNCLASSIFIED // AI-SYNTHESIZED OPEN-SOURCE INTELLIGENCE // LIVE REALM-TIME FEED
            </p>
            <h1 className="text-base font-bold tracking-widest text-emerald-300 uppercase glow-green">
              Operation Epic Fury — Situation Report #{CONFLICT_DAY}
            </h1>
            <p className="text-xs text-zinc-500 tracking-widest mt-1">
              DATE-TIME GROUP: {toDTG(CONFLICT_DAY)} &nbsp;|&nbsp; REPORT CYCLE: DAILY
            </p>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <Shield size={28} className="text-emerald-800" />
            <ShareButton
              title={`SITREP #${CONFLICT_DAY} — Operation Epic Fury`}
              text={`Day ${CONFLICT_DAY} SITREP: Live US-Iran conflict status on Epic Fury War Dashboard`}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[10px] text-zinc-500 tracking-wide pt-2 border-t border-zinc-900">
          <div>
            <span className="text-zinc-600">FROM: </span>
            J2 Intelligence Cell, USCENTCOM FWD HQ, Al Udeid AB, Qatar
          </div>
          <div>
            <span className="text-zinc-600">TO: </span>
            All Assigned Forces / CCJ3 Watch Floor / CJFLCC-I / 5th Fleet CTF-50
          </div>
          <div>
            <span className="text-zinc-600">CLASSIFICATION: </span>
            <span className="text-emerald-500">UNCLASSIFIED // AI LIVE</span>
          </div>
          <div>
            <span className="text-zinc-600">REFS: </span>
            OPLAN 8044-26; IAEA DG Stmt 05 MAR 26; ISW #17
          </div>
        </div>
      </div>

      {/* Live AI SITREP assessment document */}
      <LiveSitrepDoc />
    </div>
  )
}
