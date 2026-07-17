/**
 * lib/access-control.ts — Route Access Control Definitions
 *
 * Single source of truth for which routes require which access tier.
 * Used by: middleware.ts (server), Sidebar.tsx (client), AccessGate (component).
 *
 * Tiers (lowest → highest):
 *   'public'     — no auth required
 *   'subscriber' — requires active paid subscription
 *   'admin'      — owner only (michael.b.hoch@gmail.com)
 */

export type AccessTier = 'public' | 'subscriber' | 'admin'

export interface RouteAccess {
  path: string
  tier: AccessTier
}

/**
 * ADMIN-ONLY routes — visible and accessible only to the app owner.
 * Anyone else hitting these URLs gets a hard 403 redirect to /dashboard.
 */
export const ADMIN_ROUTES: string[] = [
  '/dashboard/revenue',
  '/dashboard/workflows',
  '/dashboard/autonomous',
  '/dashboard/agents',
  '/dashboard/nexus',
  '/dashboard/settings',
  '/dashboard/debug',
]

/**
 * SUBSCRIBER routes — require paid subscription.
 * Unauthenticated users see an upgrade gate. Free-tier users see upgrade prompt.
 */
export const SUBSCRIBER_ROUTES: string[] = [
  '/dashboard',
  '/dashboard/feed',
  '/dashboard/sitrep',
  '/dashboard/newsroom',
  '/dashboard/news',
  '/dashboard/homeland',
  '/dashboard/intel',
  '/dashboard/oracle',
  '/dashboard/bda',
  '/dashboard/hva',
  '/dashboard/orbat',
  '/dashboard/dmo',
  '/dashboard/cop',
  '/dashboard/econ',
  '/dashboard/logistics',
  '/dashboard/ceasefire',
  '/dashboard/threats',
  '/dashboard/brief',
  '/dashboard/timeline',
  '/dashboard/world',
]

/**
 * PUBLIC routes — freely accessible without auth.
 * This list is the allow-list; anything not here defaults to subscriber-gated.
 */
export const PUBLIC_ROUTES: string[] = [
  // Keep non-dashboard routes (/, /upgrade, /login, /privacy, etc.) publicly accessible.
]

/**
 * Shells with no content behind them. Blocked at every tier — you do not charge for
 * an empty page. They return the day they have something in them.
 *
 * These must be BLOCKED, not merely dropped from SUBSCRIBER_ROUTES: getRouteTier
 * defaults any unlisted path to 'public', so deleting them would have made them
 * world-readable instead of unreachable.
 */
export const PLACEHOLDER_ROUTES: string[] = [
  '/dashboard/command',
  '/dashboard/debate',
  '/dashboard/foresight',
  '/dashboard/visuals',
]

export function isPlaceholder(pathname: string): boolean {
  return PLACEHOLDER_ROUTES.some((r) => pathname === r || pathname.startsWith(r + '/'))
}

export function getRouteTier(pathname: string): AccessTier {
  if (ADMIN_ROUTES.some((r) => pathname === r || pathname.startsWith(r + '/'))) {
    return 'admin'
  }
  if (SUBSCRIBER_ROUTES.some((r) => pathname === r || pathname.startsWith(r + '/'))) {
    return 'subscriber'
  }
  return 'public'
}
