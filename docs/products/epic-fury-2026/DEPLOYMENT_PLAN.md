# Deployment Plan - Epic Fury 2026

* **Run ID**: 20260702T233000Z-epic-fury-2026-hasf-vetting

---

## 1. Deployment Steps

### 1. Build Verification
* Execute Next.js build compilation locally:
  ```bash
  npm run build
  ```

### 2. Environment Synchronization
* Push Supabase and Stripe sandbox configuration variables to target Vercel environments:
  ```bash
  ./push-supabase-env.sh
  ./push-stripe-env.sh
  ```

### 3. Deploy to Staging/Production
* Trigger the production deploy command:
  ```bash
  npx vercel --prod --yes
  ```

### 4. Live Smoke Check
* Curl target production URLs and verify auth gates prevent unauthenticated entry with HTTP 403.
