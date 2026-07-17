/**
 * Server-side Supabase client — SERVER COMPONENTS ONLY.
 * Never import this in Client Components ('use client').
 * Uses next/headers which is App Router server-only.
 */
import { createServerClient as _createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import type { Database } from './types'

function sanitizePublicEnv(value: string): string {
  return value.replace(/%0A/gi, '').replace(/[\r\n\t\s]+/g, '').trim()
}

const supabaseUrl = sanitizePublicEnv(process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'http://localhost:54321')
const supabaseAnonKey = sanitizePublicEnv(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-anon-key')

export async function createServerClient() {
  const cookieStore = await cookies()

  const client = _createServerClient<Database>(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet: { name: string; value: string; options?: Record<string, unknown> }[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        } catch {
          // Called from a Server Component — cookies are read-only, safe to ignore.
        }
      },
    },
  })


  return client
}
