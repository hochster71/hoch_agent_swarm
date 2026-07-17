'use client'

/**
 * app/login/page.tsx
 *
 * Sign-in page — Supabase magic-link + Google OAuth.
 * Reads `?next=` query param and redirects there after successful auth.
 * Referenced by SubscriberGate and the upgrade paywall overlay.
 */

import { useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'
import { Shield, Mail, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react'

function isGoogleOauthEnabledFromEnv(): boolean {
  const raw = (process.env.NEXT_PUBLIC_ENABLE_GOOGLE_OAUTH ?? '').trim().toLowerCase()
  return raw === '1' || raw === 'true' || raw === 'yes' || raw === 'on'
}

function buildAuthCallbackUrl(next: string): string {
  const configured = (process.env.NEXT_PUBLIC_SITE_URL ?? process.env.NEXT_PUBLIC_APP_URL ?? '')
    .trim()
    .replace(/\/$/, '')
  const runtime =
    typeof window !== 'undefined' ? window.location.origin.replace(/\/$/, '') : ''

  // In the native app / local dev the runtime origin can be localhost, which
  // Supabase will reject and fall back to its Site URL. Prefer the configured
  // production origin whenever the runtime origin is empty or localhost.
  const isLocal = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:|$)/i.test(runtime)
  const base = !runtime || isLocal ? configured || runtime : runtime

  if (!base) return `/auth/callback?next=${encodeURIComponent(next)}`

  return `${base}/auth/callback?next=${encodeURIComponent(next)}`
}

// ── Google logo SVG (inline — no external dependency) ───────────────────────
function GoogleIcon() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}

function LoginContent() {
  const searchParams = useSearchParams()
  const next = searchParams.get('next') ?? '/dashboard'
  const authError = searchParams.get('error')

  const [email, setEmail]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [oauthLoading, setOAuth]    = useState(false)
  const [googleEnabled, setGoogleEnabled] = useState(isGoogleOauthEnabledFromEnv())
  const [sent, setSent]             = useState(false)
  const [error, setError]           = useState<string | null>(authError ? 'Sign-in link expired or invalid — try again.' : null)

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault()
    if (!SUPABASE_CONFIGURED) {
      setError('Authentication is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in your Vercel environment variables.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const supabase = createBrowserClient()
      const { error: sbErr } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: buildAuthCallbackUrl(next),
        },
      })
      if (sbErr) setError(sbErr.message)
      else setSent(true)
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogle() {
    if (!googleEnabled) {
      setError('Google sign-in is disabled. Use magic link below.')
      return
    }

    if (!SUPABASE_CONFIGURED) {
      setError('Authentication is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in Vercel environment variables.')
      return
    }
    setOAuth(true)
    try {
      const supabase = createBrowserClient()
      const { error: oauthErr } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: buildAuthCallbackUrl(next),
        },
      })
      if (oauthErr) {
        const msg = oauthErr.message ?? 'Unable to start Google sign-in.'
        if (/unsupported provider|provider is not enabled/i.test(msg)) {
          setGoogleEnabled(false)
          setError('Google sign-in is not enabled for this project. Use magic link below or enable Google provider in Supabase Auth settings.')
        } else {
          setError(msg)
        }
        setOAuth(false)
      }
    } catch {
      setError('Unable to start Google sign-in. Please try magic link instead.')
      setOAuth(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-red-950/60 border border-red-800/50 rounded-xl mb-4">
            <Shield className="w-6 h-6 text-red-400" />
          </div>
          <h1 className="text-white font-black text-xl tracking-tight">EPIC FURY NEXUS</h1>
          <p className="text-zinc-500 text-[10px] mt-1 font-mono tracking-[0.2em] uppercase">
            Sign In or Create Account
          </p>
        </div>

        {!SUPABASE_CONFIGURED && (
          <div className="mb-4 flex items-start gap-3 bg-amber-950/60 border border-amber-700/50 rounded-xl px-4 py-3">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-amber-300 text-[11px] leading-relaxed font-mono">
              <span className="font-bold uppercase tracking-widest block mb-1">Auth Not Configured</span>
              Set <code className="bg-amber-900/50 px-1 rounded">NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
              <code className="bg-amber-900/50 px-1 rounded">NEXT_PUBLIC_SUPABASE_ANON_KEY</code>{' '}
              in Vercel Environment Variables, then redeploy.
            </p>
          </div>
        )}

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          {sent ? (
            /* ── Success state ── */
            <div className="px-6 py-10 text-center space-y-4">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <div>
                <p className="text-white font-semibold text-sm">Check your inbox</p>
                <p className="text-zinc-400 text-xs mt-1.5 leading-relaxed">
                  Sign-in link sent to{' '}
                  <span className="text-zinc-200 font-mono">{email}</span>.
                  <br />Click the link — it expires in 1 hour.
                </p>
              </div>
              <button
                onClick={() => { setSent(false); setError(null) }}
                className="text-zinc-600 hover:text-zinc-400 text-xs underline underline-offset-2 transition-colors"
              >
                Use a different email
              </button>
            </div>
          ) : (
            <>
              {/* ── Google OAuth ── */}
              {googleEnabled ? (
                <div className="px-6 pt-6 pb-4">
                  <button
                    onClick={handleGoogle}
                    disabled={oauthLoading}
                    className="w-full flex items-center justify-center gap-2.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white text-sm font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {oauthLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GoogleIcon />}
                    Continue with Google
                  </button>
                </div>
              ) : (
                <div className="px-6 pt-6 pb-4">
                  <p className="text-amber-400/90 text-xs text-center leading-relaxed">
                    Google sign-in is disabled. Continue with magic link.
                  </p>
                </div>
              )}

              {/* Divider */}
              <div className="px-6 flex items-center gap-3 mb-4">
                <div className="flex-1 h-px bg-zinc-800" />
                <span className="text-zinc-600 text-[10px] font-mono tracking-widest">OR</span>
                <div className="flex-1 h-px bg-zinc-800" />
              </div>

              {/* ── Magic link form ── */}
              <form onSubmit={handleMagicLink} className="px-6 pb-6 space-y-3">
                <p className="text-zinc-500 text-xs leading-relaxed -mt-1">
                  New here? No password needed — enter your email and we&apos;ll send a secure link.
                  Your account is created automatically on first sign-in.
                </p>
                <div>
                  <label className="block text-[10px] text-zinc-500 font-mono tracking-[0.2em] uppercase mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 pointer-events-none" />
                    <input
                      type="email"
                      required
                      autoComplete="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="your@email.com"
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-cyan-600 focus:ring-1 focus:ring-cyan-600/30 transition-colors"
                    />
                  </div>
                </div>

                {error && (
                  <p className="text-red-400 text-xs leading-relaxed">{error}</p>
                )}

                <button
                  type="submit"
                  disabled={loading || !email}
                  className="w-full bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 disabled:opacity-40 text-black text-sm font-bold py-2.5 rounded-lg transition-colors"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Sending…
                    </span>
                  ) : (
                    'Email me a sign-in link'
                  )}
                </button>
              </form>
            </>
          )}
        </div>

        {/* Footer links */}
        <div className="text-center mt-4 space-y-1.5">
          <p className="text-zinc-700 text-xs">
            See plans &amp; pricing?{' '}
            <a href="/upgrade" className="text-cyan-600 hover:text-cyan-400 underline underline-offset-2 transition-colors">
              View Pro plans →
            </a>
          </p>
          <p className="text-zinc-700 text-xs">
            <a href="/dashboard" className="hover:text-zinc-500 transition-colors">
              ← Back to dashboard
            </a>
          </p>
        </div>

      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-zinc-600 animate-spin" />
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  )
}
