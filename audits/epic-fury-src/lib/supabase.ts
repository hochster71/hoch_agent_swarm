/**
 * Browser-side Supabase client (safe to import in Client Components).
 * Singleton pattern avoids creating multiple GoTrueClient instances.
 *
 * Uses @supabase/ssr's cookie-based browser client so the PKCE code_verifier
 * and session live in COOKIES (not localStorage). This is required so the
 * server-side /auth/callback route and Edge middleware (both @supabase/ssr)
 * can read the same session — otherwise magic-link exchange fails and the
 * user is bounced back to /login in a loop.
 */
import { createBrowserClient as createSSRBrowserClient } from '@supabase/ssr'
import type { Database } from './types'

function sanitizePublicEnv(value: string): string {
  // Remove accidental URL-encoded newlines and stray whitespace from env values.
  return value.replace(/%0A/gi, '').replace(/[\r\n\t\s]+/g, '').trim()
}

const _rawUrl = sanitizePublicEnv(process.env.NEXT_PUBLIC_SUPABASE_URL ?? '')
const _rawKey = sanitizePublicEnv(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '')

/** True when real Supabase credentials are present — gate realtime subscriptions on this. */
export const SUPABASE_CONFIGURED =
  !!_rawUrl &&
  !_rawUrl.includes('localhost') &&
  !_rawUrl.includes('127.0.0.1') &&
  !!_rawKey &&
  _rawKey !== 'placeholder-anon-key'

// Use real URL when configured; fall back to a clearly-invalid placeholder that
// fails loudly at runtime instead of silently hitting localhost:54321.
const supabaseUrl  = SUPABASE_CONFIGURED ? _rawUrl  : 'https://not-configured.supabase.co'
const supabaseAnonKey = SUPABASE_CONFIGURED ? _rawKey : 'not-configured'

type BrowserClient = ReturnType<typeof createSSRBrowserClient<Database>>

declare global {
  // eslint-disable-next-line no-var
  var __EPIC_FURY_SUPABASE_BROWSER__: BrowserClient | undefined
}

let _browserClient: BrowserClient | null = globalThis.__EPIC_FURY_SUPABASE_BROWSER__ ?? null

export function createBrowserClient() {
  if (!_browserClient) {
    _browserClient = createSSRBrowserClient<Database>(supabaseUrl, supabaseAnonKey, {
      realtime: {
        params: {
          eventsPerSecond: 10,
        },
      },
    })
    
    
    globalThis.__EPIC_FURY_SUPABASE_BROWSER__ = _browserClient
  }
  return _browserClient
}


