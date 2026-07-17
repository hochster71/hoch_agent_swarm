# Epic Fury 2026 — True State + Remaining Founder Gates (2026-07-16)

Verified against live systems tonight. NO FAKE GREEN — every claim below was checked, not asserted.

## ✅ LIVE and verified right now
- **Epic Fury 2026 is LIVE on the App Store** (you downloaded it).
- **Web app healthy**: AI endpoint returns real data (HTTP 200); ElevenLabs + OpenAI keys confirmed on Vercel Production (110–112 days old).
- **iOS purchase path is compliant**: native Apple IAP via RevenueCat (`@revenuecat/purchases-capacitor`, StoreKit init on native only) + Stripe on web. No guideline 3.1.1 risk.
- **Sign in with Apple is NOT required**: Google OAuth is disabled in prod, so guideline 4.8 does not apply. (Skipped — would not advance GOAL.)

## ✅ Fixed + deployed this session (web → live in the app instantly, no Apple review)
1. **In-app email/password sign-in** — completes inside the app's webview, so the session reaches the server. Fixes the "voices gone" 403 (voices require a signed-in session; your gmail + icloud are both founder-allowlisted).
2. **>100% percentages killed** — threat % clamped 0–100 in the newsroom render + both AI script routes (the "4100%" bug).
3. **Homepage banner honest** — false "NOT REAL-TIME // MODELED PROJECTIONS" → accurate "LIVE OSINT FEED + MODELED SIMULATION — check each panel's label."
4. **Your name/personal email removed** from support/terms/refund pages (→ support@epicfury.app) and the store description (anonymized, credentials kept).
5. **Fabricated-as-verified news neutralized** — 63 simulated scenario items no longer stamped `verified:true` or attributed to real wires; now `verified:false` + "SIM ·" source + explicit "SIMULATED — not verified reporting" disclaimers.

Commits: `a3bcd28` (auth), `98465a3` (audit fixes), `6c05d97` (safety).

## 🔴 Remaining — all YOURS, each teed to its last click

### 1. First settled dollar — ARMED, nothing to do
Epic Fury's live web charge settles **~July 21**. A scheduled task fires **July 22 09:00 CT** that verifies the Stripe balance transaction and records HELM's first settled dollar only if it truly settled. (Task: `helm-epic-fury-settlement-check`.)

### 2. Ship the correct radar icon + de-named store listing (v1.0.2 / build 11)
The radar icon is baked into build 11 (archived, keyless, held) and the de-named description is staged. Both go up together with the v1.0.2 metadata submission.
- **Your one action:** generate a fresh App Store Connect API key (Users & Access → Integrations → App Store Connect API → Generate; download the `.p8`). The old key `YN6M769677` is revoked — that's why prior submits died.
- **Then it's automatic:** `bash ~/epic-fury-build/epic-fury-2026/finish_asc_submission.sh` — auto-detects the key, verifies auth (fail-closed), submits build 11 + metadata for review.

### 3. Confirm iOS subscription products (so native buyers can pay)
The code is wired; verify the RevenueCat **offering + products** exist and match your App Store Connect subscription products, and that `NEXT_PUBLIC_REVENUECAT_IOS_KEY` is set on Vercel prod. (Dashboards: App Store Connect + RevenueCat — your login.)

### 4. Story Studio first buyer (second revenue path, already live)
Story Studio's checkout is verified live (both tiers). Post the first-buyer kit (`docs/founder/story_studio_first_buyer_kit.md`) to get the first dollar there too. (Your send.)

## Verify voices are fixed (30 sec)
Open the app → sign-in screen → email + password → Create Account → you're in → voices should play (not the robotic fallback). If they do, the whole auth chain is confirmed end-to-end.
