'use client'

/**
 * PurchasesProvider.tsx
 *
 * Small client component that initialises RevenueCat once on native iOS.
 * Reads the current Supabase session to pass the user UUID as the RC app user ID
 * so RevenueCat and Supabase stay in sync.
 * Renders nothing — pure side-effect.
 */

import { useEffect } from 'react'
import { initializePurchases, isNative } from '@/lib/purchases'
import { createBrowserClient }           from '@/lib/supabase'

export function PurchasesProvider() {
  useEffect(() => {
    if (!isNative()) return

    async function init() {
      try {
        const supabase = createBrowserClient()
        const { data } = await supabase.auth.getSession()
        const userId = data.session?.user?.id
        await initializePurchases(userId)
      } catch (e) {
        console.warn('[PurchasesProvider] init failed:', e)
      }
    }

    init()
  }, [])

  return null
}
