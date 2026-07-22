# HELM Build Release Governance Specification (v1.0.0)

> **Normative Policy Artifact**  
> **Specification Version**: `1.0.0`  
> **Effective Date**: 2026-07-22  
> **Supersedes**: None  
> **Status**: APPROVED  

---

## 1. Scope & Objective

This specification establishes the mandatory, deterministic release governance criteria for all software builds released under the HELM Program. No release candidate may transition to `RELEASE_READY` without satisfying all requirements defined in this specification.

---

## 2. Release Qualification Domains

Every release candidate must achieve explicit qualification across six distinct domains:

1. **`Engineering Qualification`**: Source code remediation, static AST checks, component unit/JSDOM interaction tests, and clean typecheck execution.
2. **`Native Configuration Verification`**: Verification of Bundle Identifier, RevenueCat public iOS key, App Store Connect Product IDs, Offering IDs, Entitlement names, and Bundle ↔ ASC mappings.
3. **`Native Purchase Qualification`**: Verification of StoreKit payment sheet presentation, sandbox purchase execution, entitlement activation, and user cancellation handling on native iOS runtimes.
4. **`Device Qualification`**: Verification of UI flex layout and touch target hit-testing on target hardware (e.g., iPad Air 11" M3 / iPadOS 26.5.2).
5. **`Release Qualification`**: Generation of clean Xcode build archive (`.xcarchive`), incremented version/build numbers, release notes, and privacy manifest validation.
6. **`Founder Submission Authorization`**: Explicit, founder-controlled submission approval and execution.

---

## 3. Explicit Release Blockers

Transition to `RELEASE_READY` is **AUTOMATICALLY BLOCKED** if any of the following conditions exist:

- `NATIVE_CONFIG_NOT_QUALIFIED`: Native bundle ID, RevenueCat API key, product IDs, or ASC mappings unverified.
- `NATIVE_PURCHASE_NOT_QUALIFIED`: StoreKit payment sheet presentation or sandbox purchase execution unproven.
- `DEVICE_QUALIFICATION_NOT_QUALIFIED`: Touch target hit-testing unverified on target hardware viewport.
- `SUBMISSION_ELIGIBILITY_NOT_QUALIFIED`: Pre-upload sign-off checklist incomplete.
- `FOUNDER_APPROVAL_ABSENT`: Founder-controlled release authorization withheld.
- `CRITICAL_REGRESSION_DETECTED`: Failure in typecheck, smoke tests, static conformance, or component interaction suite.

---

## 4. Deterministic Decision Algorithm

```text
EVALUATION LOGIC FOR REQUIRED QUALIFICATIONS:
  IF evidence is missing       => Qualification = NOT_YET_QUALIFIED
  IF evidence is contradictory => Qualification = INCONSISTENT_EVIDENCE
  IF evidence satisfies spec   => Qualification = QUALIFIED

RELEASE DISPOSITION ALGORITHM:
  IF EngineeringQualification == QUALIFIED
     AND NativeConfiguration == QUALIFIED
     AND NativePurchase == QUALIFIED
     AND DeviceQualification == QUALIFIED
     AND ReleaseQualification == QUALIFIED
     AND FounderSubmission == APPROVED
  THEN
     OverallDisposition = RELEASE_READY
  ELSE
     OverallDisposition = WITHHELD
```

---

## 5. Machine-Readable & Human-Readable Evidence Schema

Every release candidate must generate two complementary evidence artifacts:
1. **Human-Readable Qualification Report** (`docs/founder/BUILD_<N>_QUALIFICATION_REPORT.md`)
2. **Machine-Readable Qualification JSON** (`coordination/evidence/build_<N>_qualification.json`)

---

## 6. Evidence Retention Policy

Post-release, the following qualification artifacts **MUST** be retained in the permanent evidence store (`coordination/evidence/`):

- Governance Specification Version reference (`v1.0.0`).
- Release Qualification Report & SHA-256 Manifest.
- Machine-Readable Qualification JSON.
- Static and dynamic test execution logs (`npm run test:paywall`, `vitest`).
- Native sandbox execution screenshots and screen recordings.
- App Store Connect submission receipts and build metadata.
- TestFlight internal validation records.
- Signed founder approval records and release gate attestations.
