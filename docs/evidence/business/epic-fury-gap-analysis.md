# Epic Fury HASF Onboarding Gap Analysis (RC42)

**Project Name**: Epic Fury 2026  
**Tracking ID**: `LOCAL-003`  
**Date**: 2026-07-01  

---

## 1. Analyzed Pipeline Gaps

We performed a comparative gap analysis between the **Epic Fury** deployment scripts and the standard **HASF** pipeline controls:

| Control Target | Epic Fury Status | Gaps Identified | Remediation Action |
| --- | --- | --- | --- |
| **Port Security** | Private / Local Dev | None. Dev ports restricted to local network. | Keep public exposure closed. |
| **Telemetry Integration** | Local stdout logs | Lacks structured 6-field telemetry provenance. | Map logs to PERT telemetry audit schema. |
| **Stripe Keys State** | Unconfigured | No sandbox credentials configured. | Integrate sandbox gate checks (RC42). |
| **Pipeline Visuals** | Terminal outputs | No cockpit display for pipeline progression. | Add animated flowchart to cockpit. |
| **Content Security Policy** | Too Restrictive | `CSP_PREVIEW_TOOLING_GAP`: Vercel preview toolbar iframe `https://vercel.live` blocked by `frame-src`. | Add conditional allow for `https://vercel.live` in preview/dev deployments. |

## 2. CSP Audit Findings

* **Finding ID**: `CSP_PREVIEW_TOOLING_GAP`
* **Description**: The Content Security Policy `frame-src` directive restricted framing origins exclusively to `https://js.stripe.com` and `https://hooks.stripe.com`. This successfully protected production but blocked Vercel Toolbar/preview collaboration frames.
* **Classification**: `CSP_PREVIEW_TOOLING_GAP`
* **Severity**: `LOW` for runtime app operations, `MEDIUM` for preview pipeline tooling.
* **Remediation**: Added `https://vercel.live` and `'self'` to `frame-src` under non-production environments (`process.env.VERCEL_ENV === 'preview' || process.env.VERCEL_ENV === 'development' || IS_DEV`) while retaining strict controls in production.
* **Directives Audited**:
  - `frame-src` (Stripe only in prod, Vercel Toolbar allowed in preview/dev)
  - `script-src` (Self / strict nonce-based in prod, unsafe-inline/unsafe-eval in dev for HMR)
  - `connect-src` (Supabase, Stripe, and approved AI hostnames)
  - `img-src` (Self, data, blob, and generic https)
  - `style-src` (Self, unsafe-inline, and Google fonts)
  - `font-src` (Self, data, and Google fonts)
  - `frame-ancestors` (Strictly set to `'none'`)
  - `report-uri` (Configured to `/api/security/csp-report`)

## 3. Verification Safety Invariants
- Public Port 3012 is UFW-blocked (unchanged).
- Live mode pricing elements are blocked.
- Production Content Security Policy strictly blocks `vercel.live`.
