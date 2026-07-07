# Final Pre-Commit Truth Gate

## Staged files
A	backend/brain/live_runtime_aggregator.py
A	backend/brain/runtime_truth_validator.py
M	backend/main.py
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/SUMMARY.md
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/after_state.txt
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/before_state.txt
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/bootout_decision.md
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/bootout_results.txt
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/critical_survival_check.txt
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/kill_process_group_results.txt
A	docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/rollback_bootin_commands.sh
A	docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/SUMMARY.md
A	docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/diff_review.txt
A	docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/restart_fastapi.txt
A	docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/runtime_verify.txt
A	docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/targeted_tests.txt
A	docs/evidence/runtime/post_containment_truth_endpoint_wiring.md
A	docs/evidence/runtime/source_authority_reasoning_graph_cleanup.md
A	docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/VERIFY.md
A	docs/evidence/runtime/staging_manifest_truth_gate_rebuilt_20260707T015149Z/REVIEW.md
A	docs/evidence/runtime/staging_manifest_truth_gate_rebuilt_20260707T015149Z/stage_allowlist.txt
A	has_live_project_tracker/data/brain_runtime_truth.json
A	has_live_project_tracker/data/factory_runtime_truth.json
A	has_live_project_tracker/data/reasoning_graph.json
A	has_live_project_tracker/data/source_authority_manifest.json
A	tests/test_brain_truth_endpoints.py
A	tests/test_factory_runtime_truth.py
A	tests/test_live_runtime_truth_validator.py
A	tests/test_no_fake_green_truth_endpoints.py
A	tests/test_reasoning_graph.py

## Staged diff stat
 backend/brain/live_runtime_aggregator.py           | 186 ++++++++++++++
 backend/brain/runtime_truth_validator.py           | 268 +++++++++++++++++++++
 backend/main.py                                    |  69 ++++++
 .../SUMMARY.md                                     |  16 ++
 .../after_state.txt                                |  10 +
 .../before_state.txt                               |  16 ++
 .../bootout_decision.md                            |  28 +++
 .../bootout_results.txt                            |  17 ++
 .../critical_survival_check.txt                    |  35 +++
 .../kill_process_group_results.txt                 |   2 +
 .../rollback_bootin_commands.sh                    |  21 ++
 .../SUMMARY.md                                     |  19 ++
 .../diff_review.txt                                |  21 ++
 .../restart_fastapi.txt                            |   3 +
 .../runtime_verify.txt                             |  30 +++
 .../targeted_tests.txt                             |  46 ++++
 .../post_containment_truth_endpoint_wiring.md      |  44 ++++
 .../source_authority_reasoning_graph_cleanup.md    |  80 ++++++
 .../VERIFY.md                                      | 139 +++++++++++
 .../REVIEW.md                                      | 128 ++++++++++
 .../stage_allowlist.txt                            |  17 ++
 .../data/brain_runtime_truth.json                  |  15 ++
 .../data/factory_runtime_truth.json                |  27 +++
 has_live_project_tracker/data/reasoning_graph.json |  84 +++++++
 .../data/source_authority_manifest.json            |  48 ++++
 tests/test_brain_truth_endpoints.py                |  34 +++
 tests/test_factory_runtime_truth.py                |  21 ++
 tests/test_live_runtime_truth_validator.py         | 123 ++++++++++
 tests/test_no_fake_green_truth_endpoints.py        | 127 ++++++++++
 tests/test_reasoning_graph.py                      |  21 ++
 30 files changed, 1695 insertions(+)

## Unstaged / untracked still present
 M backend/agent_runner.py
A  backend/brain/live_runtime_aggregator.py
A  backend/brain/runtime_truth_validator.py
 M backend/brain_convergence/improve_run.py
 M backend/brain_convergence/local_model_bridge.py
 M backend/brain_convergence/run_m0.py
 M backend/cluster_manager.py
M  backend/main.py
 M backend/mission_control/epic_fury.py
 M backend/pert_server.py
 M data/agent_execution_ledger.jsonl
 M data/prompt_brain/agent_audit.json
 M data/prompt_brain/champion_registry.json
 M data/prompt_brain/convergence_status.json
 M data/prompt_brain/cyber_swarm_state.json
 M data/prompt_brain/demo/demo_workflow_results.jsonl
 M data/prompt_brain/demo/messy_input_results.jsonl
 M data/prompt_brain/demo/reviewer_feedback_log.jsonl
 M data/prompt_brain/expanded_genes.jsonl
 M data/prompt_brain/gap_analysis.json
 M data/prompt_brain/gene_pool_m0.json
 M data/prompt_brain/improve_cursor.json
 M data/prompt_brain/improved_champions.jsonl
 M data/prompt_brain/model_adapter_status.json
 M data/prompt_brain/model_performance_matrix.json
 M data/prompt_brain/music/champion_registry.json
 M data/prompt_brain/music/convergence_status.json
 M data/prompt_brain/orchestrator_brief.json
 M data/prompt_brain/orchestrator_log.jsonl
 D data/prompt_brain/outreach/buyer_signal_dashboard.json
 D data/prompt_brain/outreach/outreach_approval_log.jsonl
 D data/prompt_brain/outreach/outreach_queue.jsonl
 D data/prompt_brain/outreach/phase_9_decision_gate.json
 D data/prompt_brain/outreach/reviewer_feedback_log.jsonl
 D data/prompt_brain/outreach/reviewer_feedback_summary.json
 D data/prompt_brain/outreach/target_contact_list_template.json
 D data/prompt_brain/pilot/paid_pilot_gate.json
 D data/prompt_brain/pilot/paid_pilot_hold_status.json
 D data/prompt_brain/pilot/paid_pilot_pipeline.json
 D data/prompt_brain/pilot/pilot_conversion_tracker.json
 D data/prompt_brain/pilot/pilot_onboarding_checklist.json
 D data/prompt_brain/pilot/pilot_risk_register.json
 D data/prompt_brain/pilot/pricing_model.json
 M data/prompt_brain/prompt_repair_queue.jsonl
 M data/prompt_brain/prompt_selection_log.jsonl
 M data/prompt_brain/research/champion_registry.json
 M data/prompt_brain/research/convergence_status.json
 M data/prompt_brain/research/gene_pool.json
 M data/prompt_brain/research_meta_decision.json
 M data/prompt_brain/research_meta_log.jsonl
 M data/prompt_brain/runtime_executions.jsonl
 M data/prompt_brain/self_heal_state.json
 M data/prompt_brain/splits_m0.json
 M docs/evidence/business/hoch-hasf-soccer-onboarding-audit.md
 M docs/evidence/business/project-revenue-readiness-audit.md
 M docs/evidence/business/revenue-action-queue.md
 M docs/evidence/runtime/hoch-compute-node-health.md
 M docs/evidence/runtime/hoch-pod-scheduler-evidence.md
 M docs/evidence/runtime/hoch-pods-runtime-evidence.md
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/SUMMARY.md
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/after_state.txt
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/before_state.txt
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/bootout_decision.md
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/bootout_results.txt
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/critical_survival_check.txt
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/kill_process_group_results.txt
A  docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/rollback_bootin_commands.sh
A  docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/SUMMARY.md
A  docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/diff_review.txt
A  docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/restart_fastapi.txt
A  docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/runtime_verify.txt
A  docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/targeted_tests.txt
A  docs/evidence/runtime/post_containment_truth_endpoint_wiring.md
A  docs/evidence/runtime/source_authority_reasoning_graph_cleanup.md
A  docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/VERIFY.md
A  docs/evidence/runtime/staging_manifest_truth_gate_rebuilt_20260707T015149Z/REVIEW.md
A  docs/evidence/runtime/staging_manifest_truth_gate_rebuilt_20260707T015149Z/stage_allowlist.txt
 M docs/evidence/ui/hoch-pods-theater-visual-compliance-audit.md
 M docs/evidence/ui/screenshots/hoch-pods-theater-cockpit-current.png
 M docs/evidence/ui/screenshots/rc52_1-hoch-pods-theater-current.png
 M docs/moonshot/BRAIN_GAP_ANALYSIS.md
 M docs/pert/CONSUMER_APPSTORE_PERT_TO_GOAL.md
 M docs/pert/K_TRACK_CRITICAL_PATH_LEDGER.md
 M docs/pert/K_TRACK_FOUNDER_ACTION_PACKET.md
 M docs/prompt_brain/phase_11_recursive_optimization_audit.md
 M frontend/app.js
 M frontend/data/brain_live.json
 M frontend/data/pert_tracker.json
 M frontend/index.html
 M frontend/src/components/overview/OverviewControlPlane.tsx
 M has_live_project_tracker/data/ag_execution_adapter_state.json
 M has_live_project_tracker/data/ag_execution_leases.json
 M has_live_project_tracker/data/ag_operator_hold.json
AM has_live_project_tracker/data/brain_runtime_truth.json
AM has_live_project_tracker/data/factory_runtime_truth.json
 M has_live_project_tracker/data/hoch_compute_node_health.json
 M has_live_project_tracker/data/hoch_hasf_soccer_audit_results.json
 M has_live_project_tracker/data/hoch_pod_schedule.json
 M has_live_project_tracker/data/hoch_pods_runtime_state.json
 M has_live_project_tracker/data/hoch_pods_theater_visual_compliance.json
 M has_live_project_tracker/data/human_approval_queue.json
 M has_live_project_tracker/data/k_track_founder_action_packet.json
AM has_live_project_tracker/data/reasoning_graph.json
AM has_live_project_tracker/data/source_authority_manifest.json
 M scripts/build_control_plane_status.py
 M scripts/hoch_cadence.sh
 M scripts/prompt_brain/model_adapters.py
 M scripts/prompt_brain/prompt_runtime_orchestrator.py
 M scripts/start_has_runtime.sh
 M scripts/stop_has_runtime.sh
 M scripts/write_brain_live.py
 M tests/e2e/anti-fake-runtime.spec.ts
 M tests/e2e/has-hasf-mission-control.spec.ts
 M tests/integration/test_brain_acceleration.py
A  tests/test_brain_truth_endpoints.py
A  tests/test_factory_runtime_truth.py
A  tests/test_live_runtime_truth_validator.py
A  tests/test_no_fake_green_truth_endpoints.py
 M tests/test_prompt_v4.py
 M tests/test_prompt_v5.py
A  tests/test_reasoning_graph.py
?? backend/agent_runner.py.bak_20260706
?? backend/brain_convergence/local_model_bridge.py.bak_20260706
?? backend/cluster_manager.py.bak_20260706
?? backend/factory/champion_loader.py
?? backend/factory/outcome_stats.py
?? backend/factory/runtime_ledger.py
?? backend/homemesh_runtime_asset_graph.py
?? backend/main.py.bak_fakegreen_20260706
?? data/prompt_brain/_quarantine_fabricated_20260706/
?? data/prompt_brain/outcome_feedback_ledger.jsonl
?? data/prompt_brain/outcome_stats.json
?? data/prompt_brain/runtime_usage_ledger.jsonl
?? deploy/local-autonomy/hoch-prompt-brain-runtime.service
?? docs/architecture/PROMPT_BRAIN_24_7_RUNTIME_ARCHITECTURE.md
?? docs/autonomy/PROMPT_BRAIN_24_7_RUNTIME_LOOP.md
?? docs/evidence/fake_green_sweep_20260706T225822Z.txt
?? docs/evidence/homemesh_spatial_graph/
?? docs/evidence/prompt_brain/
?? docs/evidence/runtime/final_containment_disabled_state_20260707T013240Z/
?? docs/evidence/runtime/final_precommit_truth_gate_20260707T015449Z/
?? docs/evidence/runtime/git_classification_20260707T014014Z/
?? docs/evidence/runtime/main_py_diff_audit_20260707T014239Z/
?? docs/evidence/runtime/main_py_final_route_repair_20260707T014757Z/
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_agent-router_ledger.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_brain_champion-outcome-feedback.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_brain_champion-runtime-usage.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_brain_factory-runtime-truth.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_brain_reasoning-graph.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_brain_runtime-truth.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_brain_source-authority.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_mission_brief.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_pert_data.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_v1_relay_health.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_v1_relay_registry.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__api_v1_relay_status.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/body__health.json
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/curl_errors.txt
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/main_py_pre_mount_anchor_repair.py
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/uvicorn.err.log
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/uvicorn.out.log
?? docs/evidence/runtime/main_py_route_order_repair_20260707T014607Z/
?? docs/evidence/runtime/main_py_surgical_repair_20260707T014411Z/
?? docs/evidence/runtime/persistent_containment_20260707T013142Z/
?? docs/evidence/runtime/post_endpoint_wiring_independent_verify_20260707T013026Z/
?? docs/evidence/runtime/process_governor_audit_20260707T010543Z/
?? docs/evidence/runtime/process_governor_audit_20260707T010657Z/
?? docs/evidence/runtime/process_ui_truth_audit_20260707T010310Z/
?? docs/evidence/runtime/respawn_root_cause_20260707T013328Z/
?? docs/evidence/runtime/runtime_containment_20260707T011248Z/
?? docs/evidence/runtime/runtime_pause_plan_20260707T010951Z/
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_agent-router_ledger.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_brain_champion-outcome-feedback.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_brain_champion-runtime-usage.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_brain_factory-runtime-truth.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_brain_reasoning-graph.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_brain_runtime-truth.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_brain_source-authority.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_mission_brief.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_pert_data.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_v1_relay_health.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_v1_relay_registry.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__api_v1_relay_status.json
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/body__health.json
?? docs/evidence/runtime/staged_truth_gate_review_20260707T015253Z/
?? docs/evidence/runtime/staged_truth_gate_trim_20260707T015358Z/
?? docs/evidence/runtime/staging_manifest_truth_gate_20260707T014133Z/
?? docs/evidence/ui/screenshots/homemesh-runtime-freshness.png
?? docs/evidence/ui/screenshots/homemesh-spatial-graph-current.png
?? docs/evidence/ui/screenshots/store-release-ledger-cockpit.png
?? docs/evidence/ui/screenshots/store-release-ledger-uiv2.png
?? docs/mission/PROMPT_BRAIN_24_7_RUNTIME_REPORT.md
?? docs/mission/PROMPT_BRAIN_HAS_INTEGRATION_REPORT.md
?? docs/prompt_brain/PROMPT_BRAIN_MASTER_COVERAGE_REPORT.md
?? docs/prompt_brain/PROMPT_BRAIN_PROMOTION_QUEUE.md
?? docs/prompt_brain/PROMPT_BRAIN_REMAINING_GAPS.md
?? docs/prompt_brain/PROMPT_BRAIN_RUNTIME_GAP_ANALYSIS.md
?? docs/release/ASO_DISCOVERY_GATE_G4.md
?? docs/release/DEMAND_VALIDATION_GATE_G1.md
?? has_live_project_tracker/data/generated_missing_prompts.json
?? has_live_project_tracker/data/homemesh_manual_devices.json
?? has_live_project_tracker/data/prompt_brain_has_integration_status.json
?? has_live_project_tracker/data/prompt_brain_inventory.json
?? has_live_project_tracker/data/prompt_brain_registry.json
?? has_live_project_tracker/data/prompt_brain_runtime_architecture.json
?? has_live_project_tracker/data/prompt_brain_runtime_events.jsonl
?? has_live_project_tracker/data/prompt_brain_runtime_metrics.json
?? has_live_project_tracker/data/prompt_brain_runtime_schedule.json
?? has_live_project_tracker/data/prompt_brain_runtime_state.json
?? has_live_project_tracker/data/prompt_capability_map.json
?? has_live_project_tracker/data/prompt_gap_analysis.json
?? has_live_project_tracker/data/prompt_promotion_queue.json
?? has_live_project_tracker/data/prompt_refinement_results.json
?? has_live_project_tracker/data/prompt_regression_fixtures.json
?? has_live_project_tracker/data/property_schema.json
?? has_live_project_tracker/data/room_schema.json
?? has_live_project_tracker/data/store_goal_release_ledger.json
?? scratch/verify_homemesh_runtime.py
?? scripts/brain_cadence.sh.bak_20260706
?? scripts/configure_ai_keys.py
?? scripts/fake_green_sweep.sh
?? scripts/hoch_cadence.sh.bak_20260706
?? scripts/prompt_brain/model_adapters.py.bak_20260706
?? scripts/prompt_brain/prompt_runtime_orchestrator.py.bak_20260706
?? scripts/prompt_brain_runtime_loop.py
?? scripts/run_homemesh_runtime_burnin.py
?? scripts/test_homemesh_restart_persistence.py
?? scripts/test_stale_device.py
?? scripts/test_unknown_device.py
?? scripts/verify_homemesh_brain_contract.py
?? scripts/verify_homemesh_brain_live_query.py
?? scripts/verify_prompt_brain_gap_analysis.py
?? scripts/verify_prompt_brain_has_integration.py
?? scripts/verify_prompt_brain_inventory.py
?? scripts/verify_prompt_brain_runtime_loop.py
?? scripts/verify_prompt_generation_quality.py
?? scripts/verify_prompt_registry_integrity.py
?? tests/e2e/has-hasf-homemesh-runtime-freshness.spec.ts
?? tests/e2e/has-hasf-homemesh-spatial-graph.spec.ts
?? tests/e2e/has-hasf-store-release-ledger.spec.ts
?? tests/test_homemesh_spatial_graph.py

## Forbidden staged scan
FORBIDDEN_STAGED=NO

## Compile

## Tests
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/michaelhoch/hoch_agent_swarm
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.14.1, hypothesis-6.156.1
collected 18 items

tests/test_live_runtime_truth_validator.py ......                        [ 33%]
tests/test_brain_truth_endpoints.py ...                                  [ 50%]
tests/test_factory_runtime_truth.py .                                    [ 55%]
tests/test_reasoning_graph.py .                                          [ 61%]
tests/test_no_fake_green_truth_endpoints.py .......                      [100%]

=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  /Users/michaelhoch/hoch_agent_swarm/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

backend/main.py:5362
  /Users/michaelhoch/hoch_agent_swarm/backend/main.py:5362: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

.venv/lib/python3.13/site-packages/fastapi/applications.py:4675
  /Users/michaelhoch/hoch_agent_swarm/.venv/lib/python3.13/site-packages/fastapi/applications.py:4675: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

backend/brain/doctrine_memory.py:53: 59 warnings
  /Users/michaelhoch/hoch_agent_swarm/backend/brain/doctrine_memory.py:53: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    """, (rule_id, rule_text, datetime.utcnow().isoformat() + "Z"))

backend/brain/doctrine_memory.py:67: 15 warnings
  /Users/michaelhoch/hoch_agent_swarm/backend/brain/doctrine_memory.py:67: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    """, (rule_id, r, datetime.utcnow().isoformat() + "Z"))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 18 passed, 77 warnings in 6.65s ========================

## Containment
Containment CLEAN

## Endpoint smoke
/health 200
/api/mission/brief 200
/api/v1/relay/health 200
/api/v1/relay/status 200
/api/v1/relay/registry 200
/api/agent-router/ledger 200
/api/pert/data 200
/api/brain/runtime-truth 200
/api/brain/factory-runtime-truth 200
/api/brain/reasoning-graph 200
/api/brain/source-authority 200
/api/brain/champion-runtime-usage 200
/api/brain/champion-outcome-feedback 200
