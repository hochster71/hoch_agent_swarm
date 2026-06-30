# Epic Fury 2026 PODS Launch Mission Plan

Date: 2026-06-30
Role: HOCH PODS Epic Fury Launch Mission Engineer

This document outlines the structured, non-destructive revenue launch mission plan for Epic Fury 2026 through the HOCH PODS Control Plane.

## 1. Mission Details

- **Mission ID**: `fury-epic-launch-2026`
- **Goal**: Initialize, audit, and verify the production-readiness of the Epic Fury 2026 Next.js + Supabase application on the Business POD.
- **Repository Location**: `/Users/michaelhoch/epic-fury-build/epic-fury-2026`

## 2. Segment Analysis & Stack Classification

- **Framework**: Next.js 15.5.19
- **Libraries**: React 19.0.0, Jotai 2.10.0
- **Database / Auth**: Supabase SSR
- **Mobile Integration**: Capacitor CLI/core/ios with RevenueCat purchases
- **Web Monetization**: Stripe Node SDK

## 3. Launch Audit Plan

- **Step 1: Check Workspace Integrity**
  - Verification: Local directory existence, `.git` folder presence, clean branch verification.
- **Step 2: Dependency Verification**
  - Verification: `package.json` contains `next`, `react`, `stripe`, and `@revenuecat/purchases-capacitor`.
- **Step 3: Route Discovery & Compliance**
  - Verification: `/privacy` and `/support` pages are present to satisfy store launch guidelines.
- **Step 4: Billing Endpoint Verification**
  - Verification: `/api/stripe/checkout` and `/api/webhooks/stripe` routing paths are active.
- **Step 5: E2E Telemetry Integration**
  - Verification: E2E Playwright test assertions run and register matching task names under the Control Plane telemetry graph.

## 4. Current Blockers / Status
- **Stripe & Supabase Vercel Secrets**: Local configurations exist, but the live endpoints are blocked until Vercel credentials are pushed to verify production payment pipelines.
- **k3d Kubernetes Sidecar**: Idle/waiting state due to local Docker availability.
- **Audit Result**: **GO** (Local source assets are 100% prepared).
