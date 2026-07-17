# Performance & Runtime Resilience Report — Phases 10–11

## 1. Performance

### Measured / observed this audit

| Metric | Result |
|---|---|
| Gateway lmstudio latency | ~1049.9 ms (status sample) |
| Mission API freshness | 0.0 s recompute path |
| Concurrent soak peak (historical packages) | **4** workers (configured capacity 4) |
| Spend ledger scale | 15,428 rows |
| 100 / 500 / 1000 missions load test | **NOT RUN** |
| 100 / 1000 agents load test | **NOT RUN** |
| Queue depth under load | **UNKNOWN** |
| Memory/CPU profiling of HELM under load | **NOT RUN** (process list only) |

### Historical concurrency report fields (sample)

`concurrency_mode`, `configured_limit`, `structural_capacity`, `observed_peak_concurrency`, `effective_limit` — packages exist (14 concurrency_report.json files).

**Performance verdict:** **NOT VERIFIED at claimed enterprise scale.** Only small concurrency (4) historically exercised in soak seals.

**Performance Score: 25 / 100** (instrumentation exists; scale proof absent).

---

## 2. Resilience / Kill Scenarios

| Kill target | This audit | Historical evidence | Verdict |
|---|---|---|---|
| Backend API | Not killed | — | **UNKNOWN** recovery time |
| Mission engine writer | Not killed | Multi-writer design | **UNKNOWN** |
| Scheduler / leases | Not killed | Soak FAIL on DB lock, dangling lease, stranded locks | **KNOWN PAST FAILS** |
| Factory worker | Not killed | fencing SIGKILL claim CP-10 | **NOT RE-PROVEN** |
| Model provider | Not killed | multi-backend design | **UNKNOWN** failover |
| Network / relay | Relay HTTP 302 only | — | **UNVERIFIED** |
| Filesystem corruption | Not injected live | quarantine corrupt DB exists | Recovery path **PARTIAL** |
| Redis | Not identified as core dependency on Mac path | — | **NA/UNKNOWN** |

### Soak verdict inventory (seal_verdict.json)

| Verdict | Count |
|---|---:|
| SOAK_PHASE_A_FAIL | 5 |
| SOAK_PHASE_A_SUPERSEDED | 6 |
| SOAK_PHASE_A_PASS | 1 |
| SOAK_PHASE_B_PASS | 1 |
| SOAK_PHASE_B_SUPERSEDED | 1 |
| SOAK_PHASE_C_FAIL | 1 |
| SOAK_PHASE_C_INCONCLUSIVE | 1 |
| SOAK_PHASE_C_SUPERSEDED | 1 |
| SOAK_PHASE_SMOKE3_PASS | 1 |

**Citable PASS-class packages without `may_be_cited_as_evidence: false`:** low (≈3).  
**24×7 continuous autonomous operation: NOT PROVEN.**

### Resilience Score: **40 / 100**

Culture of honest FAIL/SUPERSEDE is a strength. Continuous recovery under sustained load is not proven.
