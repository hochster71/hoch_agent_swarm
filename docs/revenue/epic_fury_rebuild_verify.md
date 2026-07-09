# Epic Fury iOS Build & Revenue Verification Report

**Date:** 2026-07-09  
**Posture:** DOORSTEP Gated  
**Status:** BLOCKED (Pending Founder Key Provisioning)

---

## 1. Vercel Environment Variables Validation

We ran security scans and checks against the active Vercel environments for Epic Fury (`epic-fury-2026`) and Story Studio (`story-studio-live`).

| Variable Name | Project | Status | Action Required |
| :--- | :--- | :--- | :--- |
| `REVENUECAT_WEBHOOK_SECRET` | `epic-fury-2026` | **SET** 🟢 | None (Already active in Production). |
| `NEXT_PUBLIC_REVENUECAT_IOS_KEY` | `epic-fury-2026` | **MISSING** 🔴 | **Founder Action:** Add this key to the Vercel dashboard (Production environment) and local build `.env` to bake it into the client-side bundle. |
| `AUTH_SECRET` | `story-studio-live` | **SET** 🟢 | None (Magic-link login active in Production). |

---

## 2. Rebuild Task (`ns-ef-rebuild`) Status

* **Directory:** `/Users/michaelhoch/epic-fury-build/epic-fury-2026`
* **Status:** **BLOCKED**
* **Reason:** Next.js bakes environment variables starting with `NEXT_PUBLIC_` directly into the client-side JavaScript bundle at build time. Running the rebuild now would produce an iOS package with a null RevenueCat public key, disabling StoreKit paywalls on device.

Once the `NEXT_PUBLIC_REVENUECAT_IOS_KEY` is set:
1. Run `npx vercel env pull` to fetch the keys locally.
2. Execute the build loop:
   ```bash
   npm run build
   npx cap sync ios
   ```
3. Bump the build version in Xcode and Fastlane.
4. Verify the iOS bundle and compile the release package.

---

## 3. Step-by-Step Action Items for Founder

### A. Paid Applications Agreement
1. Log in to [App Store Connect](https://appstoreconnect.apple.com).
2. Go to **Business** > **Agreements**.
3. Sign the **Paid Applications Agreement** and verify that your banking and tax information are active.

### B. Create Subscription IDs
1. Go to **Apps** > **Epic Fury** > **Subscriptions**.
2. Create a Subscription Group and add the following two auto-renewable subscriptions:
   * **Monthly subscription:** `com.epicfury.dashboard.pro_monthly` ($4.99/mo)
   * **Annual subscription:** `com.epicfury.dashboard.pro_annual` ($39.99/yr)
3. Generate the **App-Specific Shared Secret**.

### C. Configure RevenueCat
1. Log in to [RevenueCat Dashboard](https://app.revenuecat.com).
2. Add your iOS app under the project and input the App-Specific Shared Secret.
3. Define the two products matching the Apple product IDs above.
4. Set up the Entitlement (`pro`) and the Offering (`current`).
5. Copy the **Public SDK Key** and set the webhook URL to:
   `https://epic-fury-2026.vercel.app/api/webhooks/revenuecat` (or your active Vercel domain).

### D. Set Vercel environment
1. Add `NEXT_PUBLIC_REVENUECAT_IOS_KEY` to your Vercel project environment.
2. Trigger the `ns-ef-rebuild` task.
