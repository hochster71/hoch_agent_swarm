import { NextRequest, NextResponse } from 'next/server'
import { requireSubscriber } from '@/lib/api-auth'

export const maxDuration = 30 // seconds — Vercel Pro; ignored on Hobby (10s default)

// ── Per-IP rate limiter — 20 requests per 5 minutes ─────────────────────────
// TTS calls ElevenLabs (costs money) — prevent credit abuse from public endpoint.
const TTS_RL = new Map<string, { count: number; resetAt: number }>()
const TTS_RL_MAX  = 20
const TTS_RL_WINDOW = 5 * 60_000 // 5 minutes

function checkTTSRateLimit(ip: string): boolean {
  const now = Date.now()
  const entry = TTS_RL.get(ip)
  if (!entry || now > entry.resetAt) {
    TTS_RL.set(ip, { count: 1, resetAt: now + TTS_RL_WINDOW })
    return true
  }
  entry.count++
  return entry.count <= TTS_RL_MAX
}

// ── Server-side circuit-breaker ─────────────────────────────────────────────
// Only block on auth failures (401/403) — transient errors (timeout, 503) do not
// trip the breaker so individual segment retries can succeed.
let elFailedUntil = 0
const CIRCUIT_BREAK_MS = 5 * 60 * 1000 // 5 minutes (auth failures only)

export async function POST(req: NextRequest) {
  const deny = await requireSubscriber(req)
  if (deny) return deny

  // Per-IP rate limit — prevent ElevenLabs credit abuse
  const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? req.headers.get('x-real-ip') ?? 'unknown'
  if (!checkTTSRateLimit(ip)) {
    return NextResponse.json({ error: 'Too many TTS requests — slow down', fallback: 'webspeech' }, { status: 429 })
  }
  let text: string, voiceId: string
  try {
    const body = (await req.json()) as { text?: unknown; voiceId?: unknown }
    text    = typeof body.text    === 'string' ? body.text    : ''
    voiceId = typeof body.voiceId === 'string' ? body.voiceId : ''
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  try {
  const apiKey = process.env.ELEVENLABS_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: 'ELEVENLABS_API_KEY not configured', fallback: 'webspeech' }, { status: 503 })
  }

  if (!text || !voiceId) {
    return NextResponse.json({ error: 'Missing text or voiceId' }, { status: 400 })
  }

  // Circuit breaker — skip upstream call if recently failed
  if (Date.now() < elFailedUntil) {
    return NextResponse.json(
      { error: 'ElevenLabs temporarily unavailable', fallback: 'webspeech', retryAfter: Math.ceil((elFailedUntil - Date.now()) / 1000) },
      { status: 503 },
    )
  }

  // Truncate to 5000 chars — generous for full anchor broadcast scripts on Vercel Pro.
  const safeText = text.slice(0, 5000)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 25000)

  const upstream = await (async () => {
    try {
      return await fetch(
        `https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(voiceId)}`,
        {
          method: 'POST',
          headers: {
            'xi-api-key': apiKey,
            'Content-Type': 'application/json',
            Accept: 'audio/mpeg',
          },
          body: JSON.stringify({
            text: safeText,
            model_id: 'eleven_turbo_v2_5',  // near-realtime, fits Vercel Hobby 10s limit
            voice_settings: { stability: 0.6, similarity_boost: 0.8, style: 0.35, use_speaker_boost: true },
          }),
          signal: controller.signal,
        },
      )
    } finally {
      clearTimeout(timeoutId)
    }
  })()

  if (!upstream.ok) {
    const err = await upstream.text().catch(() => '')
    // Trip circuit breaker only on auth failures (key wrong/expired) — not transient errors
    // Only 401 trips the breaker (invalid API key). 403 = voice not on plan — transient.
    if (upstream.status === 401) {
      elFailedUntil = Date.now() + CIRCUIT_BREAK_MS
      console.warn(`[tts] ElevenLabs 401 — circuit breaker tripped for 5 min (bad API key)`)
    }
    return NextResponse.json({ error: `ElevenLabs error ${upstream.status}`, detail: err, fallback: 'webspeech' }, { status: upstream.status })
  }

  // Success — reset circuit breaker
  elFailedUntil = 0

  const audio = await upstream.arrayBuffer()
  return new NextResponse(audio, {
    headers: {
      'Content-Type': 'audio/mpeg',
      'Cache-Control': 'no-store',
      'X-Voice-Id': voiceId,
    },
  })
  } catch (err) {
    // Abort or network failure — do NOT trip circuit breaker, let next request retry
    console.error('[tts] network error / timeout', err)
    return NextResponse.json({ error: 'TTS service unreachable', fallback: 'webspeech' }, { status: 503 })
  }
}

// Only POST is supported
export async function GET() {
  return NextResponse.json({ error: 'Use POST' }, { status: 405 })
}
