'use client'

/**
 * AccessGate.tsx
 *
 * Wraps subscriber or admin-only content.
 * For free/unauthenticated users: renders NOTHING — no lock UI, no CTA,
 * no visual hint that the content exists at all.
 * Only authenticated users with the correct role see content.
 */

import { useEffect, useState, ReactNode } from 'react'
import { createBrowserClient } from '@/lib/supabase'
import { getEntitlement } from '@/lib/entitlements'

type Tier = 'subscriber' | 'admin'
type Role = 'admin' | 'subscriber' | 'free' | 'loading'

interface AccessGateProps {
  tier: Tier
  children: ReactNode
}

function getRole(user: { email?: string; app_metadata?: Record<string, unknown> } | null): Role {
  const entitlement = getEntitlement(user)
  if (!entitlement.hasAccess) return 'free'
  if (entitlement.role === 'founder' || entitlement.role === 'admin' || entitlement.role === 'qa') return 'admin'
  return 'subscriber'
}

export function AccessGate({ tier, children }: AccessGateProps) {
  const [role, setRole] = useState<Role>('loading')

  useEffect(() => {
    const supabase = createBrowserClient()
    supabase.auth.getSession().then(({ data }) => {
      setRole(getRole(data.session?.user ?? null))
    })
  }, [])

  // Still loading — render nothing (no flash of content or lock UI)
  if (role === 'loading') return null

  // Admin can see everything
  if (role === 'admin') return <>{children}</>

  // Subscriber tier: subscribers and above can see
  if (tier === 'subscriber' && role === 'subscriber') return <>{children}</>

  // Free / unauthenticated: render nothing — no lock, no CTA, no hint
  return null
}
