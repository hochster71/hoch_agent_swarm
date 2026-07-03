# HOCH Prompt Brain — Pilot Launch Checklist

This document details the checklist requirements to verify before initiating any external reviewer or first buyer pilot outreach.

---

## 1. Checklist Categories & Steps

### A. Environment & Runtime Readiness
* **[x] Demo Environment Readiness**: Verify local environment contains all datasets and model configurations.
* **[x] Local Model Readiness**: Assert LM Studio and Ollama local adapters are online with latency < 50ms.
* **[x] Command Center Route Readiness**: Verify `/prototype/prompt-brain` web interface loads cleanly.
* **[x] Demo Workflow Readiness**: Verify all 6 workflows run and complete validation loops.

### B. Buyer Collateral & Disclaimers
* **[x] Buyer-Facing Collateral Readiness**: One-pager, Q&A FAQ, and objection handling files are created.
* **[x] Risk Disclaimer Readiness**: Verify the regulatory limitations disclaimer is attached to all packs.
* **[x] External Evaluator Rubric Readiness**: Confirm the 10-dimension review rubric is accessible to testers.

### C. Compliance & Data Boundaries
* **[x] No-Sensitive-Data Validation**: Verify all files in `/demo_evidence_inputs` contain only synthetic metadata.
* **[x] Human-in-the-Loop Decision Boundary**: Ensure all reports note that AOs, SCAs, and ISSOs retain final authority.

### D. Review Loop & Sales Pipeline
* **[x] Feedback Capture Process**: Reviewer feedback forms and JSONL loggers are initialized.
* **[x] Follow-Up Conversion Plan**: Establish sequence steps to translate pilots into annual contract license sales.
