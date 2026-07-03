# Staging Static Asset Load Remediation - Epic Fury 2026

* **Run ID**: `20260702T233000Z-epic-fury-2026-hasf-vetting`
* **Candidate Commit**: `3e94f322dc1373358935dd303c0269b36a0ee5ba`
* **Timestamp**: 2026-07-03T01:44:00Z

---

## 1. Root Cause Analysis
Vercel Deployment Protection with SSO is enabled on the `us-is-ir-war-2026` team scope. When a user or test agent requests any preview deployment URL anonymously, Vercel interceptors redirect the requests to:
`https://vercel.com/sso-api?url=...`

While browser navigation redirects the primary page load successfully to Vercel's login portal, the browser's HTML parser attempts to load referenced static assets (e.g., CSS stylesheets, JS bundles, woff2 fonts under `/_next/static`) asynchronously. These sub-resources are redirected as well, causing CORS, CORS-related TLS handshake blockages, and browser layout engine errors.

---

## 2. Curl Headers Comparison

### Anonymous Access (Asset Loader Failure)
```http
HTTP/2 302 
cache-control: no-store, max-age=0
location: https://vercel.com/sso-api?url=https%3A%2F%2Fepic-fury-2026-4hjkgwv9v-us-is-ir-war-2026.vercel.app%2F_next%2Fstatic%2Fchunks%2Fwebpack.js...
server: Vercel
```

### Authenticated/Bypass Access (Success)
```http
HTTP/2 200 
content-type: application/javascript; charset=utf-8
cache-control: public,max-age=31536000,immutable
server: Vercel
```

---

## 3. Vercel Protection Status
* **SSO Protection**: `ENABLED` (Required to prevent public exposure of preview environment credentials and Supabase database schemas).
* **Password Protection**: `DISABLED` (Unavailable due to Vercel team plan constraints: *"Advanced Deployment Protection is not enabled on your team"*).
* **Automation Bypass**: `ENABLED` (Bypass token: `[REDACTED_VERCEL_PROTECTION_BYPASS]`).

---

## 4. Browser E2E Test Results
The newly created suite `tests/e2e/epic-fury-staging-assets.spec.ts` passes successfully:
* Homepage title verified: `PASS`
* Layout CSS/JS chunks load with `200 OK`: `PASS`
* No TLS or script loading exceptions caught: `PASS`

---

## 5. Founder Access Instructions

To successfully view and review the Vercel staging build:

### Option A: Standard SSO Path (Recommended)
1. In your review browser, navigate to the Staging URL:
   `https://epic-fury-2026-4hjkgwv9v-us-is-ir-war-2026.vercel.app`
2. Vercel will prompt you to log in. Click the login button and sign in using your GitHub/Vercel account (`hochster71`).
3. Once authenticated, Vercel sets the secure session cookies. Refresh the page, and the dashboard layout and all static styling assets will render perfectly.

### Option B: Automation Bypass Path
Optional automation bypass is configured but stored only in Vercel/project secret storage. Never printed in logs, docs, chat, or evidence.

---

## 6. Release Posture
* `live_release_authorized = false`
* `live_revenue_authorized = false`
