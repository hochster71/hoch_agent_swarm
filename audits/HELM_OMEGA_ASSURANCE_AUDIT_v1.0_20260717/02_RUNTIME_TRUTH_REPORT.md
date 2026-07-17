# Runtime Truth Report — HELM OMEGA ASSURANCE AUDIT v1.0

## Doctrine Applied

- Runtime overrides documentation.
- Identical truth required across consumers.
- Missing evidence = NOT VERIFIED.
- Fail-closed required on corruption / staleness / missing sources.

---

## 1. Candidate Authoritative Sources

| Candidate | Path / Endpoint | Freshness (audit time) | Authority claim |
|---|---|---|---|
| Mission state (disk) | `coordination/goal/mission_state.json` | Fresh (~0h age at generation) | “Single operational state” in code docstring |
| Goal state | `coordination/goal/goal_state.json` | Fresh (same cycle) | Requirement scoring engine |
| Active runtime source | `coordination/council/active_runtime_source.json` | 2026-07-17T12:43:23Z | Points to native cadence, not soak |
| Control posture | `coordination/security/helm_control_posture.json` | 2026-07-15 | NIST subset self-assessment |
| Brain runtime truth | `has_live_project_tracker/data/brain_runtime_truth.json` | 2026-07-14 STALE | Tracker |
| Factory runtime truth | `has_live_project_tracker/data/factory_runtime_truth.json` | 2026-07-14 STALE | Tracker |
| Source authority manifest | `has_live_project_tracker/data/source_authority_manifest.json` | **STALE** since 2026-07-03 | NAICS/O*NET/BLS |
| HOCH_STATUS.md | session artifact | 2026-07-07 STALE | Human-facing “start here” |
| Coordination bus | `coordination/coordination_bus.json` | Heartbeats 2026-07-09 | Inter-agent link |

### Authoritative mission operational state (this audit’s determination)

**Primary:** `coordination/goal/mission_state.json` produced by `backend.mission_control.mission_state.write_mission_state`, refreshed by goal engine / runtime_refresher / live API recomputation.

**Live consumer verified:** `https://127.0.0.1:8770/api/v1/helm/mission`  
- `truth_class=HELM_MISSION_STATE`  
- `source=coordination/goal/mission_state.json`  
- `freshness_seconds=0.0`  
- overall status matches disk: **`BLOCKED_EXTERNAL` / REQ-GOV-002**

**Not primary:** `:8000` main API does **not** expose the same mission route (404 on `/api/mission/state`).

---

## 2. Consumer Coherence Matrix

| Consumer | Path to truth | Same as mission_state? | Evidence |
|---|---|---|---|
| HELM LIVE mission API | `write_mission_state()` → disk + response | **YES** (live match) | curl/urllib 200 |
| HELM LIVE executive | `/api/v1/helm/mission/executive` | Intended yes | route present in OpenAPI |
| Voice briefing | imports `write_mission_state` | Intended yes | code reference |
| Voice router | imports `write_mission_state` | Intended yes | code reference |
| Independent validator | recomputes + injects faults | **VERIFIED_WITH_LIMITATIONS** | 57/64 checks; 7 FAIL |
| Main API `:8000` | separate surface | **NO single mission route** | 404 probes |
| Dashboard HTML (validator) | HTTP fetch | **FAIL during validation run** | connection closed |
| Brain live `:8000/api/brain/live` | model gateway truth | **Different truth domain** | 200 live brain |
| Tracker brain/factory truth JSON | files | **STALE (2026-07-14)** | mtime |
| Factory registry readiness | JSON | **Conflicts readiness board** | READY vs rung 1 |
| HOCH_STATUS | markdown | **STALE** | dates |
| Coordination bus ONLINE labels | JSON | **Stale heartbeats** | 2026-07-09 |

**Conclusion:** Mission state has a **strong intended single-writer/single-document design**, and the HELM LIVE path is coherent. **Portfolio-wide identical runtime truth is NOT achieved.** Multiple consumers still read divergent or stale artifacts.

---

## 3. Fail-Closed Injection Results

### 3.1 Independent validator (`scripts/validation/validate_mission_state_independent.py`)

| Injection / class | Result |
|---|---|
| Stale speech sync | PASS (no fake GO) |
| Empty goal → no fake GO | PASS (`BLOCKED_EXTERNAL` / UNKNOWN engineering) |
| Missing sources fail closed | PASS |
| Missing eng not VERIFIED | PASS (`UNKNOWN`) |
| Malformed JSON fail closed | PASS |
| Voice deploy/spend/keys refuse | PASS (DOORSTEP) |
| Voice HTTP mission | **FAIL** (connection closed) |
| Dashboard HTML served | **FAIL** (connection closed) |
| Unit regression | PASS (30 passed reported) |

**Overall validator verdict:** `VERIFIED_WITH_LIMITATIONS` — **passed=57 failed=7**

### 3.2 Unit fail-closed suite (executed this audit)

```
pytest tests/test_capability_gate_fail_closed.py tests/unit/test_mission_state.py tests/test_security_hardening.py
→ 28 passed
```

### 3.3 Injections NOT re-run end-to-end this audit

| Injection | Status |
|---|---|
| Corrupt JSON on live API under load | NOT RE-RUN (unit/validator cover engine) |
| Invalid hashes in soak package promotion | Partially covered historically (supersession exists) |
| Offline builders | NOT RE-RUN |
| Unknown factory dispatch | NOT RE-RUN live |
| Broken adapters | NOT RE-RUN live |

**Missing live injection evidence remains UNKNOWN for those cells — not inferred PASS.**

---

## 4. Runtime Topology Issues

### 4.1 Dual/competing truth clocks

- `runtime_refresher` (PID observed) publishes `active_runtime_source.json` noting native cadence, **no soak active**.
- Historical soak packages still present and easy to mis-cite.
- Goal engine can report `north_star_completion: 100.0` while mission overall is blocked.

### 4.2 Stale “truth” files still on disk

`source_authority_manifest.json` status **STALE** with age_seconds ≈ 966452 (~11 days) — yet sources marked `allowed_for_live_ui: true`. This is a **fail-open UI risk** if UIs consume it without age gates.

---

## 5. Runtime Truth Score: **62 / 100**

| Strength | Weakness |
|---|---|
| Mission state recomputable | Multi-port consumer fragmentation |
| Live 8770 matches disk | 8000 ≠ mission surface |
| Fail-closed tests exist and largely pass | Dashboard/HTTP path failures in validator |
| Honest BLOCKED/UNKNOWN statuses | Stale tracker manifests still “allowed” |
