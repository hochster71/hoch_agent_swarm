# HAS/HASF Global Project Registry Evidence (2026-06-30)

## Overview
This document records the implementation, execution, and verification of **T010 (Deduplicate and Classify)** and **T011 (Build Global Project Registry)**.

## dedupe_candidates and duplicate_groups (T010)
We ran the deduplication pipeline on raw crawls from GitHub, Local filesystem, and Cloud drives.
- **Discovered Duplicate Groups**: 13 groups
- **Merges Requiring Review**: 1 group (`hoch_agent_swarm` vs `hoch_agent_swarm_prompt_library`)
- **Normalized Canonical Assets**: 66 candidates

## Master Project Registry & Candidates (T011)
We compiled the canonical master registry into JSON and SQLite backends.
- **SQLite Database**: `has_live_project_tracker/data/global_project_registry.sqlite`
- **Monetization Candidates**: 6 candidates (including `dynasec-stripe-webhook`, `agentic-radar`, `autoforge`)
- **DevSecOps Target**: 1 scan target (`hoch_agent_swarm` due to uncommitted local files)
- **Top Registry Gaps**: Missing README, tests, or uncommitted files in canonical assets.

## Verification & Testing
* **Playwright Suite**: `tests/e2e/has-hasf-live-tracker-registry.spec.ts` verifies `/api/registry` and `/api/dedupe` APIs, the new Global Registry layout rendering, duplicate lists, monetization highlights, tooltips, and detail drawers.
* **CLI Reports**: Verified using `./scripts/tracker_dedupe_report.sh` and `./scripts/tracker_registry_report.sh`.
* **Tests Verdict**: `tests/e2e/has-hasf-live-tracker-registry.spec.ts` passes successfully in 2.8s.
