# Runtime Truth Audit Report - 2026-06-29 18:55 UTC

This audit identifies the exact sources, integrity states, and contradiction risks for all key dynamic status variables in the Hoch Agent Swarm (HAS) dashboard interface.

## Telemetry Audit Results

| Indicator / UI Label | Exact Source File / API / Table | Source Type | Last Updated | Evidence Link / Hash | Contradiction Risk | Fix / Remediation Action |
|---|---|---|---|---|---|---|
| **RC30 Tracker** | `frontend/index.html` (DOM ID `#checklist`) | `fallback_json` | 2026-06-29T18:00:00Z | None | High (Can show PASS while backend checks fail) | Rebind dynamically to the `sqlite3` `qa_runs` table |
| **Readiness 100%** | `readiness_calculator.py` | `sqlite` | 2026-06-29T18:50:00Z | `/api/v1/runtime-truth/state` | High (Falsely implies release-ready status) | Applied safety score caps (git dirty caps overall score at 90%) |
| **STATUS NO-GO** | `contradiction_detector.py` | `sqlite` | 2026-06-29T18:50:00Z | `/api/v1/runtime-truth/contradictions` | Low | Automatically blocks any production execution path |
| **GO FOR SWARM** | `backend/main.py` | `live_api` | 2026-06-29T18:50:00Z | None | Medium | Disables capability execution if any blocker is active |
| **git status clean NO** | `collector.py` using `git status --porcelain` | `script` | 2026-06-29T18:50:00Z | None | Low | Classifies dirty tree state and applies corresponding caps |
| **Monetization LAUNCH_READY** | `backend/monetization` | `sqlite` | 2026-06-29T18:50:00Z | `/api/v1/monetization/offers` | High (Hardcoded mock value risk) | Capped at 40% until a verified buyer profile is generated |
| **Planning Theory Proof Board** | `backend/main.py` | `sqlite` | 2026-06-29T18:50:00Z | None | Low | Read-only SQLite query alignment |
| **Stale Release Gov Views** | `frontend/index.html` (`#view-governance`) | `legacy-compatibility` | 2026-06-29T18:40:00Z | None | High (Falsely implies active control plane) | Moved off-screen and tagged with `data-truth-status="not-live"` |
| **Candidate Packet Compat** | `frontend/index.html` (`#candidate-release-packet-panel`) | `legacy-compatibility` | 2026-06-29T18:40:00Z | None | High | Moved off-screen and tagged with `data-truth-status="not-live"` |

## Audit Integrity Check
- Cryptographic hash-chain auditing engine successfully verified: **PASS**
- Overall runtime health state: **GO BLOCKED** (uncommitted local git modifications present).
