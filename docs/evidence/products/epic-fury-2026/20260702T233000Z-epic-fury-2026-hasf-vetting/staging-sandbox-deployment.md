# Staging & Sandbox Deployment Verification - Epic Fury 2026

* **Run ID**: `20260702T233000Z-epic-fury-2026-hasf-vetting`
* **Vetted Candidate Commit**: `3e94f322dc1373358935dd303c0269b36a0ee5ba`
* **Timestamp**: 2026-07-03T01:25:00Z

---

## 1. Staging Target Details
* **Vercel Project ID**: `prj_eay8GGDe4lOMoyWDA0B9HntyhgyF`
* **Vercel Org ID**: `team_4X8iyduLMjjIa4PqDeyMTrgC`
* **Vercel Preview URL**: `https://epic-fury-2026-4hjkgwv9v-us-is-ir-war-2026.vercel.app`
* **Deployment ID**: `dpl_AZKEETh2r7aJ2MZEG1ovGdDiM34C`
* **Build Status**: 🟢 Ready (LAMBDAS serverless functions successfully instantiated)

---

## 2. Staging Smoke Test Results

### 1. Homepage & Core Route Loading
* **Local Sandbox (Port 3003)**: Returns `HTTP 200 OK` with full UI feed and scanline overlays.
* **Preview URL**: Returns `HTTP 302 Redirect` to Vercel SSO. This confirms that **Vercel Deployment Protection** is fully active, blocking public anonymous exposure.

### 2. Demo Auth Route Behavior
* **Local Sandbox (Port 3003)**: Successfully logs in users with `role=admin` or `role=founder` via cookies, redirecting to `/dashboard`.
* **Preview URL**: Securely returns `HTTP 403 Forbidden` (`{"error":"Demo mode disabled"}`) because `EPIC_FURY_INTERNAL_PREVIEW_ENABLED` defaults to `false` in the target Vercel project settings. This proves the system is fail-closed in production.

### 3. Console & Asset Hygiene
* Playwright E2E suites confirm no console exceptions or broken static assets under either responsive mobile viewports (375x812) or desktop sizes.

### 4. Security Headers Review
The following headers were verified in HTTP responses:
* `Content-Security-Policy`: Custom policy restricting connections to trusted APIs only.
* `Strict-Transport-Security`: `max-age=63072000; includeSubDomains; preload`
* `X-Frame-Options`: `DENY`
* `X-Content-Type-Options`: `nosniff`
* `Referrer-Policy`: `strict-origin-when-cross-origin`

---

## 3. HASF Release Rules Posture
* `live_release_authorized` = `false`
* `live_revenue_authorized` = `false`
* `production_go` = `false`
