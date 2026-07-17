# HELM 100% Verification Scorecard

**Run:** 2026-07-17T12:53:01Z (UTC)
**Runner:** HELM verification agent (READ-ONLY except this report)
**Sandbox:** Linux, node v22.22.3 / npm 10.9.8 / python 3.10.12 / pytest 9.1.1
**Repo:** /Users/michaelhoch/hoch_agent_swarm
**Doctrine:** NO FAKE GREEN — every GREEN below was actually executed; every RED/BLOCKED carries real evidence and was NOT marked green.

---

## Bottom line

**8 of 10 categories GREEN · 2 RED/BLOCKED.**
**Product test suites that ran: 45 / 45 passed (4 of 5 products).** One product (cyberqrg-ai) could not run — jest not installed and this run is read-only (no `npm install`).
**Repo governance pytest: NOT cleanly runnable in this sandbox** — 1426 tests collect, but 9 modules fail import (missing `crewai` + runtime deps) and multiple tests hang on network/subprocess. Confirmed-passing sample executed here: 69 / 69 (test_trial_preflight 59, first-6 top-level files 10), 0 failed.

---

## Scorecard

| # | Category | Verdict | Evidence / exact numbers |
|---|----------|---------|--------------------------|
| 1 | Product · hff-runway (`npm test`) | 🟢 GREEN | 11 tests, **11 pass / 0 fail**, exit 0 (node --test) |
| 2 | Product · hff-invoice-aging (`npm test`) | 🟢 GREEN | 10 tests, **10 pass / 0 fail**, exit 0 (node --test) |
| 3 | Product · hrf-clarity-briefs (`pytest tests/`) | 🟢 GREEN | **12 passed / 0 failed** in 0.10s, exit 0 |
| 4 | Product · hmf-cue-library (`npm test`) | 🟢 GREEN | license-gate 7 pass + webhook 5 pass = **12 pass / 0 fail**, exit 0 |
| 5 | Product · cyberqrg-ai (`npm test` → jest) | 🔴 BLOCKED | `node_modules` ABSENT → `jest: not found`, exit 127. 7 test cases defined (schema 2, securityPolicy 3, uiSmoke 2) but **NOT RUN**. Read-only run: no `npm install` performed. |
| 6 | Repo governance · `pytest tests/` | 🔴 PARTIAL/BLOCKED | **1426 tests collected**; **9 modules fail collection** (`ModuleNotFoundError: crewai` + related runtime deps not installed in sandbox: test_artifact_validation, test_brain_runtime_compliance, test_crew_smoke, test_entry_points, test_manifest_alignment, test_model_router, test_promptqa, test_run_report, test_swarm_pipeline). Full suite **cannot complete** — several `tests/integration` + scattered tests hang on network/subprocess. Confirmed-passing sample run here: **69 / 69 pass, 0 fail** (test_trial_preflight 59/59; first-6 top-level files 10/10). |
| 7 | Orchestration · `bash -n factory_to_money.sh` | 🟢 GREEN | Syntax OK (SYNTAX_OK) |
| 8 | Orchestration · factory_readiness.py compile + run | 🟢 GREEN | `py_compile` OK; executed to readiness board, **exit 0** |
| 9 | Orchestration · liveness_producer.py compile | 🟢 GREEN | `py_compile` OK |
| 10 | Manifest integrity · registry + backlog | 🟢 GREEN | `product_registry.json` parses (5 products); `product_backlog.json` parses. Rung counts below. |

---

## Category 10 detail — products by monetization rung (from product_registry.json)

Registry: `coordination/products/product_registry.json` · Backlog: `coordination/products/product_backlog.json` (both parse clean).

| product_id | monetization_rung | revenue_state |
|---|---|---|
| EPIC_FURY_2026 | 4_SELLABLE | PENDING_SETTLEMENT |
| HSF_STORY_STUDIO | 4_SELLABLE | NOT_STARTED |
| HFF_INVOICE_AGING | 3_PRODUCTIZED_CODE_COMPLETE | NOT_STARTED |
| HFF_RUNWAY_PACKET | 3_PRODUCTIZED_DEFINED_ONLY | NOT_STARTED |
| HMF_CUE_LIBRARY | 3_PRODUCTIZED_DEFINED_ONLY | NOT_STARTED |

**By rung:** 4_SELLABLE ×2 · 3_PRODUCTIZED_CODE_COMPLETE ×1 · 3_PRODUCTIZED_DEFINED_ONLY ×2. (No product at rung 5 EARNING — consistent with NO FAKE GREEN: no settled dollar yet.)

---

## What blocks 100% green (honest gaps, not cosmetic)

1. **cyberqrg-ai has no installed test harness in this sandbox.** Its `node_modules` is absent, so `jest` cannot run. A read-only verification cannot install it. To close: `cd products/cyberqrg-ai && npm install && npm test` in a write-enabled run.
2. **Repo governance pytest is not runnable end-to-end here.** The full runtime dependency stack (`crewai` and friends) is not installed in this Linux sandbox, and several integration tests hang on network/subprocess. 1426 tests collect and the pure-logic sample that ran passed 69/69, but a true full total requires the app's `uv`/venv environment (`uv run pytest tests/`) with network access. This is an **environment limitation**, reported as such — not asserted green.

## What is genuinely green (executed, evidence-backed)

- 4 of 5 product test suites: **45/45 passing**, zero failures.
- All 3 orchestration checks: factory_to_money.sh syntax, factory_readiness.py compile+run (exit 0), liveness_producer.py compile.
- Manifest integrity: both JSON manifests parse; 5 products classified by rung.
