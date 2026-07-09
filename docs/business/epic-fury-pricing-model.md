# Epic Fury iOS In-App Purchase Compliance

## Purpose

This document reconciles the Epic Fury upgrade flow with Apple App Review Guideline **3.1.1** and confirms the required path for **iOS digital unlocks**.

## Compliance Statement

For **in-app digital upgrades/unlocks on iOS**, Epic Fury must use **Apple In-App Purchase (IAP) via StoreKit** rather than Stripe.

- **Allowed for iOS digital goods:** StoreKit / Apple IAP
- **Not allowed for iOS digital goods:** Stripe checkout or any external payment flow
- **Optional implementation layer:** RevenueCat may be used as a wrapper, provided it ultimately uses Apple IAP / StoreKit

## Required Behavior

The app must ensure that:

1. **iOS digital subscriptions are initiated through StoreKit**
2. **Stripe is not used** to purchase or unlock digital content/features inside the iOS app
3. Any unlock that grants digital access in the app is tied to Apple-managed subscription products

## Required Subscription Product IDs

The following **auto-renewable subscription** product IDs must be configured and used for iOS:

- `pro_monthly`
- `pro_annual`

These product IDs should be registered in App Store Connect and mapped to the app’s iOS entitlement/unlock logic.

## Implementation Fix If Stripe Is Wired

If the current upgrade flow in `docs/business/epic-fury-pricing-model.md` or the app code routes iOS digital upgrades through Stripe, the fix is:

1. **Replace Stripe checkout for iOS digital unlocks**
   - Remove Stripe as the purchase path for any in-app digital subscription or feature unlock on iOS.

2. **Route purchases through StoreKit**
   - Use Apple IAP directly via StoreKit, or
   - Use RevenueCat configured to purchase Apple subscriptions via StoreKit

3. **Map entitlements to Apple subscription products**
   - Connect `pro_monthly` and `pro_annual` to the app’s premium entitlement logic.

4. **Preserve Stripe only for non-iOS or non-digital use cases**
   - Stripe may remain in use for web or other permitted commerce flows, but not for iOS in-app digital purchases.

## Compliance Confirmation

Epic Fury’s iOS app must call **StoreKit**, not Stripe, for digital upgrades and unlocks.  
The required auto-renewable subscription product IDs are:

- `pro_monthly`
- `pro_annual`

If Stripe is currently wired for this flow, it must be removed or bypassed for iOS digital purchases and replaced with Apple IAP / StoreKit, optionally mediated by RevenueCat.
