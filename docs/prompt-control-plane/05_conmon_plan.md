# Continuous Monitoring (ConMon) Plan

This plan establishes recurring health, security, and governance auditing cadences for the HOCH Agent Swarm.

## Daily Monitoring Tasks
- **Known Asset Reporting**: Run network/ping sweeps to update active hosts.
- **Model Runtime Health**: Query local Ollama (`:11434`) and LM Studio (`:1234`) model-list endpoints.
- **Critical/High Findings**: Audit the SIEM event log for any high-priority warnings.
- **Failed Jobs**: Scrutinize the transaction history inside `backend/swarm_ledger.db` for agent execution aborts.
- **Prompt-Safety Events**: Scan logs for prompt injection attempts or blocked tool-misuse warnings.
- **Backup Status**: Confirm that daily rclone copies to secure destinations have succeeded.

## Weekly Monitoring Tasks
- **SAST/SCA/Secrets Scans**: Run automated checks for hardcoded credentials, API keys, or security regressions.
- **Dependency Drift**: Review dependencies in `package.json` and python virtual environments.
- **Firewall & Port Exposure**: Scan the control-plane node (MacBook Pro) for listening ports.
- **Evidence Freshness**: Verify that evidence files in the active workspace have current timestamps.
- **Release Readiness**: Assess readiness of candidate branches against qa_evidence_matrix targets.

## Monthly Monitoring Tasks
- **Full QA/Security Audit**: Run comprehensive integration test suites across all operational flows.
- **Disaster Recovery Validation**: Test restore flows from rclone model backups.
- **Model Lifecycle/Quarantine**: Review model evaluation classification status.
- **Prompt Library Drift**: Compare active prompts against the golden prompt library manifest.
- **Risk Register Refresh**: Re-evaluate severity and likelihood metrics in `risk_register.csv`.
- **Control Mapping**: Re-map validated tests against NIST SP 800-53 controls.

## Quarterly Monitoring Tasks
- **North Star Review**: Evaluate the Validated Positive Production Outcomes Per Week score.
- **OKR Review/Reset**: Re-align swarm objectives and key results.
- **Control-Plane Architecture Review**: Verify network topologies, nodes, and router configurations.
- **Red-Team Exercise**: Execute simulated prompt injection and sandbox breakout attempts.
- **Value Review**: Assess business throughput, home automation utility, and time saved.
