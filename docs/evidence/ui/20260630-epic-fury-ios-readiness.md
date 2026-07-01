# Epic Fury 2026 iOS/Capacitor Readiness Evidence

Date: 2026-06-30
Role: Business POD Epic Fury iOS Readiness Engineer

This document provides evidence of the Capacitor iOS shell readiness audit performed on the local clone of Epic Fury 2026.

## 1. Capacitor configuration

- **App ID (Bundle Identifier)**: `com.epicfury.dashboard`
- **App Name**: `Epic Fury 2026`
- **Server Web URL**: `https://epic-fury-2026.vercel.app` (native wrapper pointing to the Vercel-hosted server-rendered site)
- **Background Color**: `#09090b` (zinc-950)
- **Active Plugins**: `SplashScreen`, `StatusBar`

## 2. native iOS project structure

- **Path**: `/Users/michaelhoch/epic-fury-build/epic-fury-2026/ios/App`
- **Xcode Project File**: `App.xcodeproj` exists.
- **Dependencies Management**: Swift Package Manager (`Package.swift` inside `CapApp-SPM` directory)
- **Privacy Manifest**: `App/PrivacyInfo.xcprivacy` exists and contains correct reason codes for `NSUserDefaults` (`CA92.1`) and `FileTimestamp` (`C617.1`).
- **Assets**: 
  - AppIcon: `AppIcon.appiconset` is present with a universal 1024x1024 master icon (`AppIcon-512@2x.png`).
  - Splash screen: `Splash.imageset` is present with required `splash-2732x2732.png` assets.

## 3. RevenueCat integration

- **Integration helper**: Located at `lib/purchases.ts`.
- **Product IDs**:
  - `com.epicfury.dashboard.pro_monthly` (Monthly Sub)
  - `com.epicfury.dashboard.pro_annual` (Annual Sub)
- **Configuration Method**: Configured dynamically using `NEXT_PUBLIC_REVENUECAT_IOS_KEY`.

## 4. App Store Connect Registration Gaps

While the native wrapper and codebase are build-ready, the following items are required prior to App Store submission:
1. **Bundle ID Registration**: Confirm `com.epicfury.dashboard` is registered in the Apple Developer portal.
2. **Screenshots**: The `/screenshots` directory is currently empty. Apple requires 6.5" and 5.5" iPhone screenshots for submission.
3. **Terms of Service (EULA)**: A dedicated terms route (e.g. `/terms`) is missing (only `/privacy` and `/support` are implemented).
4. **App Store Connect Metadata**: Setting app category to News and configuring the RevenueCat purchase products matching the product IDs.

## 5. Audit Verdict

**CONDITIONAL GO** (code, configuration, and dependencies are clean and fully build-ready, but submission-specific assets/registrations like screenshots and terms route are pending).
