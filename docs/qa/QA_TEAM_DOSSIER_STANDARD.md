# QA Team Dossier Standard

* **Version**: 1.0.0
* **Goal**: Establish the structural standard, metrics, and verification rules for all 16 QA Teams of the HAS/HASF swarm.

---

## Dossier Schema Requirements
All QA dossiers must be stored as JSON objects in `data/qa_dossiers/` and conform to the schema:
1. **Metadata**: `team_id`, `team_name`, `last_verified_at`, `signoff_agent`.
2. **Result**: `verification_status` (one of `PASS`, `FAIL`, `QA_PARTIAL`, `UNKNOWN`).
3. **Metrics**: Key-value pairs containing quantitative indicators (e.g. coverage, count, ages).
4. **Evidence & Defects**: Lists of validated file references and unresolved flaws.

---

## Mapped QA Teams

1. **RemoteOps QA** (`remoteops_qa`): Monitors remote deployment, host ping, Docker containers health.
2. **Revenue QA** (`revenue_qa`): Monetization metrics and Stripe integration correctness.
3. **Product QA** (`product_qa`): Feature specification coverage and Kano requirements.
4. **Cyber DevSecOps QA** (`cyber_devsecops_qa`): Vulnerability status, static code scanning results.
5. **Evidence QA`** (`evidence_qa`): Evidence ledger validity and hashing check.
6. **Runner QA** (`runner_qa`): Heartbeat freshness and execution daemon status.
7. **UI Truth QA** (`ui_truth_qa`): Port configuration and UI api match percent.
8. **Planning QA** (`planning_qa`): PERT critical path accuracy and completion estimation.
9. **IV&V Red Team QA** (`ivv_red_team_qa`): Adherence to NO-GO rules and anti-fake checking.
10. **HASF Commercialization QA** (`hasf_commercialization_qa`): Pricing tiers, outbound target lists.
11. **SRE Reliability QA** (`sre_reliability_qa`): Watchdog daemon checks and uptime.
12. **Supply Chain QA** (`supply_chain_qa`): Pinned packages, Docker base image validation.
13. **Secrets & Identity QA** (`secrets_identity_qa`): Secret leaks avoidance and permissions validation.
14. **Backup & Recovery QA** (`backup_recovery_qa`): WAL database backup validation.
15. **Release Authority QA** (`release_authority_qa`): Release GO posture gating.
16. **Customer Outcome QA** (`customer_outcome_qa`): User interface usability and response latency.
