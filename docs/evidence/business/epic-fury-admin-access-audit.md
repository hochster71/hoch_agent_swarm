# Epic Fury 2026 Admin Access & Payment Gate Security Audit

This document compiles the security audit findings for Epic Fury 2026's authentication, role-based access control, and Stripe payment/subscription gates.

---

## 1. Protected Pages & Routing Tiers

Premium and administrative routes are mapped in [lib/access-control.ts](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/lib/access-control.ts).
- **Admin Tier (`ADMIN_ROUTES`)**: Hard-blocked for anyone who is not an administrator. Includes:
  - `/dashboard/revenue`
  - `/dashboard/workflows`
  - `/dashboard/autonomous`
  - `/dashboard/agents`
  - `/dashboard/nexus`
  - `/dashboard/settings`
  - `/dashboard/debug`
- **Subscriber Tier (`SUBSCRIBER_ROUTES`)**: Requires an active subscription. Soft-blocked for free/unauthenticated users (they see a blurred skeleton overlay, rather than a hard redirect, to prevent console log noise). Includes:
  - `/dashboard`
  - All oracle, threat assessment, ceasefire models, intelligence feeds, battle maps, logistics, and forecasting views.

---

## 2. Gatekeeper Files (Access Controls)

We identified four central points of enforcement:

1. **Edge Middleware**: [middleware.ts](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/middleware.ts)
   - Method: `getUserRole()`
   - Inspects `session.user.app_metadata.role` (which can be `admin` or `subscriber`).
   - Fallback: Hardcodes `ADMIN_EMAIL` match against `session.user.email` (defaults to `michael.b.hoch@gmail.com`).
   - If user is not authorized, it performs a 302 redirect for admin pages.

2. **Server Gate Component**: [SubscriberGate.tsx](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/components/SubscriberGate.tsx)
   - Server-side wrapper around dashboard layout.
   - Inspects `session.user.app_metadata.role` dynamically from the current Supabase session.
   - If free or unauthenticated, renders a locked upgrade payload overlay.

3. **Client Gate Component**: [AccessGate.tsx](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/components/AccessGate.tsx)
   - Client-side component to wrap premium widget elements.
   - Checks `session.user.app_metadata.role` and `NEXT_PUBLIC_ADMIN_EMAIL`.

4. **API Auth Library**: [lib/api-auth.ts](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/lib/api-auth.ts)
   - Method: `resolveUserRole()`
   - Resolves caller role on API requests, gating server actions and cron executions.

---

## 3. Stripe Billing Integration

- **Checkout**: [/api/stripe/checkout](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/app/api/stripe/checkout/route.ts) creates checkout sessions.
- **Customer Portal**: [/api/stripe/portal](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/app/api/stripe/portal/route.ts) enables users to manage their billing profiles.
- **Webhook Ingestion**: [/api/webhooks/stripe](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/app/api/webhooks/stripe/route.ts) parses incoming webhook notifications to update the Supabase users' `app_metadata.role`.

---

## 4. Proposed Auditable Access Bypass Pattern

To enable founder/admin/internal QA access without weakening the public billing enforcement, we will implement a unified entitlement helper [lib/entitlements.ts](file:///Users/michaelhoch/epic-fury-build/epic-fury-2026/lib/entitlements.ts).
Access will be dynamically granted based on:
1. `EPIC_FURY_ADMIN_EMAILS` (Founder override)
2. `EPIC_FURY_QA_EMAILS` (Internal QA bypass)
3. `EPIC_FURY_INTERNAL_PREVIEW_ENABLED` (Local/development bypass flag)
4. `EPIC_FURY_STRIPE_TEST_MODE` (Stripe test client simulation)
5. Standard paid customer role checking
