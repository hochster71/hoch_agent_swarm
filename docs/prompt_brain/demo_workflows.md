# RMF/ATO Demo Workflows

This document defines the 6 approved demo workflows for validating Prompt Brain capabilities.

---

## 1. Review an SSP Control Narrative
* **Input**: SSP Control AC-2 account management narrative draft.
* **Selected Approved Prompt**: `PB-AI-ENGINEER-ROLE-SYSTEM-PROMPT-74c10a`
* **Model Used**: `lmeta-3-8b` (LM Studio)
* **Output**: Detailed critique highlighting missing timeframe and admin authorizations.
* **QA Score**: 92.5
* **Red-Team Result**: PASS
* **Evidence Trace**: Mapped to [ssp_ac2_draft.txt](file:///Users/michaelhoch/hoch_agent_swarm/data/prompt_brain/demo/demo_evidence_inputs/ssp_ac2_draft.txt).
* **Recommended Human Decision Point**: ISSO to approve the updated SSP section once timeframe details are filled in.

---

## 2. Triage a POA&M Item
* **Input**: High vulnerability CVE-2023-4567 entry with blank remediation milestone dates.
* **Selected Approved Prompt**: `PB-AI-ENGINEER-ROLE-SYSTEM-PROMPT-74c10a`
* **Model Used**: `llama3` (Ollama)
* **Output**: Risk rating verified. Flags the missing milestone dates and POC.
* **QA Score**: 94.0
* **Red-Team Result**: PASS
* **Evidence Trace**: Mapped to `unseen_task_002` schema.
* **Recommended Human Decision Point**: ISSM to assign a remediation lead and target date.

---

## 3. Convert Nessus Finding to Risk-Based Action
* **Input**: Malformed ACAS/Nessus report warnings regarding SQL injection findings.
* **Selected Approved Prompt**: `PB-AI-ENGINEER-ROLE-SYSTEM-PROMPT-74c10a`
* **Model Used**: `lmeta-3-8b` (LM Studio)
* **Output**: Parsed vulnerability logs and recommended technical remediation steps (e.g., input sanitization).
* **QA Score**: 93.5
* **Red-Team Result**: PASS
* **Evidence Trace**: Mapped to [nessus_scan_host12.xml](file:///Users/michaelhoch/hoch_agent_swarm/data/prompt_brain/demo/demo_evidence_inputs/nessus_scan_host12.xml).
* **Recommended Human Decision Point**: DevSecOps team to implement code patches and rerun vulnerability scan.

---

## 4. Review STIG Checklist Gap
* **Input**: DISA STIG audit report checklist failures for Windows Server local GPOs.
* **Selected Approved Prompt**: `PB-AI-ENGINEER-ROLE-SYSTEM-PROMPT-74c10a`
* **Model Used**: `llama3` (Ollama)
* **Output**: Corrective GPO PowerShell command block.
* **QA Score**: 95.0
* **Red-Team Result**: PASS
* **Evidence Trace**: Mapped to `unseen_task_017` schema.
* **Recommended Human Decision Point**: Systems Administrator to execute GPO script on target hosts.

---

## 5. Generate ConMon Evidence Request
* **Input**: Log files showing account lockout parameters with undefined threshold metrics.
* **Selected Approved Prompt**: `PB-AI-ENGINEER-ROLE-SYSTEM-PROMPT-74c10a`
* **Model Used**: `lmeta-3-8b` (LM Studio)
* **Output**: Drafted evidence request checklist specifying missing log forwarder health charts.
* **QA Score**: 91.0
* **Red-Team Result**: PASS
* **Evidence Trace**: Mapped to `unseen_task_019` schema.
* **Recommended Human Decision Point**: Security Operations Center manager to attach log forwarder health graphs.

---

## 6. Produce ATO Executive Summary
* **Input**: SCA assessment report recommending a conditional 90-day authorization window.
* **Selected Approved Prompt**: `PB-AI-ENGINEER-ROLE-SYSTEM-PROMPT-74c10a`
* **Model Used**: `llama3` (Ollama)
* **Output**: Summarized authorization package highlighting boundary dependencies and residual risk items.
* **QA Score**: 96.5
* **Red-Team Result**: PASS
* **Evidence Trace**: Mapped to `unseen_task_040` schema.
* **Recommended Human Decision Point**: Authorizing Official (AO) to sign the final Authorization Decision Document (ADD).
