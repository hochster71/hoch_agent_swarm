# PERT Analysis — HOCH Agent Swarm RC15 Forward Execution

## Executive Summary
This document outlines the Program Evaluation and Review Technique (PERT) analysis performed for the HOCH Agent Swarm v0.1.0-rc15 release track. It defines remaining tasks, task dependencies, critical path, risks, and recommended execution lanes to guarantee a reliable, secure release transition.

## Current Baseline
- **Release Tag**: `v0.1.0-rc15`
- **Latest Commit**: `ce6d3c8`
- **Host Tests**: 554 / 554 tests passing
- **Docker UI status**: Active, healthy, running locally on `http://localhost:8086`
- **Security Posture**: Local-only proxy enabled with strict SSRF filtering on nested playlists/segments.

## Assumptions
1. The Docker Desktop environment remains stable during execution (no additional daemon socket memory-limit crashes).
2. The code changes required for local proxying do not alter external APIs or cause regressions in unrelated modules.
3. Verification is complete prior to executing the final release seal.

## Task Inventory & PERT Estimates
All durations are estimated in hours.

| Task ID | Task Name | Predecessors | Optimistic (O) | Most Likely (M) | Pessimistic (P) | Expected (TE) | Variance (V) |
|---|---|---|---|---|---|---|---|
| **PERT-001** | Confirm RC15 baseline & tree | None | 0.10 | 0.20 | 0.50 | 0.233 | 0.0044 |
| **PERT-002** | Run full host pytest | PERT-001 | 0.20 | 0.30 | 0.50 | 0.317 | 0.0025 |
| **PERT-003** | Run Docker pytest | PERT-001 | 0.20 | 0.40 | 0.80 | 0.433 | 0.0100 |
| **PERT-004** | Start Docker UI & check health | PERT-001 | 0.20 | 0.30 | 1.00 | 0.400 | 0.0178 |
| **PERT-005** | Verify Evidence Brain export | PERT-004 | 0.10 | 0.15 | 0.30 | 0.167 | 0.0011 |
| **PERT-006** | Verify HOCH TV proxy routes | PERT-004 | 0.10 | 0.20 | 0.40 | 0.217 | 0.0025 |
| **PERT-007** | Verify screenshot manifest | PERT-001 | 0.10 | 0.15 | 0.30 | 0.167 | 0.0011 |
| **PERT-008** | Refresh live screenshots | PERT-004, PERT-007 | 0.20 | 0.40 | 0.80 | 0.433 | 0.0100 |
| **PERT-009** | Inspect final reviewer packet | PERT-001 | 0.10 | 0.20 | 0.40 | 0.217 | 0.0025 |
| **PERT-010** | Inspect traceability matrix | PERT-001 | 0.10 | 0.20 | 0.40 | 0.217 | 0.0025 |
| **PERT-011** | Inspect acceptance signoff package | PERT-001 | 0.10 | 0.20 | 0.40 | 0.217 | 0.0025 |
| **PERT-012** | Create CURRENT_STATE handoff | PERT-001 | 0.10 | 0.20 | 0.40 | 0.217 | 0.0025 |
| **PERT-013** | Create PERT artifacts | PERT-002..PERT-011 | 0.50 | 1.00 | 2.00 | 1.083 | 0.0625 |
| **PERT-014** | Seal next release candidate | PERT-012, PERT-013 | 0.10 | 0.20 | 0.40 | 0.217 | 0.0025 |
| **PERT-015** | Prepare next-track proposal | PERT-014 | 0.10 | 0.20 | 0.30 | 0.200 | 0.0011 |

## Critical Path Analysis
The critical path is the longest sequence of dependent tasks that determines the minimum execution time:
$$\text{Critical Path: } \text{PERT-001} \rightarrow \text{PERT-004} \rightarrow \text{PERT-008} \rightarrow \text{PERT-013} \rightarrow \text{PERT-014} \rightarrow \text{PERT-015}$$

- **Total Expected Duration**: **2.567 hours**
- **Total Variance along Path**: **0.0983 hours²**
- **Standard Deviation**: **0.314 hours (~19 minutes)**

## Parallel Execution Lanes
To optimize delivery time, three separate testing lanes can run concurrently:
1. **Host Verification Lane**: Run host tests (`PERT-002`) and inspect reviewer documents (`PERT-009`, `PERT-010`, `PERT-011`).
2. **Containerized Test Lane**: Spin up Docker and run `test-runner` pytest (`PERT-003`).
3. **Screenshot & Health Lane**: Launch local cockpit UI, verify endpoints, and run Playwright screenshot workers (`PERT-004` $\rightarrow$ `PERT-008`).

## Recommended Next Track
Following release sealing of `v0.1.0-rc16`, the team should prioritize a dedicated human auditor dry-run utilizing the operator cockpit simulation controls to test ConMon drift triggers and PromptQA auto-recovery lanes.

## Security & compliance boundary
> [!WARNING]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated. System is local-only unless explicitly configured otherwise.*
