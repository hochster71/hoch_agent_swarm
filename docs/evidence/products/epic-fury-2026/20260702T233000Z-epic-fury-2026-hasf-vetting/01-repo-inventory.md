# Phase 1: Repo Inventory - Epic Fury 2026

* **Run ID**: 20260702T233000Z-epic-fury-2026-hasf-vetting
* **Audited Path**: `/Users/michaelhoch/epic-fury-build/epic-fury-2026`
* **Audited Commit**: `91e0adb70ff29e5947ef1daf9c6ac952fa78a24b`
* **Timestamp**: 2026-07-02T23:30:00Z

---

## 1. Stack Detection
* **Runtime**: Node.js (>=20.0.0)
* **Framework**: Next.js (15.5.19, App Router)
* **Language**: TypeScript (5.x)
* **Package Manager**: npm (package-lock.json detected)
* **CSS Framework**: Tailwind CSS (3.4.1)
* **Database/Backend**: Supabase (via @supabase/ssr and @supabase/supabase-js)
* **Monetization**: Stripe & RevenueCat (purchases-capacitor)
* **App Shell**: Capacitor CLI & Capacitor iOS (hybrid iOS app deployment capability)

---

## 2. Docker & Containerization
* **Dockerfile**: Present (dev & production)
* **docker-compose.yml**: Present
* **docker-compose.dev.yml**: Present

---

## 3. GitHub Actions CI/CD workflows
* **ios-deploy.yml**: For Capacitor iOS App deployment
* **production-contract.yml**: Performs production checks
* **upload-screenshots.yml**: For app store updates

---

## 4. Operational & Test Suites
* **test:contract**: `node scripts/ci/test-contract.mjs`
* **test:smoke**: `node scripts/ci/test-smoke.mjs`
* **test:api-hardening**: `node scripts/ci/test-api-hardening.mjs`
* **truth:gate**: `node scripts/ci/domain-truth-gate.mjs`
