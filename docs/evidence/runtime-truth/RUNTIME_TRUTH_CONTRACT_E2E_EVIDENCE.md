# Runtime Truth Contract — End-to-End Wiring Evidence

* **Artifact under test**: Evidence Discipline Baseline + Runtime Truth Contract enforcement
* **Captured (UTC)**: 2026-07-05T18:04:55Z
* **Environment note**: Tests executed under a Linux sandbox `python3`/`node`; the repo `.venv` is a macOS environment and was not the runner. Test code is stdlib-only for Python and dependency-free for the JS helper, so results are expected to reproduce under the local `.venv`. This claim is OBSERVED here, not yet VERIFIED on the local venv.

---

## 1. What was built and wired

| File | Role | State |
|------|------|-------|
| `docs/doctrine/HAS_EVIDENCE_DISCIPLINE_BASELINE.md` | Formal doctrine (enforcement-first, anti-gaming, proportionality, source-of-truth hierarchy, label-state machine) | VERIFIED (exists, referenced) |
| `config/runtime_truth_contract.json` | Machine-readable contract (valid JSON) | VERIFIED |
| `backend/final_verifier/runtime_truth_contract.py` | Contract loader + `RuntimeTruthVerdictGuard` fake-green guard | VERIFIED (7+4 tests) |
| `backend/final_verifier/final_verdict.py` | Guard wired into the live verdict; new `runtime_truth_contract` output section | VERIFIED (constructs + real run) |
| `frontend/runtime_truth_status.js` | UI label-state → chip adapter (only VERIFIED renders green) | VERIFIED (JS harness) |
| `tests/integration/test_runtime_truth_contract.py` | 11 tests over contract + guard | VERIFIED (11 passed) |

Enforcement point: `FinalVerdict.get_final_verdict()` computes a provisional verdict, runs
`RuntimeTruthVerdictGuard.validate_verdict(status, readiness_score)`, and folds the result into
`all_valid`. The guard is fail-open (missing/ambiguous inputs return valid) so it can only tighten
a would-be-green verdict, never loosen a blocked one.

---

## 2. Test evidence

**Python** — `tests/integration/test_runtime_truth_contract.py`: **11 passed** in ~0.04s.
Covers: contract load, source-of-truth hierarchy, only-VERIFIED-renders-green, full-evidence
requirement for VERIFIED, freshness budgets (fail-closed on unknown kind), proportionality tiers,
release-blocker list, and the guard (blocks fake-green, allows legit green at 90, ignores non-green
status, fails open on bad input).

**Drift check** — guard `not_ready_cap = 50.0` is loaded from
`config/readiness_cap_policy.yaml` (`caps.not_ready = 50.0`); `aligned = True`. The guard and the
`ReadinessCapEngine` now read the same single source, so the cap cannot drift.

**JS helper** — CJS harness over `frontend/runtime_truth_status.js`: all 5 cases PASS, including the
seeded fake-green case (`VERIFIED @ 40 -> BLOCKED`). `rendersGreen` is true only for VERIFIED.

**Seeded-fault (guard)** — `test_guard_blocks_fake_green`: a `VERIFIED` claim at readiness `50.0`
and `30.0` is forced to `is_valid=False` with a `fake_green:` violation. This proves the detector
fails the build on an intentional fake-green, per contract principle 4.

---

## 3. Real end-to-end verdict (live DB)

`FinalVerdict().get_final_verdict()` against the live runtime-truth state store returned:

```json
{
  "status": "BLOCKED",
  "readiness_score": 50.0,
  "readiness_caps": [
    "No active release GO source",
    "stale component heartbeat: backend_core",
    "git working tree is dirty"
  ],
  "runtime_truth_contract": { "is_valid": true, "reason": "BLOCKED does not render green", "violations": [] },
  "blocker_reporter": { "blocker_count": 1 }
}
```

Interpretation: the system is honestly `BLOCKED`, not green. The guard correctly no-ops because the
verdict is already non-green (there is nothing to fake). The new contract section is present in the
live output, confirming the wiring is exercised end-to-end.

---

## 4. Mapping to GOAL (`goal_completion_contract.json` → `HAS-HASF-FULL-BUILDOUT`)

| Completion-definition item | Contribution from this work | State |
|----------------------------|-----------------------------|-------|
| "No fake PASS/ONLINE states" | Guard + UI adapter block green unless VERIFIED and above not-ready floor | VERIFIED (unit + e2e) |
| "Tests prove ... doctrine ..." | 11 Python + 5 JS assertions over the doctrine's rules | VERIFIED |
| "PERT dashboard shows current project truth" | UI chip adapter enforces label-state truth; not yet mounted into `index.html` | PARTIAL / UNKNOWN |
| "All high-risk actions require approval" | Proportionality tier T3 requires operator approval (declared in contract) | DECLARED, not yet gate-enforced |

Remaining GOAL items (runtime start reliability, RACI, critical path, sustainment) are outside this
change set and remain as previously tracked.

---

## 5. Honest UNKNOWN / not-done

1. UI adapter (`runtime_truth_status.js`) is built and unit-passing but **not yet mounted** into the
   490KB `frontend/index.html` render path — deliberately deferred as an unverifiable blind edit.
2. Proportionality tiers are declared in the contract but not yet enforced by a live promotion gate
   (T3 approval is policy, not yet code-blocking beyond the existing approval_gate).
3. Local `.venv` reproduction of the test run is expected but not yet observed.

Per doctrine: these are labeled, not asserted as done.
