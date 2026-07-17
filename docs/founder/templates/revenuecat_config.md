# RevenueCat Config Template — Epic Fury (iOS IAP)

**Placeholders only. Do NOT paste secret values into this file or into chat.**
Fill these in inside the RevenueCat dashboard (step S5 of `docs/founder/epic_fury_appstore_runbook.md`). Secret VALUES go only into the RevenueCat dashboard and the Vercel / local build env by their NAMES below.

Apple Team ID: `K34GR8P326`

---

## 1. iOS app
- Platform: **iOS (Apple App Store)**
- Bundle prefix: `com.epicfury.dashboard`
- **App-Specific Shared Secret:** `<PASTE_FROM_APP_STORE_CONNECT>`  ← generated in ASC at step S4; entered in RevenueCat, never committed.

## 2. Products (must match App Store Connect product IDs exactly)
| Product ID | Type | Price (ASC) | RevenueCat package |
|---|---|---|---|
| `com.epicfury.dashboard.pro_monthly` | Auto-renewable subscription | `$4.99 / month` | `$rc_monthly` |
| `com.epicfury.dashboard.pro_annual`  | Auto-renewable subscription | `$39.99 / year` | `$rc_annual`  |

> Price source: queue item `ef-b2-create-subs`. Final price is set by the founder in App Store Connect at creation time.

## 3. Entitlement
- Identifier: **`pro`**
- Attach BOTH products above to entitlement `pro`.

## 4. Offering
- Identifier: **`current`** (default offering)
- Packages:
  - Monthly → `com.epicfury.dashboard.pro_monthly`
  - Annual  → `com.epicfury.dashboard.pro_annual`

## 5. Webhook
- URL: `https://<APP_BASE_URL>/api/webhooks/revenuecat`
- Auth header secret: stored under env name **`REVENUECAT_WEBHOOK_SECRET`** (value set in Vercel + local build env, not here).

## 6. Key NAMES only (values live in env / dashboard, never in this file or chat)
| Name | Where it's set | What it is |
|---|---|---|
| `NEXT_PUBLIC_REVENUECAT_IOS_KEY` | Vercel env + local build env | RevenueCat **iOS public SDK key** (replaces the dummy `rc_dummy_active_key_test` currently baked in build v3) |
| `REVENUECAT_WEBHOOK_SECRET`      | Vercel env + local build env | Shared secret validating the RevenueCat → app webhook |
| App-Specific Shared Secret        | RevenueCat dashboard (iOS app) | ASC shared secret so RevenueCat can validate Apple receipts |

---

### Acceptance check (mirrors runbook S5–S6)
- RevenueCat shows 2 products, entitlement `pro`, offering `current` (monthly + annual).
- iOS public SDK key copied into `NEXT_PUBLIC_REVENUECAT_IOS_KEY`.
- Webhook saved to `/api/webhooks/revenuecat` with `REVENUECAT_WEBHOOK_SECRET`.
- Next rebuild (S7) bakes the **real** key, not `rc_dummy_active_key_test` (verify per `docs/revenue/epic_fury_rebuild_verify.md`).
