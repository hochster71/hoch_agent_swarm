# Validation Command Stdout Evidence

This document captures verbatim terminal outputs for all system status verifier scripts, unit tests, and integration build validations.

---

## 1. Private-First Doctrine Auditor

* **Command**: `python3 scripts/verify_private_first_doctrine.py`
* **Exit Code**: `0`
* **Output**:
```text
PRIVATE_FIRST_DOCTRINE: GO
```

---

## 2. Autonomy Daemon Burn-In Validator

* **Command**: `python3 scripts/verify_ag_execution_burn_in.py`
* **Exit Code**: `0`
* **Output**:
```text
Executing master AG Execution Burn-In Validator...
Verdict derived: RUNTIME_PROOF_CONDITIONAL_GO
Phase E Verdict: PHASE_E_TEST_MODE_GO
  Real Cycles: 0
  Simulated Cycles: 26
  Duplicates: 0
  Missing Proofs: 0
  Failed Real Rate: 0.00
  Elapsed Hours: 0.0104
🟢 AG Burn-In verification succeeded.
✅ AG Burn-In verification PASSED with verdict: RUNTIME_PROOF_CONDITIONAL_GO
```

---

## 3. Apple Compliance Preflight Gate

* **Command**: `python3 scripts/verify_appstore_preflight.py`
* **Exit Code**: `0`
* **Output**:
```text
Executing Apple Compliance Preflight Gate...
🟢 Apple Compliance Preflight verification succeeded.
✅ Apple Compliance Preflight verification PASSED with verdict: APPSTORE_PREFLIGHT_GO
```

---

## 4. K-Track Ledger Sync & Verifier

* **Command**: `python3 scripts/verify_k_track_ledger.py`
* **Exit Code**: `0`
* **Output**:
```text
Executing K-Track Ledger Verification...
Verdict derived: K_TRACK_BLOCKED
🟢 K-Track Ledger verified and synced cleanly.
✅ K-Track Ledger verification PASSED with verdict: K_TRACK_BLOCKED
```

---

## 5. Three-Lane PERT Reconciler

* **Command**: `python3 scripts/verify_three_lane_pert_reconciliation.py`
* **Exit Code**: `0`
* **Output**:
```text
Executing Three-Lane PERT Reconciliation Validator...
Verdict derived: CONDITIONAL_GO
🟢 PERT task graph is fully reconciled and verified.
✅ Three-lane PERT verification PASSED.
```

---

## 6. Burn-In Launch Readiness Validator

* **Command**: `python3 scripts/verify_burn_in_launch_readiness.py`
* **Exit Code**: `0`
* **Output**:
```text
Executing Burn-In Launch Readiness Verification...
Verdict derived: CONDITIONAL_READY_HOST_PENDING
🟢 Burn-In Launch Readiness verified successfully.
✅ Burn-in launch readiness verification PASSED with verdict: CONDITIONAL_READY_HOST_PENDING
```

---

## 7. Python Unit Test Suites

* **Command**: `uv run pytest tests/prompt_brain -vv`
* **Exit Code**: `0`
* **Outcome**: **143 passed, 77 warnings** (100% success rate).

---

## 8. Frontend Integration Pipeline Build

* **Command**: `npm run ci:validate`
* **Exit Code**: `0`
* **Outcome**: **FULL INTEGRATION PIPELINE COMPLETED SUCCESSFULLY** (100% success rate).
