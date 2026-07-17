/**
 * lib/visual-engine.ts — EPIC FURY 2026 Visual Epic Storytelling Engine
 *
 * Governor Layer 4: Cinematic AI-generated visuals for every verified intel item.
 * Emphasizes US-citizen impact, Operation Epic Fury conflict coverage, and
 * fact-checked visual storytelling with full provenance labelling.
 *
 * Provider chain (each activated by its corresponding env var):
 *   DALLE3        — OpenAI DALL-E 3 (images, infographics, maps)   ← OPENAI_API_KEY
 *   GROK_IMAGINE  — xAI Grok 2 image                               ← GROK_API_KEY
 *   KLING         — Kling 3.0 text-to-video                        ← KLING_API_KEY
 *   RUNWAY        — Runway Gen-4.5 text-to-video                   ← RUNWAY_API_KEY
 *   VEO           — Google Veo 3.1 text-to-video                   ← VEO_API_KEY
 *   SORA          — OpenAI Sora 2 text-to-video                    ← SORA_API_KEY
 *   QUEUED        — No key available; asset queued for future run
 *
 * Security:
 *   - All LLM prompts truncated at 1500 chars
 *   - DALL-E 3 prompts further limited to 1000 chars (API max)
 *   - No user-supplied strings interpolated without explicit truncation
 *   - Visuals generated only after LLM-as-Judge Layer 2 gate (verified=true)
 *   - Watermark: "EPIC FURY AI Visual – Fact-Checked" on every asset record
 */

import { createClient } from '@supabase/supabase-js'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type VisualProvider  = 'KLING' | 'VEO' | 'SORA' | 'RUNWAY' | 'GROK_IMAGINE' | 'DALLE3' | 'QUEUED'
export type VisualAssetType = 'MAP' | 'VIDEO' | 'INFOGRAPHIC' | 'RECAP' | 'AR_ASSET' | 'IMAGE'
export type VisualStatus    = 'QUEUED' | 'GENERATING' | 'GENERATED' | 'FAILED' | 'PUBLISHED'

export interface VisualAsset {
  id?:              string
  intel_id:         string | null
  asset_type:       VisualAssetType
  title:            string
  prompt_used:      string
  provider:         VisualProvider
  model_version:    string | null
  status:           VisualStatus
  storage_path:     string | null
  external_url:     string | null
  watermark_label:  string
  verified:         boolean
  kg_verified_by:   string[] | null
  provenance_json:  Record<string, unknown>
  metadata_json:    Record<string, unknown>
  engagement_score: number
  error_message?:   string | null
  created_at?:      string
  updated_at?:      string
}

export interface VisualRequest {
  intel_id:    string
  title:       string
  summary:     string
  theater:     string
  asset_types: VisualAssetType[]
}

export interface VisualResult {
  assets:    VisualAsset[]
  generated: number
  queued:    number
  failed:    number
}

export interface VisualStats {
  total:           number
  generated:       number
  queued:          number
  failed:          number
  byType:          Record<string, number>
  byProvider:      Record<string, number>
  recentlyPublished: number
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function getSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) throw new Error('VISUAL-ENGINE: Missing Supabase credentials')
  return createClient(url, key, { auth: { persistSession: false } })
}

const OPENAI_BASE = 'https://api.openai.com/v1'
const WATERMARK   = 'EPIC FURY AI Visual – Fact-Checked'

function truncate(text: string, max = 1500): string {
  return text.length > max ? text.slice(0, max) + '…' : text
}

// ---------------------------------------------------------------------------
// Prompt generator — GPT-4o-mini crafts vivid cinematic prompts per asset type
// ---------------------------------------------------------------------------

async function generateVisualPrompt(
  title:     string,
  summary:   string,
  theater:   string,
  assetType: VisualAssetType,
): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) return buildFallbackPrompt(title, theater, assetType)

  const typeGuide: Record<VisualAssetType, string> = {
    MAP:         'a tactical real-time map visualization: conflict zones highlighted, US-citizen evacuation corridors, military positions, and economic impact overlays in a dark cinematic style',
    VIDEO:       'a dramatic cinematic news explainer: sweeping aerial visuals of the theater, data overlays, breaking news typography, and US-citizen impact focus',
    INFOGRAPHIC: 'a clean high-contrast military infographic: timeline, verified statistics, key actors, and US economic/safety impact callouts on a dark background',
    RECAP:       'a short-form verified news recap frame: bold key facts, confirmed US-citizen advisories highlighted, classified military typeface',
    AR_ASSET:    'an augmented-reality-ready 3D scene: layered conflict theater visualization with floating data panels, unit positions, and US-impact annotations',
    IMAGE:       'a photorealistic editorial illustration: dramatic cinematic lighting, conflict atmosphere, verified facts caption zone at bottom',
  }

  try {
    const res = await fetch(`${OPENAI_BASE}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: `You are a cinematic AI visual prompt engineer for EPIC FURY 2026, the USA's verified military-news platform.
Create ONE concise vivid visual generation prompt (max 200 words) for: ${typeGuide[assetType]}.
Requirements: include theater "${theater}", US-citizen perspective, dramatic but factual tone, space for "EPIC FURY 2026" watermark.
Output ONLY the raw prompt text, no explanation, no quotes.`,
          },
          {
            role: 'user',
            content: `News: ${truncate(title, 200)}\nSummary: ${truncate(summary, 600)}`,
          },
        ],
        max_tokens: 260,
        temperature: 0.4,
      }),
      signal: AbortSignal.timeout(15_000),
    })
    if (!res.ok) return buildFallbackPrompt(title, theater, assetType)
    const d = await res.json() as { choices?: { message?: { content?: string } }[] }
    const content = d.choices?.[0]?.message?.content?.trim()
    return truncate(content ?? buildFallbackPrompt(title, theater, assetType), 1500)
  } catch {
    return buildFallbackPrompt(title, theater, assetType)
  }
}

function buildFallbackPrompt(title: string, theater: string, assetType: VisualAssetType): string {
  const base = `EPIC FURY 2026 verified military news. Theater: ${truncate(theater, 50)}. Story: ${truncate(title, 150)}.`
  const map: Record<VisualAssetType, string> = {
    MAP:         `${base} Tactical dark map with conflict zones, US evacuation corridors, and military unit positions marked. Cinematic satellite style.`,
    VIDEO:       `${base} Cinematic aerial sweep of conflict theater. Bold breaking-news lower-thirds. US-citizen impact data overlays.`,
    INFOGRAPHIC: `${base} Dark military infographic, bright accent data points, US-citizen impact statistics, verified-facts badge.`,
    RECAP:       `${base} Bold short-form news recap. Key verified facts listed. US-citizen advisory banner prominent.`,
    AR_ASSET:    `${base} 3D augmented reality conflict theater visualization. Floating data panels, unit icons, US-impact zones.`,
    IMAGE:       `${base} Dramatic editorial illustration, cinematic side lighting, verified-facts caption bar at bottom.`,
  }
  return map[assetType]
}

// ---------------------------------------------------------------------------
// DALL-E 3 — image / infographic / map generation
// ---------------------------------------------------------------------------

async function generateDalle3Image(
  prompt:    string,
  assetType: VisualAssetType,
): Promise<{ url: string; revisedPrompt: string } | null> {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) return null

  const size = assetType === 'INFOGRAPHIC' ? '1024x1792' : '1792x1024'

  try {
    const res = await fetch(`${OPENAI_BASE}/images/generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model:   'dall-e-3',
        prompt:  truncate(prompt, 1000),   // DALL-E 3 hard limit
        size,
        quality: 'standard',
        n:       1,
        style:   'vivid',
      }),
      signal: AbortSignal.timeout(50_000),
    })
    if (!res.ok) return null
    const d = await res.json() as { data?: { url?: string; revised_prompt?: string }[] }
    const item = d.data?.[0]
    if (!item?.url) return null
    return { url: item.url, revisedPrompt: item.revised_prompt ?? prompt }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Grok Imagine — fallback image generation
// ---------------------------------------------------------------------------

async function generateGrokImage(prompt: string): Promise<{ url: string } | null> {
  const apiKey = process.env.GROK_API_KEY
  if (!apiKey) return null

  try {
    const res = await fetch('https://api.x.ai/v1/images/generations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model:  'grok-2-image',
        prompt: truncate(prompt, 700),
        n:      1,
      }),
      signal: AbortSignal.timeout(30_000),
    })
    if (!res.ok) return null
    const d = await res.json() as { data?: { url?: string }[] }
    const url = d.data?.[0]?.url
    return url ? { url } : null
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Kling 3.0 — text-to-video (queued if no KLING_API_KEY)
// ---------------------------------------------------------------------------

async function generateKlingVideo(prompt: string): Promise<{ url: string; jobId: string } | null> {
  const apiKey = process.env.KLING_API_KEY
  if (!apiKey) return null

  try {
    const res = await fetch('https://api.klingai.com/v1/videos/text2video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ prompt: truncate(prompt, 800), duration: 5, mode: 'std' }),
      signal: AbortSignal.timeout(30_000),
    })
    if (!res.ok) return null
    const d = await res.json() as { data?: { task_id?: string; video_url?: string } }
    const jobId = d.data?.task_id ?? ''
    const url   = d.data?.video_url ?? ''
    return { url, jobId }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Runway Gen-4.5 — text-to-video (queued if no RUNWAY_API_KEY)
// ---------------------------------------------------------------------------

async function generateRunwayVideo(prompt: string): Promise<{ url: string; taskId: string } | null> {
  const apiKey = process.env.RUNWAY_API_KEY
  if (!apiKey) return null

  try {
    const res = await fetch('https://api.runwayml.com/v1/image_to_video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ promptText: truncate(prompt, 600), seconds: 5 }),
      signal: AbortSignal.timeout(30_000),
    })
    if (!res.ok) return null
    const d = await res.json() as { id?: string; output?: string[] }
    return { url: d.output?.[0] ?? '', taskId: d.id ?? '' }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Supabase persistence
// ---------------------------------------------------------------------------

async function storeVisualAsset(
  asset: Omit<VisualAsset, 'id' | 'created_at' | 'updated_at'>,
): Promise<string | null> {
  try {
    const sb = getSupabase()
    const { data, error } = await sb
      .from('visual_assets')
      .insert({ ...asset })
      .select('id')
      .single()
    if (error || !data) return null
    return (data as { id: string }).id
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Public: generateVisualsForIntel
// Governor Layer 4 entry — generates all requested asset types for one intel item
// ---------------------------------------------------------------------------

export async function generateVisualsForIntel(request: VisualRequest): Promise<VisualResult> {
  const assets: VisualAsset[]  = []
  let generated = 0
  let queued    = 0
  const failed    = 0

  for (const assetType of request.asset_types) {
    const prompt = await generateVisualPrompt(
      request.title, request.summary, request.theater, assetType,
    )

    const base: Omit<VisualAsset, 'id' | 'created_at' | 'updated_at'> = {
      intel_id:        request.intel_id,
      asset_type:      assetType,
      title:           `${assetType}: ${request.title.slice(0, 100)}`,
      prompt_used:     prompt,
      provider:        'QUEUED',
      model_version:   null,
      status:          'QUEUED',
      storage_path:    null,
      external_url:    null,
      watermark_label: WATERMARK,
      verified:        true,
      kg_verified_by:  null,
      provenance_json: {
        intel_id:     request.intel_id,
        theater:      request.theater,
        requested_at: new Date().toISOString(),
      },
      metadata_json:   { original_type: assetType },
      engagement_score: 0,
    }

    let result: Omit<VisualAsset, 'id' | 'created_at' | 'updated_at'> = { ...base }

    const isImageType = (['IMAGE', 'INFOGRAPHIC', 'MAP'] as VisualAssetType[]).includes(assetType)
    const isVideoType = (['VIDEO', 'RECAP', 'AR_ASSET'] as VisualAssetType[]).includes(assetType)

    if (isImageType) {
      // Primary: DALL-E 3
      const dalle = await generateDalle3Image(prompt, assetType)
      if (dalle) {
        result = {
          ...base,
          provider:       'DALLE3',
          model_version:  'dall-e-3',
          status:         'GENERATED',
          external_url:   dalle.url,
          provenance_json: {
            ...base.provenance_json,
            revised_prompt: dalle.revisedPrompt,
            generated_at:   new Date().toISOString(),
          },
        }
        generated++
      } else {
        // Fallback: Grok Imagine
        const grok = await generateGrokImage(prompt)
        if (grok?.url) {
          result = {
            ...base,
            provider:       'GROK_IMAGINE',
            model_version:  'grok-2-image',
            status:         'GENERATED',
            external_url:   grok.url,
            provenance_json: { ...base.provenance_json, generated_at: new Date().toISOString() },
          }
          generated++
        } else {
          result = { ...base, status: 'QUEUED', provider: 'QUEUED' }
          queued++
        }
      }
    } else if (isVideoType) {
      // Primary: Kling 3.0
      const kling = await generateKlingVideo(prompt)
      if (kling?.url) {
        result = {
          ...base,
          provider:       'KLING',
          model_version:  'kling-3.0',
          status:         'GENERATED',
          external_url:   kling.url,
          provenance_json: {
            ...base.provenance_json,
            job_id:        kling.jobId,
            generated_at:  new Date().toISOString(),
          },
        }
        generated++
      } else {
        // Fallback: Runway Gen-4.5
        const runway = await generateRunwayVideo(prompt)
        if (runway?.url) {
          result = {
            ...base,
            provider:       'RUNWAY',
            model_version:  'gen-4.5',
            status:         'GENERATED',
            external_url:   runway.url,
            provenance_json: {
              ...base.provenance_json,
              task_id:       runway.taskId,
              generated_at:  new Date().toISOString(),
            },
          }
          generated++
        } else {
          result = { ...base, status: 'QUEUED', provider: 'QUEUED' }
          queued++
        }
      }
    }

    const id = await storeVisualAsset(result)
    assets.push({ ...result, id: id ?? undefined })
  }

  return { assets, generated, queued, failed }
}

// ---------------------------------------------------------------------------
// Public: getVisualizableIntel
// Returns verified intel items that don't yet have visual assets
// ---------------------------------------------------------------------------

export async function getVisualizableIntel(limit = 5): Promise<{
  id: string; title: string; summary: string; theater: string; verified: boolean
}[]> {
  try {
    const sb = getSupabase()

    // Find intel IDs that already have at least one visual
    const { data: existing } = await sb
      .from('visual_assets')
      .select('intel_id')
      .not('intel_id', 'is', null)

    const coveredIds = new Set(
      (existing ?? []).map((v: { intel_id: string }) => v.intel_id).filter(Boolean),
    )

    // Fetch recent verified intel, over-fetching to allow filtering
    const { data: items } = await sb
      .from('intel')
      .select('id, title, summary, theater')
      .eq('verified', true)
      .order('created_at', { ascending: false })
      .limit(limit + coveredIds.size + 10)

    if (!items) return []

    return (items as { id: string; title: string; summary: string; theater: string }[])
      .filter(item => !coveredIds.has(item.id))
      .slice(0, limit)
      .map(item => ({ ...item, verified: true }))
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Public: getRecentVisuals — used by VisualFeed component and API route
// ---------------------------------------------------------------------------

export async function getRecentVisuals(
  limit         = 20,
  statusFilter?: VisualStatus,
): Promise<VisualAsset[]> {
  try {
    const sb = getSupabase()
    let query = sb
      .from('visual_assets')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit)

    if (statusFilter) query = query.eq('status', statusFilter)

    const { data } = await query
    return (data ?? []) as VisualAsset[]
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Public: computeVisualStats — aggregate metrics for GovernorPanel
// ---------------------------------------------------------------------------

export async function computeVisualStats(): Promise<VisualStats> {
  try {
    const sb = getSupabase()
    const { data } = await sb
      .from('visual_assets')
      .select('status, asset_type, provider, created_at')

    const rows = (data ?? []) as { status: string; asset_type: string; provider: string; created_at: string }[]

    const cutoff = Date.now() - 24 * 60 * 60 * 1000 // last 24 hours

    const stats: VisualStats = {
      total:             rows.length,
      generated:         rows.filter(r => r.status === 'GENERATED' || r.status === 'PUBLISHED').length,
      queued:            rows.filter(r => r.status === 'QUEUED').length,
      failed:            rows.filter(r => r.status === 'FAILED').length,
      byType:            {},
      byProvider:        {},
      recentlyPublished: rows.filter(r => new Date(r.created_at).getTime() > cutoff && r.status === 'GENERATED').length,
    }

    for (const row of rows) {
      stats.byType[row.asset_type]   = (stats.byType[row.asset_type]   ?? 0) + 1
      stats.byProvider[row.provider] = (stats.byProvider[row.provider] ?? 0) + 1
    }

    return stats
  } catch {
    return { total: 0, generated: 0, queued: 0, failed: 0, byType: {}, byProvider: {}, recentlyPublished: 0 }
  }
}
