# SWARM-4 Truth-Item Triage — HJOS / J-Space CONTRADICTED consensus

Holder: `swarm/truth-items` · Generated: 2026-07-15 (~16:2x UTC) · Doctrine: RUNTIME TRUTH, NO FAKE GREEN, fail-closed.

## 0. Method / provenance
- Live API `http://127.0.0.1:8770` is not network-reachable from the analysis VM, but it is a pure
  read-through over `coordination/jspace/*` and `coordination/**`. All values below were read
  **directly from those authoritative source files** (the same bytes the API serves) and by
  **re-running the real observers read-only** (`/tmp/verify_swarm4.py`, no ledger/health writes).
- Overall consensus at last live cycle (`coordination/jspace/health.json`, cycle `JCYC-20260715-5514F4`,
  observed `2026-07-15T15:42:43Z`): **overall = CONTRADICTED, promotion_authority = NONE,
  recommended_action = WITHHOLD_PROMOTION.** This remains the honest outcome after this workstream.

## 1. How the numbers are actually produced (so we resolve the right thing)
- `/brain` shows **latest assessment per (observer, subject)** from the append-only ledger
  (`assessments.jsonl`). A subject that goes red and is never re-emitted **latches red forever**.
- `health.json.overall` is recomputed **fresh each cycle** by `MetaObserver.reconcile()` (worst-wins over
  the assessments emitted *in that cycle only*) — NOT the ledger-latest. So a stale ledger-latest red can
  pollute `/brain` **without** driving `overall`.
- **"unresolved_findings": 4206 / "historical_findings": 4207** is an **append-only tally of every
  CONTRADICTED/BLOCKED assessment ever written** (`runner._finding_history`), minus contained. It is NOT
  4206 distinct live defects. The distinct live open subjects are the handful below. This tally is
  immutable history (governance: historical findings immutable, auto-mutation disabled) and must not be
  "reduced" by mutation.

## 2. The 13 (observer, subject) pairs — current verdicts
| Observer | Subject | Verdict | Class |
|---|---|---|---|
| evidence_auditor | canonical_lease_ledger | CONFIRMED_LIVE | ok |
| evidence_auditor | authority_binding_completeness | CONFIRMED_LIVE | ok |
| performance_analyst | dispatch_failure_rate | CONFIRMED_LIVE | ok |
| performance_analyst | live_concurrency | CONFIRMED_LIVE | ok |
| truth_sentinel | runtime_pointer | CONFIRMED_LIVE | ok |
| flow_sentinel | lease_expiry | CONFIRMED_LIVE→CONTRADICTED* | OPEN (real) |
| flow_sentinel | lease_balance | CONFIRMED_LIVE | ok |
| security_sentinel | secret_exposure_scan | CONFIRMED_LIVE | ok |
| **truth_sentinel** | **active_leases_authority** | **CONTRADICTED** | **OPEN (real)** |
| **security_sentinel** | **control_posture** | **BLOCKED** | **OPEN (real)** |
| **truth_sentinel** | **scheduler_instance_consistency** | **CONTRADICTED (stale)** | **RESOLVED (false-red latch)** |
| **flow_sentinel** | **concurrency_pressure** | **BLOCKED (stale)** | **RESOLVED (false-red latch)** |
| meta_observer | helm_jspace_health | CONTRADICTED | DERIVED (worst-wins) |

\* `lease_expiry` was CONFIRMED_LIVE at 15:42Z; the offending lock has since passed its `expires_at`, so a
fresh cycle now reads it as CONTRADICTED — same underlying orphan lock as `active_leases_authority`.

## 3. RESOLVED by evidence — false-red LATCH bugs (source fix, my lane)
Both subjects had a red branch but **no clearing branch**, so a transient red latched permanently in the
ledger-latest `/brain` view even after the condition cleared. This is the same defect class as the
already-blessed GAP-07 "SOAK_FRESHNESS_SOURCE_STALE false-red" fix.

### 3a. `scheduler_instance_consistency` — CONTRADICTED (STALE)
- Stale record: `observed_at 2026-07-15T07:37:40Z`, `claimed_state sched-2a30d75c`, `FOREIGN_LOCKS=3` — a
  **prior scheduler instance**. Current runtime pointer is `sched-7954d2d1`; the current lock carries no
  foreign `scheduler_instance_id`, so `foreign == []`. Old code only emitted this subject inside
  `if foreign:` (no `else`), so the 07:37Z red was never superseded.
- Fix: `backend/jspace/observers/truth_sentinel.py` — added an `elif locks:` clearing branch emitting
  CONFIRMED_LIVE ("no active lock references a foreign scheduler_instance_id"), with transparent
  `matching`/`unlabeled` counts. Detection unchanged: a genuine foreign lock still → CONTRADICTED.

### 3b. `concurrency_pressure` — BLOCKED (STALE)
- Stale record: `observed_at 2026-07-15T15:14:43Z`, `active_locks=9` (a transient spike). Now only 1 real
  lock (`SOAK-HASF-266.lock`; `_fencing_tokens.lock` is a 0-byte non-lock). Old code only emitted inside
  `if len(locks) > 8:` (no `else`), so the red latched.
- Fix: `backend/jspace/observers/flow_sentinel.py` — added `else:` clearing branch emitting CONFIRMED_LIVE
  ("simultaneous lease locks within capacity"). Detection unchanged: >8 locks still → BLOCKED.

**Evidence:**
- Post-fix read-only re-run: `coordination/qa/swarm4/postfix_verification.txt` — both subjects flip
  `CONTRADICTED/BLOCKED → CONFIRMED_LIVE` against the current live snapshot.
- Regression suite (4/4 pass): `tests/test_jspace_latch_clearing.py` → `coordination/qa/swarm4/regression_test.txt`
  (asserts BOTH the clear verdict AND that the red still fires — no weakening).
- Diff: +32 lines, additions only, in the two observer files (`git diff --stat`).

**Live-board caveat (honest):** the HJOS daemon (`scripts/jspace/hjos_daemon.py`) is a persistent loop that
imports the observers **once at startup**; it will not hot-reload this source. So `/brain` keeps showing the
two stale reds until the daemon is **restarted** (owner: SWARM-1 / founder — do NOT restart during the Phase C
soak). The fix is proven correct in isolation; it will take effect on the next clean daemon start.

## 4. OPEN — genuine live findings (NOT flipped; fail-closed is correct)

### 4a. `active_leases_authority` — CONTRADICTED — **OPEN**
- Root cause (evidence-traced): `coordination/leases/SOAK-HASF-266.lock` has `status:"ACTIVE"` but **no
  `authority_decision_id`**, and its `lease_id lease-e2a84747` appears in **no ledger** — not
  `authority_binding_ledger.jsonl`, not `_lease_history.jsonl`, not the soak `task_lease_ledger.jsonl`. It is
  also now **past `expires_at` (15:48:37Z)**. It is an **orphan / stale lock file**.
- The task's *genuine* live lease is `lease-dec2fce2` (binding `AUTH-44d62b6a06cac189`, `ACTIVE`, scheduler
  `sched-7954d2d1` matching the pointer, created 15:38:03Z) — properly authority-bound in the ledger. So the
  work is authorized; the on-disk `.lock` is a stray artifact.
- **Why OPEN, not fixed:** removing/releasing the orphan lock is **orphan-lease hygiene**, which governance
  gates behind founder approval (`health.governance.orphan_lease_hygiene = "manual_approval"`,
  `automatic_quarantine_enabled = false`, `authorizing_policy_id = null`). Deleting the live lock myself would
  mutate live runtime state and violate that gate. The finding correctly holds the gate closed.
- **Owner / action:** founder to authorize orphan-lease hygiene (governed quarantine) OR the soak scheduler
  to release the stale lock on its next sweep. Adjacent to SWARM-2's binding lane; not duplicated here.

### 4b. `control_posture` — BLOCKED — **OPEN** (this is the ~76.9% SECURITY score)
- Root cause: `coordination/security/helm_control_posture.json` → `posture_percent 76.9`, `high_findings 1`,
  `open_findings 3`. The single HIGH is **AU-9 "Protection of Audit Information": `NOT_IMPLEMENTED`, evidence
  "hash chain broken", detail "spend=False rev=True founder=True"** — the spend-ledger audit hash chain is
  broken. (Other two open: `not_implemented=3` controls.)
- **Why OPEN, not fixed:** a broken **audit** hash chain must not be "repaired" by rewriting it — that would
  destroy the evidence of the break and is itself an integrity/governance violation. Genuine remediation
  (rebuild spend-ledger integrity under governance, re-attest) is security-hardening work.
- **Owner / action:** SWARM-2 (Zero-Trust security hardening) / founder. Reference SWARM-2; not duplicated.

### 4c. `helm_jspace_health` (meta) — CONTRADICTED — **DERIVED**
- Worst-wins reconciliation of the specialists. Clears automatically when 4a/4b clear; not independently
  fixable. No action.

## 5. Did consensus move?
- **Live `health.json.overall`: NO — still CONTRADICTED. This is the correct, honest outcome.** It is driven
  by `active_leases_authority` (and now `lease_expiry`), which are genuine and remain OPEN pending founder-gated
  orphan-lease hygiene. Even a perfect clean-up of the two stale latches cannot and must not turn this green.
- **`/brain` per-subject accuracy: IMPROVED at source** — 2 stale latched reds are eliminated by the fix
  (proven in `postfix_verification.txt`); this reaches the live board on the next daemon restart.
- No state was flipped without attached evidence. No immutable historical finding was mutated. The 4206/4207
  historical tally was left untouched.

## 6. Verification-environment caveat (disclosed, not hidden)
The read-only re-run in `postfix_verification.txt` also shows `evidence_auditor/canonical_lease_ledger →
CONTRADICTED`. That is an **artifact of running in the analysis VM**: the runtime pointer stores a **host
absolute path** (`/Users/michaelhoch/...`) that does not exist inside the VM. On the live host this subject is
CONFIRMED_LIVE (confirmed by the live ledger-latest). It is **not** a real finding and **not** a regression
from my change.

## 7. Founder-approval asks
1. **Approve governed orphan-lease hygiene** to release/quarantine `SOAK-HASF-266.lock` (orphan, unbound,
   expired). Until then `active_leases_authority` + `lease_expiry` correctly hold the gate → resolves 4a.
2. **Restart the HJOS daemon at a safe point** (post-soak) so the two false-red latch fixes reach the live
   `/brain`. Owner: SWARM-1.
3. **AU-9 remediation** (spend-ledger audit-chain integrity) is SWARM-2 security-hardening scope → resolves 4b
   and lifts the ~76.9% posture / BLOCKED `control_posture`.

## 8. Files
- Fixes: `backend/jspace/observers/truth_sentinel.py`, `backend/jspace/observers/flow_sentinel.py`
- Test: `tests/test_jspace_latch_clearing.py`
- Evidence: `coordination/qa/swarm4/postfix_verification.txt`, `coordination/qa/swarm4/regression_test.txt`
