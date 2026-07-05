# Apple Compliance Preflight

This document outlines the Apple compliance criteria, data flow audits, differentiation checkpoints, and reviewer instructions.

## Verification Checklist

1. **Privacy Manifest File**:
   - iOS project includes `Runner/PrivacyInfo.xcprivacy`.
   - Third-party SDK manifests checked for API category reasons (`UserDefaults`, `FileTimestamp`).

2. **Data Flow Audit**:
   - Verified that actual network telemetry data flows do not conflict with privacy label definitions.
   - Diffed flows against `provider_data_egress_policy.json` to reject unapproved targets.

3. **Differentiation Checklist**:
   - Unique functionality: Companion app for RMF review evidence.
   - Custom UI: Specialized dark theme with compliance charts.
   - Original branding: Built under the HASF banner.
   - No web wrapper, clone pattern, or duplicate codebase spam.

4. **Reviewer Instructions**:
   - Clean install checked.
   - Demo credentials: `auditor@hasf.local` / `Compliance2026!`.
   - Restore purchases verified if dynamic paywall is toggled.
