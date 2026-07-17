/**
 * components/VisualFeed.tsx — EPIC FURY 2026 Visual Assets Gallery
 *
 * Displays AI-generated cinematic visuals from Layer 4 of the Platform Governor.
 * Shows generated images, queued video assets, and their full provenance.
 * All assets are post-verification only; labelled as AI-generated.
 */

'use client'

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Film, Map, BarChart3, Image, Video, Clock,
  CheckCircle2, AlertCircle, Loader2, RefreshCw,
  Cpu, Layers,
} from 'lucide-react'
import type { VisualAsset, VisualAssetType, VisualStatus, VisualStats } from '@/lib/visual-engine'

interface VisualAPIResponse {
  visuals: VisualAsset[]
  stats:   VisualStats
}

// ── Asset type → icon mapping ───────────────────────────────────────────────

const TYPE_ICONS: Record<VisualAssetType, React.ElementType> = {
  MAP:         Map,
  VIDEO:       Video,
  INFOGRAPHIC: BarChart3,
  RECAP:       Film,
  AR_ASSET:    Layers,
  IMAGE:       Image,
}

const TYPE_COLOR: Record<VisualAssetType, string> = {
  MAP:         'text-cyan-400',
  VIDEO:       'text-violet-400',
  INFOGRAPHIC: 'text-amber-400',
  RECAP:       'text-blue-400',
  AR_ASSET:    'text-emerald-400',
  IMAGE:       'text-pink-400',
}

// ── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: VisualStatus }) {
  const map: Record<VisualStatus, { label: string; cls: string; Icon: React.ElementType }> = {
    GENERATED:  { label: 'GENERATED',  cls: 'border-emerald-700/50 bg-emerald-950/20 text-emerald-400', Icon: CheckCircle2 },
    PUBLISHED:  { label: 'PUBLISHED',  cls: 'border-emerald-600/60 bg-emerald-950/30 text-emerald-300', Icon: CheckCircle2 },
    QUEUED:     { label: 'QUEUED',     cls: 'border-zinc-700/50 bg-zinc-900/40 text-zinc-500',           Icon: Clock },
    GENERATING: { label: 'GENERATING', cls: 'border-amber-700/50 bg-amber-950/20 text-amber-400',        Icon: Loader2 },
    FAILED:     { label: 'FAILED',     cls: 'border-red-700/50 bg-red-950/20 text-red-400',              Icon: AlertCircle },
  }
  const { label, cls, Icon } = map[status] ?? map.QUEUED
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border text-[8px] font-bold tracking-wider ${cls}`}>
      <Icon className={`w-2 h-2 ${status === 'GENERATING' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  )
}

// ── Provider badge ────────────────────────────────────────────────────────────

const PROVIDER_COLORS: Record<string, string> = {
  DALLE3:       'bg-emerald-950/30 text-emerald-400 border-emerald-800/40',
  GROK_IMAGINE: 'bg-purple-950/30 text-purple-400 border-purple-800/40',
  KLING:        'bg-cyan-950/30 text-cyan-400 border-cyan-800/40',
  RUNWAY:       'bg-blue-950/30 text-blue-400 border-blue-800/40',
  VEO:          'bg-amber-950/30 text-amber-400 border-amber-800/40',
  SORA:         'bg-sky-950/30 text-sky-400 border-sky-800/40',
  QUEUED:       'bg-zinc-900/40 text-zinc-600 border-zinc-800/30',
}

function ProviderBadge({ provider }: { provider: string }) {
  const cls = PROVIDER_COLORS[provider] ?? PROVIDER_COLORS.QUEUED
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded border text-[7px] font-bold tracking-widest ${cls}`}>
      {provider === 'DALLE3' ? 'DALL-E 3' : (provider ?? '').replace('_', ' ')}
    </span>
  )
}

// ── Single visual card ────────────────────────────────────────────────────────

function VisualCard({ asset }: { asset: VisualAsset }) {
  const [imgError, setImgError] = useState(false)
  const Icon = TYPE_ICONS[asset.asset_type] ?? Image
  const iconColor = TYPE_COLOR[asset.asset_type] ?? 'text-zinc-400'

  const isGenerated = asset.status === 'GENERATED' || asset.status === 'PUBLISHED'
  const hasImage    = isGenerated && asset.external_url && !imgError && ['IMAGE', 'INFOGRAPHIC', 'MAP'].includes(asset.asset_type)

  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/60 overflow-hidden flex flex-col group hover:border-zinc-700/60 transition-colors">
      {/* Visual preview area */}
      <div className="relative w-full aspect-video bg-black/60 overflow-hidden">
        {hasImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={asset.external_url!}
            alt={asset.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-zinc-800">
            <Icon className={`w-8 h-8 ${isGenerated ? iconColor : 'text-zinc-800'}`} />
            {asset.status === 'QUEUED' && (
              <span className="text-[9px] text-zinc-700 tracking-widest font-mono">AWAITING PROVIDER KEY</span>
            )}
          </div>
        )}

        {/* Watermark overlay */}
        <div className="absolute bottom-1 right-1">
          <span className="text-[7px] font-bold text-zinc-600/80 bg-black/60 px-1 py-0.5 rounded tracking-wider">
            AI VISUAL
          </span>
        </div>

        {/* Type icon badge */}
        <div className="absolute top-1.5 left-1.5">
          <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-black/70 border border-zinc-800/40 text-[8px] font-bold ${iconColor}`}>
            <Icon className="w-2.5 h-2.5" />
            {asset.asset_type}
          </span>
        </div>
      </div>

      {/* Card body */}
      <div className="p-2.5 flex flex-col gap-1.5 flex-1">
        <div className="text-[10px] text-zinc-300 font-medium line-clamp-2 leading-tight">
          {asset.title}
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <StatusBadge   status={asset.status} />
          <ProviderBadge provider={asset.provider} />
        </div>

        {/* Watermark label */}
        <div className="text-[8px] text-zinc-600 font-mono mt-auto pt-1 border-t border-zinc-800/30">
          {asset.watermark_label}
        </div>
      </div>
    </div>
  )
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatsBar({ stats }: { stats: VisualStats }) {
  return (
    <div className="grid grid-cols-4 gap-2 mb-4">
      {[
        { label: 'GENERATED',   value: stats.generated,         color: 'text-emerald-400' },
        { label: 'QUEUED',      value: stats.queued,            color: 'text-zinc-500' },
        { label: 'TOTAL',       value: stats.total,             color: 'text-zinc-300' },
        { label: '24H',         value: stats.recentlyPublished, color: 'text-amber-400' },
      ].map(({ label, value, color }) => (
        <div key={label} className="rounded border border-zinc-800/60 bg-zinc-950/40 p-2 text-center">
          <div className="text-[8px] text-zinc-600 tracking-widest mb-0.5">{label}</div>
          <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function VisualFeed({ compact = false }: { compact?: boolean }) {
  const [data, setData]       = useState<VisualAPIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchVisuals = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    try {
      const limit = compact ? 6 : 24
      const res   = await fetch(`/api/visuals?limit=${limit}`, { cache: 'no-store' })
      if (res.ok) setData(await res.json() as VisualAPIResponse)
    } catch { /* non-fatal */ } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [compact])

  useSmartPoll(() => fetchVisuals(true), 90_000)

  const visuals = data?.visuals ?? []
  const stats   = data?.stats

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Film className="w-4 h-4 text-violet-400" />
        <span className="tac-label text-violet-300 tracking-widest text-[10px]">VISUAL STORYTELLING</span>
        <span className="text-[8px] text-zinc-600 font-mono ml-1">L4 · AI-GENERATED · FACT-CHECKED</span>
        <button
          onClick={() => fetchVisuals(true)}
          disabled={refreshing}
          className="ml-auto text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Stats bar — only in full mode */}
      {!compact && stats && <StatsBar stats={stats} />}

      {/* Visuals grid */}
      {loading ? (
        <div className="flex items-center gap-2 text-zinc-600 text-[10px] py-4">
          <Loader2 className="w-3 h-3 animate-spin" />
          Loading visuals…
        </div>
      ) : visuals.length === 0 ? (
        <div className="rounded border border-zinc-800/40 bg-zinc-950/30 p-4 text-center text-zinc-600 text-[10px] tracking-wide">
          <Film className="w-5 h-5 mx-auto mb-2 opacity-30" />
          No visuals yet — Governor Layer 4 generates assets for verified intel.
          <br />
          Add <code className="text-zinc-500">OPENAI_API_KEY</code> for DALL-E 3 images.
        </div>
      ) : (
        <div className={`grid gap-3 ${compact ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4'}`}>
          {visuals.map((asset) => (
            <VisualCard key={asset.id ?? asset.title} asset={asset} />
          ))}
        </div>
      )}

      {/* AI disclaimer */}
      <div className="flex items-center gap-1.5 text-[8px] text-zinc-700 pt-1 border-t border-zinc-800/30">
        <Cpu className="w-2.5 h-2.5" />
        All visuals are AI-generated explanatory content. Verified against KG before generation.
        Never published as real footage.
      </div>
    </div>
  )
}
