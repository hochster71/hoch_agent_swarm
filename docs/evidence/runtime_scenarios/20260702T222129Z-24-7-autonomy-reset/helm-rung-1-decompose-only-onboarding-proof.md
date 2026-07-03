# HELM Rung 1 Decompose-Only Onboarding Proof

---

## 1. Onboarding Details
* **Founder Spot-Check Status**: `FOUNDER_SPOT_CHECK_PASS`
* **Bridge-Control State**:
  ```json
  {
    "orchestration_bridge_enabled": true,
    "allow_provider_api_calls": false,
    "allow_ag_execution": false,
    "allow_founder_gated_execution": false,
    "max_concurrent_missions": 1
  }
  ```
* **Mission ID**: `mission-0b9c280f`
* **Mission Status**: `DECOMPOSED`
* **Sanitizer Result**: `PASS`
* **Signing Status**: `VALID` (dry-run signing accepted)
* **Decomposition Result**: Success. Bounded task generated.
* **Provider API Calls**: 0 (dry-run mode active)
* **AG Execution Calls**: 0 (execution disabled)
* **Founder-Gated Actions**: Blocked.

---

## 2. Derivation Parameters
* **Copy/Paste Required**: `True`
* **Reason**: `insufficient autonomous mission history`

---

## 3. Promotion & Rollback Criteria
* **Promotion to Rung 2**: Requires at least one clean completed live mission.
* **Rollback Trigger**: Any manual prompt injection or policy gate failure reverts `orchestration_bridge_enabled` to `false`.
