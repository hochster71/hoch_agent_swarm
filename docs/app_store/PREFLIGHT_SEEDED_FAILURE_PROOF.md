# App Store Preflight Seeded Failure Proof

This document provides evidence of the planted-failure proof execution for the Apple Compliance Preflight gate.

## Seeded Mismatch Execution Log

* **Command Executed**: `python3 scripts/verify_appstore_preflight.py --seeded-fail`
* **Execution Timestamp**: 2026-07-05T00:25:58Z
* **Expected Outcome**: Exit Code `1` (Failure detected)
* **Actual Outcome**: Exit Code `1`

### Stdout Output Capture
```text
Executing Apple Compliance Preflight Gate...
❌ Preflight checks failed:
  - Marketing contains autonomy claims but Phase E burn-in is incomplete.
  - [SEEDED FAILURE] Privacy manifest does not declare NSPrivacyCollectedDataTypeLocation tracked in source code.
❌ Apple Compliance Preflight verification failed.
```

## Failure Recovery Validation

When executing without the `--seeded-fail` flag, the privacy manifest is compared against actual white-listed egress classes, and the check passes:

* **Command Executed**: `python3 scripts/verify_appstore_preflight.py`
* **Exit Code**: `0`
* **Output**:
```text
Executing Apple Compliance Preflight Gate...
🟢 Apple Compliance Preflight verification succeeded.
✅ Apple Compliance Preflight verification PASSED with verdict: APPSTORE_PREFLIGHT_GO
```
