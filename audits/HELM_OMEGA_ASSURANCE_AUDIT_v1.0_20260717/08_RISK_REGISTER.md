# Risk Register — HELM OMEGA ASSURANCE AUDIT v1.0

| ID | Title | Phase | Likelihood | Impact | Risk | Status | Evidence pointer |
|---|---|---|---|---|---|---|---|
| R-01 | Unauthenticated GET on HELM LIVE | 5 | M | H | **HIGH** | OPEN | helm_live_api CORS/auth; live probe without creds |
| R-02 | CORS allow_origins=* | 5 | M | H | **HIGH** | OPEN | backend/helm_live_api.py |
| R-03 | NIST posture 100% on 13 controls | 5/9 | H | H | **HIGH** | OPEN | helm_control_posture.json |
| R-04 | CM-3 uncommitted claim false now | 1/9 | H | M | **HIGH** | OPEN | git status 289 dirty |
| R-05 | Factory READY overclaim | 7 | H | H | **HIGH** | OPEN | factory_registry vs readiness board |
| R-06 | Dual API truth surfaces | 2 | H | H | **HIGH** | OPEN | :8000 vs :8770 probes |
| R-07 | Mission blocked REQ-GOV-002 | 3/8 | Certain | H | **HIGH** | OPEN | mission_state overall |
| R-08 | $0 settled revenue / PENDING only | 7/14 | Certain | H (mission) | **HIGH** | OPEN | revenue_ledger.jsonl |
| R-09 | Apple TestFlight/ASC UNKNOWN | 8/14 | Certain | H | **HIGH** | OPEN | mission_state approvals.apple |
| R-10 | Soak false-green history | 10/12 | M | H | **HIGH** | MITIGATED-in-culture | SUPERSEDED seals |
| R-11 | 24h soak not cleanly proven | 10 | H | H | **HIGH** | OPEN | seal_verdict inventory |
| R-12 | Stale HOCH_STATUS / bus ONLINE | 1/2 | H | M | **MEDIUM** | OPEN | mtimes/heartbeats |
| R-13 | Stale source_authority_manifest allowed_for_live_ui | 2 | M | M | **MEDIUM** | OPEN | status STALE |
| R-14 | High cyclomatic hotspots | 1 | M | M | **MEDIUM** | OPEN | AST CC report |
| R-15 | Performance 100–1000 scale unmeasured | 11 | M | M | **MEDIUM** | OPEN | no run this audit |
| R-16 | Dependency CVEs unknown | 5 | M | H | **MEDIUM** | OPEN | scan not completed |
| R-17 | LLM prompt injection residual | 6 | M | H | **HIGH** | OPEN | TEVV not run |
| R-18 | Write race on mission_state.json | 3 | L–M | M | **MEDIUM** | OPEN | multi-writer design |
| R-19 | LAN pentest residuals F-1..F-5 | 5 | M | M | **MEDIUM** | OPEN | artifacts/pentest |
| R-20 | HHF/HPF unimplemented but listed | 7 | H | L–M | **MEDIUM** | OPEN | registry stubs |
