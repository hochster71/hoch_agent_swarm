export interface UserEntitlement {
  hasAccess: boolean;
  role: 'public' | 'qa' | 'admin' | 'founder';
  mode: 'paid_customer' | 'internal_preview' | 'stripe_test' | 'founder_override' | null;
}

export function getEntitlement(
  user: { email?: string; app_metadata?: Record<string, any> } | null
): UserEntitlement {
  // Read environments (checking public fallback for browser bundle compatibility)
  const adminEmailsStr = 
    process.env.EPIC_FURY_ADMIN_EMAILS || 
    process.env.NEXT_PUBLIC_EPIC_FURY_ADMIN_EMAILS || 
    "michael.b.hoch@gmail.com";
  const adminEmails = adminEmailsStr
    .split(",")
    .map(e => e.trim().toLowerCase())
    .filter(Boolean);

  const qaEmailsStr = 
    process.env.EPIC_FURY_QA_EMAILS || 
    process.env.NEXT_PUBLIC_EPIC_FURY_QA_EMAILS || 
    "";
  const qaEmails = qaEmailsStr
    .split(",")
    .map(e => e.trim().toLowerCase())
    .filter(Boolean);

  const internalPreviewEnabled = 
    process.env.EPIC_FURY_INTERNAL_PREVIEW_ENABLED === "true" || 
    process.env.NEXT_PUBLIC_EPIC_FURY_INTERNAL_PREVIEW_ENABLED === "true";

  const stripeTestMode = 
    process.env.EPIC_FURY_STRIPE_TEST_MODE === "true" || 
    process.env.NEXT_PUBLIC_EPIC_FURY_STRIPE_TEST_MODE === "true";

  const isDev = process.env.NODE_ENV !== "production";

  if (!user) {
    return {
      hasAccess: false,
      role: 'public',
      mode: null
    };
  }

  const email = (user.email || "").toLowerCase();

  // 1. Founder check via email allowlist or app_metadata
  if (adminEmails.includes(email) || email === "michael.b.hoch@gmail.com") {
    return {
      hasAccess: true,
      role: 'founder',
      mode: 'founder_override'
    };
  }

  // 2. Admin role via app_metadata
  if (user.app_metadata?.role === 'admin') {
    return {
      hasAccess: true,
      role: 'admin',
      mode: 'founder_override'
    };
  }

  // 3. QA allowlist check
  if (qaEmails.includes(email)) {
    return {
      hasAccess: true,
      role: 'qa',
      mode: 'internal_preview'
    };
  }

  // 4. Local/Dev Internal Preview Mode
  if (internalPreviewEnabled && isDev) {
    return {
      hasAccess: true,
      role: 'qa',
      mode: 'internal_preview'
    };
  }

  // 5. Standard Stripe subscriber checks
  // A paid customer is proven by the FACT OF PAYMENT (subscription_status), not only by
  // the role string. An admin who pays keeps role='admin' (we never downgrade a
  // privileged role) -- without this, a paying admin would be invisible as a customer
  // and the paid path could never be proven end to end.
  const hasActiveSubscription = user.app_metadata?.subscription_status === 'active';
  const isSubscriber = user.app_metadata?.role === 'subscriber' || hasActiveSubscription;
  if (isSubscriber) {
    return {
      hasAccess: true,
      role: 'public',
      mode: 'paid_customer'
    };
  }

  // 6. Stripe Test Mode check (simulated subscriber)
  //    HARDENED: was `stripeTestMode && ...` with NO environment guard, so a single
  //    env var in production would have granted paid access to any user carrying a
  //    stripe_customer_id. Test-only paths must be UNAVAILABLE in production.
  if (stripeTestMode && isDev && user.app_metadata?.stripe_customer_id) {
    return {
      hasAccess: true,
      role: 'public',
      mode: 'stripe_test'
    };
  }

  return {
    hasAccess: false,
    role: 'public',
    mode: null
  };
}
