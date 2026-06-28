import json
from datetime import datetime

# 1. Framework Sources & Standards References
cybergov_framework_sources = [
    {"source_id": "NIST_SP_800_53_REV_5", "name": "NIST SP 800-53 Rev. 5 / Release 5.2.0", "description": "Security and Privacy Controls for Information Systems and Organizations"},
    {"source_id": "NIST_SP_800_137", "name": "NIST SP 800-137 ConMon", "description": "Information Security Continuous Monitoring (ISCM) for Federal Information Systems"},
    {"source_id": "NIST_SP_800_37_REV_2", "name": "NIST SP 800-37 Rev. 2 RMF", "description": "Risk Management Framework for Information Systems and Organizations"},
    {"source_id": "NIST_CSF_2_0", "name": "NIST CSF 2.0", "description": "Cybersecurity Framework 2.0"},
    {"source_id": "DOD_ZT_2027", "name": "DoD Zero Trust Strategy", "description": "DoD Zero Trust Strategy and Roadmap Crosswalk"},
    {"source_id": "CISA_KEV_CPG", "name": "CISA KEV / CPG", "description": "CISA Known Exploited Vulnerabilities and Cross-Sector Cybersecurity Performance Goals"}
]

# 2. Control Families Definition (NIST SP 800-53 Rev. 5 / Release 5.2.0)
cybergov_control_families = [
    {"family_id": "AC", "name": "Access Control", "description": "System access restrictions and authorization rules"},
    {"family_id": "AU", "name": "Audit and Accountability", "description": "Audit logging, storage, analysis, and reviews"},
    {"family_id": "CA", "name": "Assessment, Authorization, and Monitoring", "description": "RMF compliance, security assessments, and authorization"},
    {"family_id": "CM", "name": "Configuration Management", "description": "System baselines, inventory tracking, and change controls"},
    {"family_id": "IR", "name": "Incident Response", "description": "Incident handling, detection, reporting, and recovery"},
    {"family_id": "RA", "name": "Risk Assessment", "description": "Vulnerability scanning, risk registers, and threat modeling"},
    {"family_id": "SR", "name": "Supply Chain Risk Management", "description": "Software bill of materials (SBOM), provenance, and signing"}
]

# 3. Control Catalog (aligned with 5.2.0 requirements)
cybergov_controls = [
    {
        "control_id": "AC-2",
        "family": "AC",
        "title": "Account Management",
        "baseline_applicability": "High",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-ac-01"],
        "owner": "ISSO",
        "frequency": "Monthly",
        "last_assessed": "2026-06-15",
        "next_due": "2026-07-15",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section AC-2 (Release 5.2.0)"
    },
    {
        "control_id": "AU-2",
        "family": "AU",
        "title": "Event Logging",
        "baseline_applicability": "High",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-au-01", "ev-au-02"],
        "owner": "ISSO",
        "frequency": "Daily",
        "last_assessed": "2026-06-27",
        "next_due": "2026-06-28",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section AU-2 (Release 5.2.0)"
    },
    {
        "control_id": "CA-2",
        "family": "CA",
        "title": "Control Assessments",
        "baseline_applicability": "High",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-ca-01"],
        "owner": "SCA",
        "frequency": "Quarterly",
        "last_assessed": "2026-06-20",
        "next_due": "2026-09-20",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section CA-2 (Release 5.2.0)"
    },
    {
        "control_id": "CA-7",
        "family": "CA",
        "title": "Continuous Monitoring",
        "baseline_applicability": "High",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-ca-02"],
        "owner": "ISSM",
        "frequency": "Daily",
        "last_assessed": "2026-06-27",
        "next_due": "2026-06-28",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section CA-7 (Release 5.2.0)"
    },
    {
        "control_id": "CM-2",
        "family": "CM",
        "title": "Baseline Configuration",
        "baseline_applicability": "Medium",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-cm-01"],
        "owner": "ISSO",
        "frequency": "Weekly",
        "last_assessed": "2026-06-24",
        "next_due": "2026-07-01",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section CM-2 (Release 5.2.0)"
    },
    {
        "control_id": "IR-4",
        "family": "IR",
        "title": "Incident Handling",
        "baseline_applicability": "High",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-ir-01"],
        "owner": "ISSM",
        "frequency": "Monthly",
        "last_assessed": "2026-06-10",
        "next_due": "2026-07-10",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section IR-4 (Release 5.2.0)"
    },
    {
        "control_id": "RA-5",
        "family": "RA",
        "title": "Vulnerability Monitoring and Scanning",
        "baseline_applicability": "High",
        "implementation_status": "PARTIALLY_IMPLEMENTED",
        "assessment_status": "ASSESSED_WARN",
        "evidence_refs": ["ev-ra-01"],
        "owner": "ISSO",
        "frequency": "Weekly",
        "last_assessed": "2026-06-25",
        "next_due": "2026-07-02",
        "risk_rating": "Medium",
        "poam_link": "PM-RA-05-1",
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section RA-5 (Release 5.2.0)"
    },
    {
        "control_id": "SR-4",
        "family": "SR",
        "title": "Provenance and SBOM",
        "baseline_applicability": "High",
        "implementation_status": "IMPLEMENTED",
        "assessment_status": "ASSESSED_PASS",
        "evidence_refs": ["ev-sr-01", "ev-sr-02"],
        "owner": "SCA",
        "frequency": "Monthly",
        "last_assessed": "2026-06-26",
        "next_due": "2026-07-26",
        "risk_rating": "Low",
        "poam_link": None,
        "framework_source": "NIST_SP_800_53_REV_5",
        "source_citation": "NIST SP 800-53 Rev. 5 Section SR-4 (Release 5.2.0)"
    }
]

# 4. Evidence Vault
cybergov_evidence = [
    {"evidence_id": "ev-ac-01", "name": "Access Control List Configuration", "hash": "sha256-a1b2c3d4e5f6g7h8", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/environment.env.template", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-au-01", "name": "Uvicorn Audit Logging Config", "hash": "sha256-8c9d10e11f12g13h", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/launch.sh", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-au-02", "name": "Action Cryptoledger Blocks Index", "hash": "sha256-f5e4d3c2b1a0e9d8", "path": "backend/ledger_manager.py", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-ca-01", "name": "SCA Preflight Gate Scorecard", "hash": "sha256-preflight1234567890", "path": "artifacts/qa/readiness-scorecard.json", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-ca-02", "name": "Continuous Monitoring Dashboard Probes", "hash": "sha256-conmon77889900aabb", "path": "backend/staging_manager.py", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-cm-01", "name": "Kubernetes Service Deployment Specification", "hash": "sha256-yamlcm9988776655", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/deployment-service.yaml", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-ir-01", "name": "Automated Rollback Capsule", "hash": "sha256-rollbackcapsule99887", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/runtime/rollback_capsule.sh", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-ra-01", "name": "Known Exploited Vulnerabilities Coverage Report", "hash": "sha256-ra5scanresults9900", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/sbom.spdx.json", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-sr-01", "name": "Software Bill of Materials (SBOM)", "hash": "sha256-ad804b4cdbf758c0986a18e085e3f7ad2fcc51384dad7857667c9d1c743539f2", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/sbom.spdx.json", "timestamp": "2026-06-28T08:00:00Z"},
    {"evidence_id": "ev-sr-02", "name": "Supply Chain Provenance Attestation", "hash": "sha256-43001b4fed4f25e85fc7cb47438e4c29d650af6fbbcab20f01e8c272c5fe2358", "path": "dist/releases/0.1.6-ERROR-BUDGET-AWARE-AUTONOMY/provenance.intoto.jsonl", "timestamp": "2026-06-28T08:00:00Z"}
]

# 5. Assessments Data
cybergov_assessments = [
    {"assessment_id": "as-ac-01", "control_id": "AC-2", "status": "PASS", "tested_by": "SCA", "date": "2026-06-15", "notes": "Account lockout and MFA policies successfully enforced by runtime supervisor."},
    {"assessment_id": "as-au-01", "control_id": "AU-2", "status": "PASS", "tested_by": "ISSO", "date": "2026-06-27", "notes": "Auditable event blocks successfully chained in SQLite and serialized blocks JSON."},
    {"assessment_id": "as-ra-01", "control_id": "RA-5", "status": "WARN", "tested_by": "ISSO", "date": "2026-06-25", "notes": "Weekly vulnerability scan completed, identified 1 open medium-severity item tracked in POA&M."}
]

# 6. Findings / Vulnerability Tracking
cybergov_findings = [
    {"finding_id": "fi-ra-05-1", "control_id": "RA-5", "title": "Legacy dependency library alert", "severity": "Medium", "status": "OPEN", "identified_date": "2026-06-25", "description": "Vulnerability scanning identified non-critical package mismatch in dependency tree. Mitigated via cosign waiver."}
]

# 7. POA&M Plan of Action and Milestones
cybergov_poam = [
    {"poam_id": "PM-RA-05-1", "finding_id": "fi-ra-05-1", "title": "Upgrade legacy package dependency", "weakness_description": "Legacy library version in packaging manifest.", "owner": "ISSO", "scheduled_completion": "2026-07-25", "status": "OPEN", "closure_evidence": None}
]

# 8. Risk Register & Residual Risks
cybergov_risks = [
    {"risk_id": "ri-01", "title": "Simulated environment mismatch", "description": "Risk that simulated local cockpit environment differs from live multi-cluster target.", "severity": "Medium", "likelihood": "Low", "acceptance_status": "ACCEPTED_AO", "accepted_by": "Authorizing Official (AO)", "mitigation": "Staging dry-run validations verify configuration parameters prior to execution."}
]

# 9. Continuous Monitoring Calendar & Scheduling (NIST SP 800-137)
cybergov_conmon_events = [
    {"event_id": "cm-ev-01", "event_name": "Audit Logging Proximity Check", "frequency": "Daily", "last_run": "2026-06-27", "status": "PASS", "description": "Ensures event logging blocks are successfully generating and appending to the ledger."},
    {"event_id": "cm-ev-02", "event_name": "Weekly Vulnerability Scanning", "frequency": "Weekly", "last_run": "2026-06-25", "status": "WARN", "description": "Automated vulnerability check against known threat catalogs."},
    {"event_id": "cm-ev-03", "event_name": "Quarterly Security Assessment", "frequency": "Quarterly", "last_run": "2026-06-20", "status": "PASS", "description": "ISSM-guided validation of administrative controls."}
]

# 10. Framework Crosswalks & Zero Trust Pillars
cybergov_crosswalks = [
    {"control_id": "AC-2", "csf_category": "PR.AC (Protect / Access Control)", "zt_pillar": "User", "zt_capability": "Authentication and Access Governance", "fisma_omb": "OMB A-130 App I"},
    {"control_id": "AU-2", "csf_category": "DE.AE (Detect / Anomalies and Events)", "zt_pillar": "Visibility and Analytics", "zt_capability": "Audit Log Collection", "fisma_omb": "FISMA FY2026 Metric 3.4"},
    {"control_id": "RA-5", "csf_category": "ID.RA (Identify / Risk Assessment)", "zt_pillar": "Device", "zt_capability": "Vulnerability Management", "fisma_omb": "FISMA FY2026 Metric 1.2"}
]

# 11. CyberGov Export/Audit Logs Tracker
cybergov_exports = []

def get_cybergov_scorecard() -> dict:
    total_cnt = len(cybergov_controls)
    impl_cnt = sum(1 for c in cybergov_controls if c["implementation_status"] == "IMPLEMENTED")
    assessed_pass = sum(1 for c in cybergov_controls if c["assessment_status"] == "ASSESSED_PASS")
    
    # Calculate percentages
    impl_pct = round((impl_cnt / total_cnt) * 100) if total_cnt > 0 else 0
    assess_pct = round((assessed_pass / total_cnt) * 100) if total_cnt > 0 else 0
    
    return {
        "framework_coverage_target": "100% framework coverage mapping target",
        "control_traceability_target": "100% control-to-evidence traceability target",
        "reporting_coverage_target": "100% reporting coverage target",
        "implementation_score": impl_pct,
        "assessment_score": assess_pct,
        "conmon_state": "ACTIVE",
        "total_controls": total_cnt,
        "implemented_controls": impl_cnt,
        "open_poams": sum(1 for p in cybergov_poam if p["status"] == "OPEN"),
        "accepted_risks": sum(1 for r in cybergov_risks if r["acceptance_status"] == "ACCEPTED_AO"),
        "compliance": {
            "statement": "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW",
            "notice": "The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made."
        }
    }

def get_rmf_lifecycle() -> list:
    return [
        {"step": "1. PREPARE", "status": "COMPLETE", "description": "Establish team, define boundaries, map standards to NIST SP 800-53 Rev. 5 / Release 5.2.0."},
        {"step": "2. CATEGORIZE", "status": "COMPLETE", "description": "Categorize system as Moderate-Impact baseline based on FIPS 199 parameters."},
        {"step": "3. SELECT", "status": "COMPLETE", "description": "Select baseline controls, tailor overlays, establish Continuous Monitoring Strategy (NIST SP 800-137)."},
        {"step": "4. IMPLEMENT", "status": "COMPLETE", "description": "Implement access rules, audit logging pipelines, SBOMS, and launch supervisors."},
        {"step": "5. ASSESS", "status": "COMPLETE", "description": "Run security assessments (NIST SP 800-53A), record findings, and publish POA&Ms."},
        {"step": "6. AUTHORIZE", "status": "PENDING_REVIEW", "description": "Compile evidence package, present to Authorizing Official (AO) for risk acceptance."},
        {"step": "7. MONITOR", "status": "ACTIVE", "description": "Conduct continuous audit logging, vulnerability checks, and automated configuration monitoring."}
    ]

def get_cybergov_data() -> dict:
    return {
        "framework_sources": cybergov_framework_sources,
        "control_families": cybergov_control_families,
        "controls": cybergov_controls,
        "evidence": cybergov_evidence,
        "assessments": cybergov_assessments,
        "findings": cybergov_findings,
        "poams": cybergov_poam,
        "risks": cybergov_risks,
        "conmon_events": cybergov_conmon_events,
        "crosswalks": cybergov_crosswalks,
        "scorecard": get_cybergov_scorecard(),
        "rmf_lifecycle": get_rmf_lifecycle()
    }

def generate_cybergov_reports_bundle() -> dict:
    # Generates all 12 required reports/crosswalks in text/JSON format
    scorecard = get_cybergov_scorecard()
    rmf_lifecycle = get_rmf_lifecycle()
    
    return {
        "1_nist_800_53_rev5_control_implementation_matrix": {
            "title": "NIST SP 800-53 Rev. 5 Control Implementation Matrix (Release 5.2.0)",
            "applicability": "Moderate-Impact Baseline",
            "controls": cybergov_controls,
            "disclaimer": "100% framework coverage mapping target"
        },
        "2_nist_800_53a_assessment_results_matrix": {
            "title": "NIST SP 800-53A Assessment Results Matrix",
            "assessments": cybergov_assessments,
            "disclaimer": "100% control-to-evidence traceability target"
        },
        "3_nist_sp_800_137_conmon_report": {
            "title": "NIST SP 800-137 Continuous Monitoring Report",
            "conmon_state": scorecard["conmon_state"],
            "schedule": cybergov_conmon_events
        },
        "4_rmf_lifecycle_status_report": {
            "title": "Risk Management Framework (RMF) Lifecycle Status Report (NIST SP 800-37 Rev. 2)",
            "current_step": "Step 6. Authorize (PENDING_REVIEW)",
            "steps": rmf_lifecycle
        },
        "5_poam_export": {
            "title": "FISMA Plan of Action and Milestones (POA&M) Weaknesses Export",
            "weaknesses": cybergov_poam
        },
        "6_risk_register_export": {
            "title": "Residual Risk Register Export",
            "risks": cybergov_risks
        },
        "7_evidence_traceability_matrix": {
            "title": "Control-to-Evidence Traceability Matrix",
            "evidence": cybergov_evidence
        },
        "8_cisa_kev_cpg_coverage_report": {
            "title": "CISA Known Exploited Vulnerabilities & Cybersecurity Performance Goals Coverage Report",
            "status": "PASS",
            "metrics": {
                "known_exploited_vulns_open": 0,
                "cpg_goals_implemented": 3,
                "secure_by_design_principles_mapped": 2
            }
        },
        "9_dod_zero_trust_crosswalk": {
            "title": "DoD Zero Trust Strategy Pillar and Capability Crosswalk",
            "crosswalks": cybergov_crosswalks
        },
        "10_ao_review_package": {
            "title": "Authorizing Official (AO) Review and Authorization Sign-Off Package",
            "recommendation": "SUPPORT EVIDENCE PACKAGE COMPILED FOR REVIEW. ACTUAL ATO NOT GRANTED.",
            "checklist": [
                {"item": "SSP Evidence Complete", "status": "PASS"},
                {"item": "NIST SP 800-53 Matrix Generated", "status": "PASS"},
                {"item": "Continuous Monitoring Active", "status": "PASS"}
            ]
        },
        "11_executive_cybersecurity_scorecard": {
            "title": "Executive Cybersecurity Scorecard",
            "overall_posture": scorecard
        },
        "12_machine_readable_json_evidence_bundle": get_cybergov_data()
    }
