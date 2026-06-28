# Universal Prompt Gap Analysis Report

Audit timestamp: 2026-06-28T21:35:51.912224+00:00

### Findings Overview:
- Critical Gaps: 26
- High Gaps: 58

## Identified Missing Prompt Families Table
| Gap ID | Prompt ID | Title | Category | Severity | Status |
| --- | --- | --- | --- | --- | --- |
| GAP-TRAC-BRAIN-001 | BRAIN-001 | Central LLM Brain Architect | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-002 | BRAIN-002 | Evidence Ingestion Agent | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-003 | BRAIN-003 | Knowledge Graph Builder | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-004 | BRAIN-004 | Semantic Memory Curator | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-005 | BRAIN-005 | Duplicate Finding Reconciler | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-006 | BRAIN-006 | Source Trust Scoring Agent | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-007 | BRAIN-007 | Citation and Provenance Agent | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-008 | BRAIN-008 | Decision Memory Agent | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-009 | BRAIN-009 | Lessons Learned Agent | LLM Brain | Critical | OPEN |
| GAP-TRAC-BRAIN-010 | BRAIN-010 | Brain Drift Auditor | LLM Brain | Critical | OPEN |
| GAP-TRAC-PROMPT-001 | PROMPT-001 | Prompt Coverage Auditor | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-002 | PROMPT-002 | Prompt Quality Scorer | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-003 | PROMPT-003 | Prompt Version Control Agent | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-004 | PROMPT-004 | Prompt Safety Reviewer | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-005 | PROMPT-005 | Prompt-to-Control Mapper | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-006 | PROMPT-006 | Prompt Routing Policy Agent | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-007 | PROMPT-007 | Prompt Regression Tester | Prompt Governance | Critical | OPEN |
| GAP-TRAC-PROMPT-008 | PROMPT-008 | Prompt Drift Detection Agent | Prompt Governance | Critical | OPEN |
| GAP-TRAC-GAP-001 | GAP-001 | Universal Gap Analysis Commander | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-002 | GAP-002 | Gap-to-POA&M Converter | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-003 | GAP-003 | Remediation Dependency Planner | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-004 | GAP-004 | Closure Evidence Validator | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-005 | GAP-005 | Compensating Control Designer | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-006 | GAP-006 | Residual Risk Acceptance Agent | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-007 | GAP-007 | Gap Burn-Down Manager | Gap Analysis | Critical | OPEN |
| GAP-TRAC-GAP-008 | GAP-008 | Control Closure QA Agent | Gap Analysis | Critical | OPEN |
| GAP-TRAC-SWARM-001 | SWARM-001 | Agent Registry Curator | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-002 | SWARM-002 | Agent Capability Mapper | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-003 | SWARM-003 | Agent Tool Permission Auditor | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-004 | SWARM-004 | Agent Memory Boundary Agent | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-005 | SWARM-005 | Agent Task Router | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-006 | SWARM-006 | Agent Conflict Resolver | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-007 | SWARM-007 | Agent Output QA Judge | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-008 | SWARM-008 | Agent Evidence Validator | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-009 | SWARM-009 | Agent Autonomy Risk Auditor | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-010 | SWARM-010 | Human Approval Gatekeeper | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-011 | SWARM-011 | Agent-to-Agent Handoff Auditor | Agent Governance | High | OPEN |
| GAP-TRAC-SWARM-012 | SWARM-012 | Agent Performance Scorer | Agent Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-001 | GOVFRAME-001 | NIST 800-53 Rev. 5 Control Family Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-002 | GOVFRAME-002 | NIST 800-37 RMF Lifecycle Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-003 | GOVFRAME-003 | NIST 800-137 ConMon Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-004 | GOVFRAME-004 | NIST 800-171 CUI Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-005 | GOVFRAME-005 | CMMC 2.0 Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-006 | GOVFRAME-006 | CJIS Security Policy Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-007 | GOVFRAME-007 | IRS Pub 1075 Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-008 | GOVFRAME-008 | TIC 3.0 Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-009 | GOVFRAME-009 | CDM Program Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-010 | GOVFRAME-010 | OMB A-130 Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-011 | GOVFRAME-011 | OMB M-21-31 Logging Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-012 | GOVFRAME-012 | CISA BOD/ED Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-013 | GOVFRAME-013 | NIST AI RMF Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-014 | GOVFRAME-014 | DoD Zero Trust Capability Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-015 | GOVFRAME-015 | DoD 8140 Workforce Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-016 | GOVFRAME-016 | DISA STIG Compliance Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-017 | GOVFRAME-017 | CNSSI 1253 Agent | Governance | High | OPEN |
| GAP-TRAC-GOVFRAME-018 | GOVFRAME-018 | Privacy Act / SORN Agent | Governance | High | OPEN |
| GAP-TRAC-ELECTION-001 | ELECTION-001 | Election Systems Security Agent | Governance | High | OPEN |
| GAP-TRAC-GRANTS-001 | GRANTS-001 | Grants Compliance Agent | Governance | High | OPEN |
| GAP-TRAC-FAR-001 | FAR-001 | FAR/DFARS Contracting Agent | Governance | High | OPEN |
| GAP-TRAC-AG-001 | AG-001 | AgTech / USDA Data Security Agent | Governance | High | OPEN |
| GAP-TRAC-FOOD-001 | FOOD-001 | Food Safety / Supply Chain Traceability Agent | Governance | High | OPEN |
| GAP-TRAC-CONST-001 | CONST-001 | Construction Project Systems Risk Agent | Governance | High | OPEN |
| GAP-TRAC-PROP-001 | PROP-001 | PropertyTech Privacy and Access Agent | Governance | High | OPEN |
| GAP-TRAC-INS-001 | INS-001 | Insurance Claims Fraud / Data Governance Agent | Governance | High | OPEN |
| GAP-TRAC-MEDIA-001 | MEDIA-001 | Content Rights / Streaming Security Agent | Governance | High | OPEN |
| GAP-TRAC-HOSP-001 | HOSP-001 | Guest Data / Reservation Security Agent | Governance | High | OPEN |
| GAP-TRAC-NONPROFIT-001 | NONPROFIT-001 | Donor Data / Grant Compliance Agent | Governance | High | OPEN |
| GAP-TRAC-PROSERV-001 | PROSERV-001 | Client Confidentiality Agent | Governance | High | OPEN |
| GAP-TRAC-HR-001 | HR-001 | HR Data Privacy Agent | Governance | High | OPEN |
| GAP-TRAC-PUBHEALTH-001 | PUBHEALTH-001 | Public Health Data Governance Agent | Governance | High | OPEN |
| GAP-TRAC-COURTS-001 | COURTS-001 | Judicial Case Management Security Agent | Governance | High | OPEN |
| GAP-TRAC-CORR-001 | CORR-001 | Corrections Facility Systems Security Agent | Governance | High | OPEN |
| GAP-TRAC-EMERG-001 | EMERG-001 | Emergency Management Systems Agent | Governance | High | OPEN |
| GAP-TRAC-SMARTCITY-001 | SMARTCITY-001 | Smart Cities IoT Security Agent | Governance | High | OPEN |
| GAP-TRAC-ENV-001 | ENV-001 | Environmental Sensor Data Integrity Agent | Governance | High | OPEN |
| GAP-TRAC-RESEARCH-001 | RESEARCH-001 | Research Data / IP Protection Agent | Governance | High | OPEN |
| GAP-TRAC-FINOPS-001 | FINOPS-001 | Finance Controls Auditor | Governance | High | OPEN |
| GAP-TRAC-PROC-001 | PROC-001 | Procurement Risk Agent | Governance | High | OPEN |
| GAP-TRAC-CRM-001 | CRM-001 | CRM / Customer Data Security Agent | Governance | High | OPEN |
| GAP-TRAC-RECORDS-001 | RECORDS-001 | Records Retention Agent | Governance | High | OPEN |
| GAP-TRAC-TRAIN-001 | TRAIN-001 | Workforce Training Compliance Agent | Governance | High | OPEN |
| GAP-TRAC-FAC-001 | FAC-001 | Facilities / Physical Security Systems Agent | Governance | High | OPEN |
| GAP-TRAC-CONTRACT-001 | CONTRACT-001 | Contract Risk Agent | Governance | High | OPEN |
| GAP-TRAC-PMO-001 | PMO-001 | Program Risk / Milestone Agent | Governance | High | OPEN |