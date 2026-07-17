/**
 * app/auth/callback/route.ts
 *
 * Handles the redirect from Supabase after a sign-in email is clicked.
 *
 * TWO BUGS lived here, both of which produced a login that "succeeds" but leaves the user
 * logged out:
 *
 * 1. LINK FORMAT. Supabase sends TWO magic-link formats and this route must handle both:
 *      PKCE:        /auth/callback?code=...              -> exchangeCodeForSession
 *      OTP / magic: /auth/callback?token_hash=&type=...  -> verifyOtp   (the DEFAULT)
 *    Handling only `code` sent every default magic link to /login = an email loop.
 *
 * 2. COOKIE DELIVERY. The session cookies MUST be written onto the exact NextResponse we
 *    return. The previous version set them via the `next/headers` cookie store and then
 *    returned a SEPARATE NextResponse.redirect(). In a Route Handler, cookies set on the
 *    next/headers store do NOT reliably attach to a hand-constructed redirect response —
 *    so the auth exchange succeeded server-side, but the browser received a redirect with
 *    NO session cookie. Every page after that saw the user as logged out. For the founder
 *    (hard-coded full access) that surfaced as an unexpected PAYWALL.
 *
 * The fix for #2: build the redirect response FIRST, bind the Supabase client's cookie
 * writer to THAT response's cookies, then return it.
 */
import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import type { EmailOtpType } from '@supabase/supabase-js'

export async function GET(req: NextRequest) {
  const { searchParams, origin } = new URL(req.url)

  const code = searchParams.get('code')
  const token_hash = searchParams.get('token_hash')
  const type = searchParams.get('type') as EmailOtpType | null
  const next = searchParams.get('next') ?? '/dashboard'
  const safeNext = next.startsWith('/') && !next.startsWith('//') ? next : '/dashboard'

  const configuredOrigin = (process.env.NEXT_PUBLIC_APP_URL ?? process.env.NEXT_PUBLIC_SITE_URL ?? '')
    .trim()
    .replace(/\/$/, '')
  const base =
    origin.includes('localhost') || origin.includes('127.0.0.1') ? configuredOrigin || origin : origin

  // Build the SUCCESS response up front so the Supabase client can write session cookies
  // directly onto it. This is the whole fix for the "logged in but no cookie" bug.
  const successResponse = NextResponse.redirect(`${base}${safeNext}`)

  const failResponse = (reason: string) => {
    console.error('[auth/callback] failed:', reason)
    return NextResponse.redirect(`${base}/login?error=auth_failed`)
  }

  const errParam = searchParams.get('error_description') || searchParams.get('error')
  if (errParam && !code && !token_hash) return failResponse(`supabase: ${errParam}`)
  if (!code && !(token_hash && type)) return failResponse('no code and no token_hash+type')

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return req.cookies.getAll()
        },
        setAll(cookiesToSet: { name: string; value: string; options?: Record<string, unknown> }[]) {
          // Write onto the response we will RETURN. This is what actually delivers the
          // session cookie to the browser.
          cookiesToSet.forEach(({ name, value, options }) =>
            successResponse.cookies.set(name, value, options as Parameters<typeof successResponse.cookies.set>[2]),
          )
        },
      },
    },
  )

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (error) return failResponse(`exchangeCodeForSession: ${error.message}`)
    return successResponse
  }

  const { error } = await supabase.auth.verifyOtp({ type: type!, token_hash: token_hash! })
  if (error) return failResponse(`verifyOtp: ${error.message}`)
  return successResponse
}
