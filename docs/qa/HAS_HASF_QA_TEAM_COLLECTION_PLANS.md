# HAS/HASF QA Team Collection Plans

* **Goal**: Establish the collection path mappings and validation methodologies for compiling evidence from the 16 QA teams.

---

## Plan Mappings

| Team ID | Verification Target | Verification Methodology | Expected Output |
|---|---|---|---|
| **remoteops_qa** | `docs/evidence/vps/` | SSH_PORT_PROBE | Valid remote host reachability record |
| **revenue_qa** | `docs/hasf/` | REVENUE_OPS_CHECK | Stripe configuration boundary document |
| **product_qa** | `docs/planning/` | SPEC_MATCH | Product specification list check |
| **cyber_devsecops_qa** | `docs/evidence/ci/` | SAST_SCAN_PARSE | Vulnerability scan aggregate outputs |
| **evidence_qa** | `docs/evidence/helm/` | LEDGER_INTEGRITY_CHECK | Evidence manifest hashing check |
| **runner_qa** | `docs/evidence/helm/` | HEARTBEAT_PROBE | Runner daemon log age validator |
| **ui_truth_qa** | `docs/evidence/ui/` | URL_PORT_SCAN | Check against public port exposure |
| **planning_qa** | `docs/evidence/goal_tracker/` | PERT_SUMMATION_CHECK | Sum critical path expected values |
| **ivv_red_team_qa** | `docs/evidence/ui/` | ANTI_FAKE_SCAN | Check for hardcoded mock statuses |
| **hasf_commercialization_qa**| `docs/hasf/` | TIER_COUNT | Assert minimum pricing tiers list |
| **sre_reliability_qa** | `docs/runbooks/` | WATCHDOG_CHECK | Watchdog logs freshness check |
| **supply_chain_qa** | `docs/evidence/ci/` | DEPENDENCY_PIN_CHECK | Pinned python and node libraries |
| **secrets_identity_qa** | `docs/evidence/ci/` | GITLEAKS_PARSE | Secret scan execution verification |
| **backup_recovery_qa** | `docs/runbooks/` | SQLITE_WAL_CHECK | SQLite WAL format and backups integrity |
| **release_authority_qa** | `docs/evidence/helm/` | RELEASE_POSTURE_CHECK | Enforce release authority rules |
| **customer_outcome_qa** | `docs/evidence/ui/` | LATENCY_VERIFY | UI response time measurements |
