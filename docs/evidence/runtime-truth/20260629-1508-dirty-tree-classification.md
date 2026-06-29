# Dirty Tree Classification Manifest - 2026-06-29 15:08 LOCAL

This document classifies all modified and untracked files in the Hoch Agent Swarm (HAS) workspace working tree. It outlines which files are source changes, tests, generated evidence, runtime data, or screenshots, and defines their target commit actions.

## 1. Source Code Files (`KEEP_SOURCE`)
*These files represent the core operational logic of the stabilization pass and should be committed.*
- `backend/main.py` -> KEEP_SOURCE (commit)
- `backend/runtime_execution_store.py` -> KEEP_SOURCE (commit)
- `backend/networkops_manager.py` -> KEEP_SOURCE (commit)
- `backend/brain_orchestrator.py` -> KEEP_SOURCE (commit)
- `backend/brain/` -> KEEP_SOURCE (commit)
- `backend/coding_war_room/` -> KEEP_SOURCE (commit)
- `backend/continuous_improvement/` -> KEEP_SOURCE (commit)
- `backend/devices/` -> KEEP_SOURCE (commit)
- `backend/homeops/` -> KEEP_SOURCE (commit)
- `backend/modelops/` -> KEEP_SOURCE (commit)
- `backend/policy/` -> KEEP_SOURCE (commit)
- `backend/qa_director/` -> KEEP_SOURCE (commit)
- `backend/runtime_truth/` -> KEEP_SOURCE (commit)
- `backend/monetization/buyer_signal_tracker.py` -> KEEP_SOURCE (commit)
- `backend/monetization/market_validator.py` -> KEEP_SOURCE (commit)
- `backend/monetization/pricing_tester.py` -> KEEP_SOURCE (commit)
- `backend/monetization/revenue_offer_packager.py` -> KEEP_SOURCE (commit)
- `config/confidence_policy.yaml` -> KEEP_SOURCE (commit)
- `config/planning_theory_hypotheses.yaml` -> KEEP_SOURCE (commit)
- `config/theory_validation_policy.yaml` -> KEEP_SOURCE (commit)
- `frontend/index.html` -> KEEP_SOURCE (commit)
- `frontend/styles.css` -> KEEP_SOURCE (commit)
- `frontend/src/components/hochster/PullRequestAutomationPanel.tsx` -> KEEP_SOURCE (commit)
- `playwright.config.ts` -> KEEP_SOURCE (commit)
- `scripts/anti_fake_gate.sh` -> KEEP_SOURCE (commit)
- `scripts/scan_hardcoded_status.sh` -> KEEP_SOURCE (commit)
- `server/` -> KEEP_SOURCE (commit)

## 2. Test Code Files (`KEEP_TEST`)
*These files verify the correctness of the active test baseline and should be committed.*
- `tests/e2e/*.spec.ts` -> KEEP_TEST (commit - classified & updated specs)
- `tests/integration/test_runtime_truth_source_map.py` -> KEEP_TEST (commit)
- `tests/unit/brain/` -> KEEP_TEST (commit)
- `tests/unit/test_claim_guard.py` -> KEEP_TEST (commit)

## 3. Evidence Reports (`KEEP_EVIDENCE`)
*These files represent official audit artifacts and compliance logs for the release candidate and should be committed.*
- `docs/evidence/runtime-truth/` -> KEEP_EVIDENCE (commit)
- `docs/evidence/monetization/` -> KEEP_EVIDENCE (commit)
- `docs/evidence/brain/` -> KEEP_EVIDENCE (commit)
- `docs/evidence/qa-automation/qa_report.json` -> KEEP_EVIDENCE (commit)
- `docs/evidence/release-readiness/readiness_checklist.json` -> KEEP_EVIDENCE (commit)
- `docs/evidence/runtime/stability_report.json` -> KEEP_EVIDENCE (commit)
- `docs/evidence/security-gates/security_report.json` -> KEEP_EVIDENCE (commit)

## 4. Generated Artifacts (`GENERATED_ARTIFACT`)
*These are locally compiled or staged build files; they should not be committed to the VCS (except tailwind.css).*
- `frontend/dist/tailwind.css` -> GENERATED_ARTIFACT (ignore / do not commit)
- `frontend/app.js` -> GENERATED_ARTIFACT (ignore / do not commit)
- `artifacts/promptbrain/` -> GENERATED_ARTIFACT (ignore / do not commit)
- `artifacts/promptqa/` -> GENERATED_ARTIFACT (ignore / do not commit)
- `artifacts/qa/` -> GENERATED_ARTIFACT (ignore / do not commit)

## 5. Runtime and Mock Data (`RUNTIME_DATA`)
*These are dynamic databases, heartbeats, task feeds, or media playlists that change at runtime; they should not be committed.*
- `backend/task_history.json` -> RUNTIME_DATA (ignore)
- `backend/db/networkops_healing_ledger.json` -> RUNTIME_DATA (ignore)
- `backend/db/networkops_incidents.json` -> RUNTIME_DATA (ignore)
- `data/demo_config.json` -> RUNTIME_DATA (ignore)
- `data/production_tracker.json` -> RUNTIME_DATA (ignore)
- `data/prompt_registry/` -> RUNTIME_DATA (ignore)
- `data/tv_epg.xml` -> RUNTIME_DATA (ignore)
- `data/tv_playlist.m3u` -> RUNTIME_DATA (ignore)
- `data/backups/` -> RUNTIME_DATA (ignore)
- `data/qa_loop.log` -> RUNTIME_DATA (ignore)
- `frontend/data/runtime_reliability.json` -> RUNTIME_DATA (ignore)
- `frontend/data/agent_registry.json` -> RUNTIME_DATA (ignore)

## 6. Screenshots (`SCREENSHOT_ARTIFACT`)
*Visual proof of dashboard liveness; committed only if operator requires hard evidence, otherwise excluded.*
- `a_wide_high_detail_ui_dashboard_screenshot_conc.png` -> SCREENSHOT_ARTIFACT (ignore)
- `docs/evidence/screenshots/` -> SCREENSHOT_ARTIFACT (exclude/keep local)

## 7. Temporary / Unwanted Files (`TEMP_REMOVE`)
*Scratch analysis files generated during the layout audit; safe to delete.*
- `scripts/count_divs.py` -> TEMP_REMOVE (delete)
- `scripts/tag_legacy_tests.py` -> TEMP_REMOVE (delete)
