/**
 * GET /api/intel/digest
 *
 * NEXUS Live AI Situation Report Digest — called by Vercel Cron every 30 minutes.
 * Also callable client-side (no auth required; read-only).
 *
 * Returns a structured situation report synthesising:
 *  - Last 24h intel from Supabase (grouped by theater)
 *  - ORACLE-9 threat probabilities
 *  - COMPASS economic cascade metrics
 *  - Verification rate + source diversity
 *  - Top developments (verified, sorted by confidence)
 *  - Overall assessment level
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextResponse } from 'next/server'
import { createServerClient } from '@/lib/supabase-server'
import { computeAllThreats }      from '@/lib/oracle-engine'
import { computeEconomicCascade } from '@/lib/compass-engine'
import { getConflictDay, toDTG }  from '@/lib/conflict-day'
import { AI_AVAILABLE, generateSitrep } from '@/lib/ai-engine'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 120  // AI sitrep generation + Supabase theater aggregation

// ── Types ──────────────────────────────────────────────────────────────────
export interface TheaterDigest {
  name:       string
  count:      number
  verified:   number
  avgConf:    number
  topTitle:   string
  topSource:  string | null
}

export interface IntelDigest {
  ok:             boolean
  conflictDay:    number
  dtg:            string
  generatedAt:    string

  // Intel DB summary
  total24h:       number
  verified24h:    number
  verifyRate:     number   // 0-100
  sourceCount:    number   // distinct sources in last 24h
  theaters:       TheaterDigest[]

  // Top 5 key developments (verified or highest confidence)
  keyDevelopments: {
    title:      string
    theater:    string
    confidence: number
    verified:   boolean
    source:     string | null
    created_at: string
  }[]

  // ORACLE threat summary (top 5 by probability)
  topThreats: {
    label:       string
    domain:      string
    probability: number
    severity:    string
    trend:       string
  }[]

  // COMPASS economics
  economics: {
    brentUsd:             number
    hormuzThroughputMbpd: number
    lloydWarRiskPct:      number
    globalCpiImpulsePp:   number
    dxyMovePp:            number
  }

  // Overall assessment
  assessmentLevel: 'CRITICAL' | 'HIGH' | 'ELEVATED' | 'MODERATE'
  assessmentReason: string

  // AI-generated content (null when OPENAI_API_KEY not set)
  aiNarrative:      string | null
  aiPipelineHealth: import('@/lib/ai-engine').PipelineAssessment | null
  aiAvailable:      boolean
}

// ── Handler ─────────────────────────────────────────────────────────────────
export async function GET() {
  try {
    const conflictDay = getConflictDay()
    const since24h    = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()

    const supabase = await createServerClient()

    // Query last 24h intel
    const { data: rows } = await (supabase as any)
      .from('intel')
      .select('id,title,theater,confidence,source_name,verified,created_at')
      .gte('created_at', since24h)
      .order('confidence', { ascending: false })
      .limit(100)

    const items: any[] = rows ?? []

    // Theater grouping
    const theaterMap = new Map<string, { count: number; verified: number; confSum: number; topTitle: string; topSource: string | null; topConf: number }>()
    const sourceSet  = new Set<string>()

    for (const row of items) {
      const t = (row.theater ?? 'Unknown').trim()
      if (!theaterMap.has(t)) {
        theaterMap.set(t, { count: 0, verified: 0, confSum: 0, topTitle: '', topSource: null, topConf: 0 })
      }
      const entry = theaterMap.get(t)!
      entry.count++
      entry.confSum += row.confidence ?? 0
      if (row.verified) entry.verified++
      if ((row.confidence ?? 0) > entry.topConf) {
        entry.topConf   = row.confidence ?? 0
        entry.topTitle  = row.title ?? ''
        entry.topSource = row.source_name ?? null
      }
      if (row.source_name) sourceSet.add(row.source_name)
    }

    const theaters: TheaterDigest[] = [...theaterMap.entries()]
      .map(([name, d]) => ({
        name,
        count:    d.count,
        verified: d.verified,
        avgConf:  d.count > 0 ? Math.round(d.confSum / d.count) : 0,
        topTitle: d.topTitle,
        topSource: d.topSource,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)

    // Key developments — top 5 verified-first then by confidence
    const keyDevelopments = [...items]
      .sort((a, b) => {
        if (b.verified !== a.verified) return (b.verified ? 1 : 0) - (a.verified ? 1 : 0)
        return (b.confidence ?? 0) - (a.confidence ?? 0)
      })
      .slice(0, 5)
      .map(r => ({
        title:      r.title ?? '',
        theater:    r.theater ?? 'Unknown',
        confidence: r.confidence ?? 0,
        verified:   r.verified ?? false,
        source:     r.source_name ?? null,
        created_at: r.created_at,
      }))

    const total24h    = items.length
    const verified24h = items.filter(r => r.verified).length
    const verifyRate  = total24h > 0 ? Math.round((verified24h / total24h) * 100) : 0

    // ORACLE threats
    const threats = computeAllThreats(conflictDay)
    const topThreats = threats
      .sort((a, b) => b.probability - a.probability)
      .slice(0, 5)
      .map(t => ({
        label:       t.label,
        domain:      t.domain,
        probability: Math.round(t.probability * 100),
        severity:    t.severity,
        trend:       t.trend,
      }))

    // COMPASS economics
    const cascade   = computeEconomicCascade(conflictDay, 'CONTESTED')
    const economics = {
      brentUsd:             cascade.brentUsd,
      hormuzThroughputMbpd: cascade.hormuzThroughputMbpd,
      lloydWarRiskPct:      cascade.lloydWarRiskPct,
      globalCpiImpulsePp:   cascade.globalCpiImpulsePp,
      dxyMovePp:            cascade.dxyMovePp,
    }

    // Assessment level
    const criticalThreats = threats.filter(t => t.severity === 'CRITICAL').length
    const highThreats     = threats.filter(t => t.severity === 'HIGH').length
    const hasCriticalIntel = items.some(r => (r.confidence ?? 0) >= 85 && r.verified)

    let assessmentLevel: IntelDigest['assessmentLevel']
    let assessmentReason: string

    if (criticalThreats >= 3 || hasCriticalIntel) {
      assessmentLevel  = 'CRITICAL'
      assessmentReason = `${criticalThreats} CRITICAL-severity ORACLE threats active; ${verified24h} verified intel items in last 24h.`
    } else if (criticalThreats >= 1 || highThreats >= 4) {
      assessmentLevel  = 'HIGH'
      assessmentReason = `${highThreats} HIGH-severity threats across ${theaterMap.size} active theaters. Monitoring.`
    } else if (total24h >= 10 || highThreats >= 2) {
      assessmentLevel  = 'ELEVATED'
      assessmentReason = `${total24h} intel items processed; ${theaterMap.size} theaters active. Elevated vigilance required.`
    } else {
      assessmentLevel  = 'MODERATE'
      assessmentReason = `${total24h} items ingested. No immediate CRITICAL threats. Continue monitoring.`
    }

    // AI narrative — non-blocking, degrades gracefully when OpenAI is unavailable
    const aiNarrative = await generateSitrep({
      conflictDay,
      assessmentLevel,
      topDevelopments: keyDevelopments.map(d => `[${d.theater}] ${d.title}`),
      topThreats: topThreats.map(t => ({ label: t.label, probability: t.probability, severity: t.severity })),
      brentUsd:         economics.brentUsd,
      verifiedCount:    verified24h,
      totalIntel24h:    total24h,
      activeTheaters:   theaters.map(t => t.name),
    }).catch(() => null)
    const aiPipelineHealth = null

    const digest: IntelDigest = {
      ok: true,
      conflictDay,
      dtg:            toDTG(conflictDay),
      generatedAt:    new Date().toISOString(),
      total24h,
      verified24h,
      verifyRate,
      sourceCount:    sourceSet.size,
      theaters,
      keyDevelopments,
      topThreats,
      economics,
      assessmentLevel,
      assessmentReason,
      aiNarrative:      aiNarrative ?? null,
      aiPipelineHealth: aiPipelineHealth ?? null,
      aiAvailable:      AI_AVAILABLE,
    }

    return NextResponse.json(digest, {
      headers: { 'Cache-Control': 'no-store' },
    })
  } catch (err: any) {
    return NextResponse.json({
      ok: false,
      error: String(err?.message ?? err),
      conflictDay: getConflictDay(),
      generatedAt: new Date().toISOString(),
    }, { status: 500 })
  }
}
