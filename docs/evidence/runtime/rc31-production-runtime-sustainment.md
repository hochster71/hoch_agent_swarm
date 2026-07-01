# Production Runtime Sustainment Evidence — RC31

**Epic:** HOCH-200  
**RC:** RC31  
**Branch:** `rc31-production-runtime-sustainment`  
**Date:** 2026-07-01  
**Author:** automated (antigravity/RC31)

---

## 1. Release Invariants & Provenance Baseline

This validation ledger registers the post-release sustainment evidence for version **v0.1.7** under the branch `rc31-production-runtime-sustainment`.

- **Release Tag:** `v0.1.7` (strictly fixed at `face8ce`, not modified)
- **Master Branch Baseline HEAD:** `84b0600`
- **Sustainment Checks Executed:** `scripts/rc31_sustainment_verify.sh`
- **Verdict:** **SUCCESS / PASS**

---

## 2. Gate Verification Checklist

| Gate / Check | Target / Condition | Status | Detail |
|--------------|--------------------|--------|--------|
| **Tag Location Integrity** | Tag `v0.1.7` must point to `face8ce` | **PASS** | Checked via `git rev-parse v0.1.7` |
| **Doctrine DB Schema** | `doctrine_rules` table verified | **PASS** | `verify_doctrine_db.py` exits 0 (74 rules active) |
| **Local API Health** | `/api/mission/brief` active | **PASS** | Returns HTTP 200 and operational statistics |
| **Relay Status Proxy** | `/api/v1/relay/status` active | **PASS** | Returns `HAS-WORKER-RELAY-001` with status `ONLINE` |
| **Public Port Closed** | Port 3012 unreachable on VPS public IP | **PASS** | Socket connection to `50.116.41.183:3012` times out |
| **E2E Playwright RC26** | `rc26-relay-routing.spec.ts` passes | **PASS** | 13/13 passed |
| **E2E Playwright RC28** | `rc28-mission-execution-proof.spec.ts` passes | **PASS** | 16/16 passed |
| **Git Working Tree Clean**| Status is clean after committing deliverables | **PASS** | Checked via `git status` |

---

## 3. Automated Check Execution Logs

```
======================================================================
          RC31 Sustainment Verification: v0.1.7 Production
======================================================================
Checking tag placement...
  [PASS] Tag v0.1.7 points to face8ce 
Checking API mission brief...
  [PASS] Local API /api/mission/brief 
Checking API relay status...
  [PASS] Local API /api/v1/relay/status (Contains HAS-WORKER-RELAY-001)
Running full release check suite...
======================================================================
         RC29 Release Verification: Swarm Relay & Computing
======================================================================
Base URL: http://localhost:8000
VPS IP:   50.116.41.183
======================================================================
Running Check 1: Doctrine DB verification...
  [PASS] Doctrine DB Table Verification 
Running Check 2: RC26 Playwright E2E regression suite...
  13 passed (6.0s)
  [PASS] RC26 Playwright Test Suite 
Running Check 3: RC28 Playwright E2E mission proof suite...
  16 passed (5.4s)
  [PASS] RC28 Playwright Test Suite 
Running Check 4: Port 3012 Public Exposure Check...
REFUSED_OR_TIMEOUT: timed out
  [PASS] VPS Public Port 3012 Exposure (Port is closed/unreachable)
Running Check 5: Git dirty state check...
  [PASS] Git Working Directory Clean 
======================================================================
  >> SUCCESS: All release gates for RC25-RC28 are fully verified!
======================================================================
  [PASS] RC29 Verification Suite 
======================================================================
  >> SUCCESS: Production runtime sustainment is verified!
======================================================================
```

---

## 4. Final Operational Signoff

**RC31 Verdict:** **FINAL_GO**

All checks pass successfully. Post-release operational posture for v0.1.7 is healthy, and the git tag remains correctly locked at `face8ce`. Branch is ready for merge.
