/**
 * lib/purchases.ts — RevenueCat in-app purchase helper
 *
 * Wraps @revenuecat/purchases-capacitor for use within the Epic Fury
 * Capacitor iOS shell. The web (Vercel) runtime skips all StoreKit calls.
 *
 * Product IDs must match what you create in App Store Connect:
 *   com.epicfury.dashboard.pro_monthly   — $4.99/month auto-renewable
 *   com.epicfury.dashboard.pro_annual    — $39.99/year auto-renewable
 *
 * After a successful purchase, the native side calls /api/auth/activate-pro
 * (bearer = RevenueCat webhook secret) to flip the Supabase user role to
 * 'subscriber'. The client also re-fetches the Supabase session so the UI
 * updates without a reload.
 */

'use client'

import { Capacitor } from '@capacitor/core'

// ── Product IDs ─────────────────────────────────────────────────────────────
export const PRODUCT_MONTHLY = 'com.epicfury.dashboard.pro_monthly'
export const PRODUCT_ANNUAL  = 'com.epicfury.dashboard.pro_annual'

export const PRICE_MONTHLY_USD = '$19'
export const PRICE_ANNUAL_USD  = '$190'     // ≈ $15.83/mo — 2 months free

// ── Platform guard ──────────────────────────────────────────────────────────
export function isNative(): boolean {
  return Capacitor.isNativePlatform()
}

// ── Lazy-import RevenueCat (native only) ────────────────────────────────────
async function rc() {
  const { Purchases, LOG_LEVEL } = await import('@revenuecat/purchases-capacitor')
  return { Purchases, LOG_LEVEL }
}

// ── Initialize ──────────────────────────────────────────────────────────────
let _initialized = false

export async function initializePurchases(userId?: string): Promise<void> {
  if (!isNative() || _initialized) return

  const apiKey = process.env.NEXT_PUBLIC_REVENUECAT_IOS_KEY
  if (!apiKey) {
    console.warn('[Purchases] NEXT_PUBLIC_REVENUECAT_IOS_KEY not set — StoreKit disabled')
    return
  }

  const { Purchases, LOG_LEVEL } = await rc()
  await Purchases.setLogLevel({ level: LOG_LEVEL.WARN })
  await Purchases.configure({ apiKey })
  if (userId) await Purchases.logIn({ appUserID: userId })
  _initialized = true
}

// ── Check entitlement ────────────────────────────────────────────────────────
export async function hasProEntitlement(): Promise<boolean> {
  if (!isNative()) return false
  try {
    const { Purchases } = await rc()
    const { customerInfo } = await Purchases.getCustomerInfo()
    return 'pro' in customerInfo.entitlements.active
  } catch {
    return false
  }
}

// ── Fetch available packages ─────────────────────────────────────────────────
export interface PurchasePackage {
  identifier: string
  productIdentifier: string
  priceString: string
}

export async function getOfferings(): Promise<PurchasePackage[]> {
  if (!isNative()) return []
  try {
    const { Purchases } = await rc()
    const offerings = await Purchases.getOfferings()
    const current = offerings.current
    if (!current) return []
    return current.availablePackages.map(p => ({
      identifier:        p.identifier,
      productIdentifier: p.product.identifier,
      priceString:       p.product.priceString,
    }))
  } catch {
    return []
  }
}

// ── Purchase ─────────────────────────────────────────────────────────────────
export async function purchasePackage(packageIdentifier: string): Promise<boolean> {
  if (!isNative()) return false
  try {
    const { Purchases } = await rc()
    const offerings = await Purchases.getOfferings()
    const pkg = offerings.current?.availablePackages.find(
      p => p.identifier === packageIdentifier
    )
    if (!pkg) return false
    const { customerInfo } = await Purchases.purchasePackage({ aPackage: pkg })
    return 'pro' in customerInfo.entitlements.active
  } catch (e) {
    // User cancelled = PurchasesErrorCode.PURCHASE_CANCELLED_ERROR — not an error
    console.warn('[Purchases] purchasePackage:', e)
    return false
  }
}

// ── Restore ──────────────────────────────────────────────────────────────────
export async function restorePurchases(): Promise<boolean> {
  if (!isNative()) return false
  try {
    const { Purchases } = await rc()
    const { customerInfo } = await Purchases.restorePurchases()
    return 'pro' in customerInfo.entitlements.active
  } catch {
    return false
  }
}
