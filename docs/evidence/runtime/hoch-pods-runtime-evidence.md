# HOCH PODS Runtime Evidence Report

**Generated**: 2026-07-02T13:06:08.447968Z  
**Status**: COMPLIANT  

## Active Agent Pods Telemetry

| Pod Name | State | Model | Node | Policy | Freshness | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| Cyber Pod | `EXECUTING` | `openai/gpt-4o` | `Dell-Latitude-9440` | `PASS` | `FRESH` | None |
| QA Pod | `POLICY_CHECK` | `openai/gpt-4o-mini` | `iMac-24` | `PASS` | `FRESH` | None |
| Builder Pod | `TOOL_BOUND` | `openai/gpt-4o` | `M4-MBP` | `PASS` | `FRESH` | None |
| Revenue Pod | `EVIDENCE_WRITING` | `openai/gpt-4o` | `M5-Pro-MBP` | `BLOCKED` | `FRESH` | Stripe integration code is missing or unverified |
| Audit Pod | `SUMMONING` | `openai/gpt-4o-mini` | `M5-Pro-MBP` | `PASS` | `FRESH` | None |
| Research Pod | `DORMANT` | `openai/gpt-4o` | `M4-MBP` | `FAIL` | `DEGRADED` | Project repository path does not exist on disk |
| Deploy Pod | `BLOCKED` | `openai/gpt-4o` | `M5-Pro-MBP` | `BLOCKED` | `FRESH` | Deployment descriptor (vercel.json) is missing |
