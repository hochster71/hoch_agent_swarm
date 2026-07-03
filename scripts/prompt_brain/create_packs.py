#!/usr/bin/env python3
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
PACKS_DIR = BASE_DIR / "data" / "prompt_brain" / "packs"
PACKS_DIR.mkdir(parents=True, exist_ok=True)

packs_data = {
    "cybersecurity_prompt_pack": {
        "pack_name": "HOCH Zero-Trust Cybersecurity Swarm Pack",
        "target_buyer": "Chief Information Security Officers (CISOs), Security Architects, and DevSecOps Directors.",
        "pricing_hypothesis": "$499/month for small teams, $1,999/month enterprise flat rate.",
        "use_cases": [
            "Establish zero-trust network boundaries and micro-segmentation guidelines.",
            "Audit cryptographic key lifecycles and HSM security policies."
        ],
        "included_prompt_families": ["Role System Prompt", "Task Execution Prompt", "SOP Prompt"],
        "approved_prompts": [
            {
                "prompt_id": "PB-CYBERSECURITY-ENGINEER-ROLE-SYSTEM-PROMPT-1",
                "family": "Role System Prompt",
                "qa_score": 92,
                "red_team_score": 100
            },
            {
                "prompt_id": "PB-CYBERSECURITY-ENGINEER-SOP-PROMPT-1",
                "family": "SOP Prompt",
                "qa_score": 94,
                "red_team_score": 100
            }
        ],
        "qa_score_summary": {
            "average_score": 93.0,
            "min_score": 92,
            "max_score": 94
        },
        "red_team_summary": {
            "vulnerabilities_found": 0,
            "critical_findings": 0,
            "remediation_status": "VERIFIED_SECURE"
        },
        "sample_workflows": [
            "Trigger 'Establish zero-trust network boundaries' SOP -> Feed environment parameters -> Audit output against network constraints."
        ],
        "deployment_instructions": "Load prompts via the HOCH Swarm Registry API or inject dynamically into runtime orchestrator adapters.",
        "risks_and_disclaimers": "Ensure manual override parameters are enabled for emergency network access operations."
    },
    "devsecops_prompt_pack": {
        "pack_name": "HOCH DevSecOps CI/CD Automation Pack",
        "target_buyer": "DevSecOps Engineers, Platform Engineers, and Release Managers.",
        "pricing_hypothesis": "$299/month per active agent cluster.",
        "use_cases": [
            "Configure automated static code scanning.",
            "Verify build artifact provenance and SBOM configurations."
        ],
        "included_prompt_families": ["Role System Prompt", "Task Execution Prompt", "SOP Prompt"],
        "approved_prompts": [
            {
                "prompt_id": "PB-DEVSECOPS-ARCHITECT-ROLE-SYSTEM-PROMPT-1",
                "family": "Role System Prompt",
                "qa_score": 91,
                "red_team_score": 100
            }
        ],
        "qa_score_summary": {
            "average_score": 91.0,
            "min_score": 91,
            "max_score": 91
        },
        "red_team_summary": {
            "vulnerabilities_found": 0,
            "critical_findings": 0,
            "remediation_status": "VERIFIED_SECURE"
        },
        "sample_workflows": [
            "Instantiate DevSecOps Architect -> Scan code via SonarQube -> Verify output provenance against SBOM policy."
        ],
        "deployment_instructions": "Mount as configmap in Kubernetes clusters or trigger dynamically during runner jobs.",
        "risks_and_disclaimers": "Verify scanner configurations before running overrides in production pipelines."
    },
    "rmf_ato_conmon_prompt_pack": {
        "pack_name": "HOCH RMF/ATO Compliance Swarm Pack",
        "target_buyer": "Compliance Officers, Security Managers, and System Administrators.",
        "pricing_hypothesis": "$999/month flat rate per system under assessment.",
        "use_cases": [
            "Audit system controls in eMASS and coordinate authorization packages.",
            "Execute continuous monitoring schedules."
        ],
        "included_prompt_families": ["Role System Prompt", "Task Execution Prompt", "SOP Prompt"],
        "approved_prompts": [
            {
                "prompt_id": "PB-RMF-ATO-COMPLIANCE-OFFICER-SOP-PROMPT-1",
                "family": "SOP Prompt",
                "qa_score": 95,
                "red_team_score": 100
            }
        ],
        "qa_score_summary": {
            "average_score": 95.0,
            "min_score": 95,
            "max_score": 95
        },
        "red_team_summary": {
            "vulnerabilities_found": 0,
            "critical_findings": 0,
            "remediation_status": "VERIFIED_SECURE"
        },
        "sample_workflows": [
            "Scan NIST AI RMF compliance requirements -> Extract control status -> Output eMASS coordination payload."
        ],
        "deployment_instructions": "Integrate with GRC platform APIs or query through the Prompt Brain command panel.",
        "risks_and_disclaimers": "Compliance outcomes must be signed off by a certified assessor."
    },
    "qa_red_team_prompt_pack": {
        "pack_name": "HOCH QA and Safety Auditing Pack",
        "target_buyer": "QA Leads, SDETs, and Safety Auditors.",
        "pricing_hypothesis": "$399/month per developer seat.",
        "use_cases": [
            "Create automated test suites.",
            "Triage vulnerability scan reports."
        ],
        "included_prompt_families": ["Role System Prompt", "Task Execution Prompt", "SOP Prompt"],
        "approved_prompts": [
            {
                "prompt_id": "PB-QA-AUTOMATION-LEAD-TASK-EXECUTION-PROMPT-1",
                "family": "Task Execution Prompt",
                "qa_score": 93,
                "red_team_score": 100
            }
        ],
        "qa_score_summary": {
            "average_score": 93.0,
            "min_score": 93,
            "max_score": 93
        },
        "red_team_summary": {
            "vulnerabilities_found": 0,
            "critical_findings": 0,
            "remediation_status": "VERIFIED_SECURE"
        },
        "sample_workflows": [
            "Load QA agent -> Parse repository schemas -> Autogenerate test fixtures."
        ],
        "deployment_instructions": "Inject as environment payload in target runner nodes.",
        "risks_and_disclaimers": "Ensure test outputs are verified in staging prior to production merges."
    },
    "software_factory_prompt_pack": {
        "pack_name": "HOCH Software Factory Orchestration Pack",
        "target_buyer": "Engineering Managers, DevOps Leads, and Product Managers.",
        "pricing_hypothesis": "$799/month per enterprise team.",
        "use_cases": [
            "Develop CI/CD pipelines.",
            "Configure task queues and lock systems."
        ],
        "included_prompt_families": ["Role System Prompt", "Task Execution Prompt", "SOP Prompt"],
        "approved_prompts": [
            {
                "prompt_id": "PB-SOFTWARE-FACTORY-AUTOMATION-ENGINEER-ROLE-SYSTEM-PROMPT-1",
                "family": "Role System Prompt",
                "qa_score": 92,
                "red_team_score": 100
            }
        ],
        "qa_score_summary": {
            "average_score": 92.0,
            "min_score": 92,
            "max_score": 92
        },
        "red_team_summary": {
            "vulnerabilities_found": 0,
            "critical_findings": 0,
            "remediation_status": "VERIFIED_SECURE"
        },
        "sample_workflows": [
            "Dispatch deployment workflow -> Verify queue status -> Confirm production locks are active."
        ],
        "deployment_instructions": "Expose endpoints on internal server networks to permit multi-agent access.",
        "risks_and_disclaimers": "Queue parameters should match available cluster memory bounds."
    }
}

for key, val in packs_data.items():
    file_path = PACKS_DIR / f"{key}.json"
    file_path.write_text(json.dumps(val, indent=2))
    print(f"[+] Wrote {file_path.name}")
