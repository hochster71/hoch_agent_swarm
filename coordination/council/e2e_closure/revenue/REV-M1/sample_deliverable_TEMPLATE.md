> **SYNTHETIC WORKED EXAMPLE — NOT A REAL ENGAGEMENT.**
> The client, the findings and the 62% score below are ILLUSTRATIVE. They are a structural template
> for the report format, not evidence of work performed. Do NOT present this as a case study.
> The real, verifiable sample assessment is `sample_deliverable.md` — it is our own system, with our
> own open HIGH finding disclosed.

# HELM AI Agent Governance Assessment Report (Sample Deliverable)
**Client:** [REDACTED Enterprise SaaS Provider]  
**Date:** July 14, 2026  
**Status:** Sample Report (Redacted Preview)  
**HELM Assessor:** Lead Governance Architect  

---

## 1. Executive Summary
We performed a technical audit of the Client’s **Autonomous Customer-Support Agent System** (built on CrewAI and hosted in AWS). The assessment evaluated privilege boundaries, threat modeling, and audit log integrity against NIST SP 800-53 Rev. 5 controls.

### Overall Compliance & Safety Score: **62% (POOR / INSUFFICIENT)**
While the application functions well, it exposes the Client to high-risk vectors, specifically in privilege isolation and database access control. 

```
[██████████████░░░░░░░░░] 62% - Current Posture
Target Posture: > 90% (Required for NIST 800-53 Level 2/3)
```

---

## 2. Key Findings & Vulnerabilities

### Finding P-1: Unrestricted Database Write Privileges
* **Severity:** CRITICAL
* **Description:** The customer support agent uses database credentials that allow write operations across all schemas, including transaction histories and user account profiles. A prompt injection could allow an attacker to delete or modify user records.
* **NIST 800-53 Mapping:** AC-3 (Access Enforcement), AC-6 (Least Privilege).
* **Remediation:** Restructure database access to use read-only views for support tools, restricting write capabilities to a separate microservice gated by a human-in-the-loop validation layer.

### Finding E-1: Mutable Audit Logging (No Evidence Integrity)
* **Severity:** HIGH
* **Description:** Agent prompts and tool execution histories are written to standard application logs. These logs are stored in plain text and can be modified or deleted by database administrators or compromised system users.
* **NIST 800-53 Mapping:** AU-9 (Protection of Audit Information).
* **Remediation:** Integrate a write-once ledger (similar to HELM's `verification_ledger.jsonl`) with cryptographic hash validation to seal each execution package.

---

## 3. NIST 800-53 Rev. 5 Gap Matrix (Excerpt)

| Control ID | Control Name | Assessment Status | Observed Gap / Action |
| :--- | :--- | :--- | :--- |
| **AC-3** | Access Enforcement | **PARTIAL** | Agent permissions are not restricted to minimal operations. |
| **AC-6** | Least Privilege | **FAIL** | Write privileges granted to agents unnecessarily. |
| **AU-9** | Protection of Audit Info | **FAIL** | Audit logs are mutable; no tamper-evident verification. |
| **SC-7** | Boundary Protection | **PASS** | Agent container runs inside isolated VPC. |

---

## 4. 30/60/90-Day Remediation Plan

### Days 1 - 30: Isolation & Least Privilege (Immediate Risk Reduction)
1. Revoke the agent's direct database write permissions.
2. Route all DB queries through a hardened read-only API gateway.
3. Configure container-level network rules to block all public internet outbound access except to verified LLM API endpoints.

### Days 31 - 60: Evidence Chain & Audit trail Hardening
1. Build a structured JSONL execution ledger.
2. Implement SHA-256 block hashing for each agent-tool invocation.
3. Export logs to a read-only S3 bucket with Object Lock enabled.

### Days 61 - 90: Automated ConMon & Human Approval Gates
1. Deploy an automated gate that blocks any transaction above $100 until approved by a human agent.
2. Integrate monthly automated compliance checks.
