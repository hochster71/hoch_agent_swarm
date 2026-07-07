# HOCH Vocabulary — a SCOREBOARD, not a description

This is not marketing language. Under HOCH doctrine (No Fake Green), every term is a *claim*,
and a claim is only trusted with evidence. So each canonical term is tagged:

- **IMPLEMENTED** — real code + passing test/evidence. Cite the path.
- **PARTIAL** — partly real; the gap is named. Do not describe it as done.
- **ASPIRATIONAL** — named, not built. A target, not a capability.

A term flips to IMPLEMENTED only via an evidence path AND a change-board approval (re-tag).
If you catch yourself using an ASPIRATIONAL term as if it were real, that is fake-green —
the exact failure this scoreboard exists to prevent.

Legend: ✅ IMPLEMENTED · 🟡 PARTIAL · ⬜ ASPIRATIONAL · ⛔ CONFLICTS WITH DOCTRINE

## Tier 1 — Core doctrine
| Term | Status | Evidence / gap |
|---|---|---|
| Runtime Truth | ✅ | `backend/runtime_governor.py`, `tests/test_no_fake_green_truth_endpoints.py` (10/10 pass) |
| No Fake Green | ✅ | fabricated fleet theater removed (`backend/cluster_manager.py`); `baseline_guard` invariant |
| Evidence-Backed Status | ✅ | computed `24h_go` gate w/ `24h_go_checks` (`infra/hoch-200/vps/relay-api/app.py`) |
| Founder-Only Gate | ✅ | DOORSTEP posture + handoff (`has_live_project_tracker/data/orchestration_bridge_control.json`) |
| Non-Founder Execution | ✅ | policy categories (`has_live_project_tracker/data/ag_execution_policy.json`) |
| Promotion Gate | ✅ | DOORSTEP staging + rung criteria (`ag_execution_runner.py`) |
| Truth Ledger | 🟡 | append-only ledgers exist but PROLIFERATED into 4 names — consolidate to ONE typed ledger |
| Reasoning Graph | 🟡 | `/api/brain/reasoning-graph` endpoint real; is it populated with real reasoning at scale? verify |
| Mission Control Plane | 🟡 | `control_plane_status.json` real but suffered SYNC_STALE; UI partly declared-not-measured |
| Recursive Optimization Loop | 🟡 | HMF/HRF converged on RUBRIC ONLY, zero combat records — ~30% real (`HOCH_STATUS.md`) |

## Tier 2 — Execution engine
| Term | Status | Evidence / gap |
|---|---|---|
| Bounded Autonomy | ✅ | DOORSTEP execution envelope + policy categories |
| Verification Harness | ✅ | pytest suites + `scripts/baseline_guard.py` + `verify_*` |
| Freshness Check | ✅ | `control_plane` max_age/expires; relay telemetry staleness guard |
| Source-of-Truth Contract | 🟡 | `system_of_record` contract exists; sync staleness was a live bug |
| Autonomous Task Routing | 🟡 | policy-category routing + `capability_router`; not yet outcome-driven |
| Critical Path Execution | 🟡 | PERT server (`/api/pert/data`) exists; live critical-path drive unproven |
| Agent Capability Matrix | 🟡 | `config/cluster_worker_profiles.json` has capabilities; many agents DECLARED not measured |
| Release Readiness Gate | 🟡 | gate verdicts exist (Epic Fury NO-GO); not fully green |
| Dependency Graph | 🟡 | present in tracker data; not the live execution driver yet |
| Self-Healing Loop | ⛔ | CONFLICTS: doctrine REMOVED auto-repair/failure-laundering. Rename → "Detect→Diagnose→Propose→Human-Approve" |

## Tier 3 — Factory scaling
| Term | Status | Evidence / gap |
|---|---|---|
| Factory Template | ✅ | the §18 pattern (this term bank) is a usable template |
| DevSecOps Pipeline | 🟡 | CI exists (`.github/`, `has-qa-runner-mac`); security scans used fallbacks (not fully real) |
| Prompt Harness | 🟡 | `data/prompt_brain/*` real; harness/regression coverage partial |
| Artifact Pipeline | 🟡 | `artifacts/crew_runs/*` produced; not uniformly evidence-gated |
| Research Pipeline (HRF) | 🟡 | keyless grounding real; converged on rubric, no combat records |
| Creative Pipeline (HMF) | 🟡 | converged (rubric); `hmf_hrf_paid_execution_allowed: false` |
| Revenue Factory | ⬜ | pre-revenue by design (DOORSTEP). Real when a user can purchase |
| Outcome Factory | ⬜ | still activity-measured, not outcome-measured |
| Workflow Factory | 🟡 | governed loop exists (DOORSTEP); not generalized across factories |
| Knowledge Graph | ⬜ | named, not built |

## Doctrine-conflict terms — DO NOT standardize as written
- **Self-Healing / Recursive Self-Healing / Autonomous Remediation** → these re-introduce the
  auto-repair that faked green and was deliberately removed. Approved form: remediation that
  **stops at a human/founder gate** and never auto-closes a status.

## Consolidation debt (the "71 files" pattern, in vocabulary form)
- FOUR ledger names (Truth / Runtime / Champion Runtime / Evidence) → ONE append-only ledger, typed events.
- SIX memory names → ONE store with typed scopes. Naming ≠ architecture.

## Canonical phrase (keep — but earn every verb)
> Hoch Agent Swarm is a recursive factory operating system: it decomposes goals, routes work to
> agents, verifies outputs against runtime truth, repairs failures, records evidence, and promotes
> only validated artifacts.

Each verb must resolve to a passing test. Today: decompose 🟡, route 🟡, verify ✅, repair ⛔(gate it),
record ✅, promote ✅.

## The rule
Aspirational terms are TARGETS. Watch them flip ⬜→🟡→✅ as HAS gets real. That progression —
not the vocabulary — is the path to /GOAL.
