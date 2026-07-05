# HOCH PODS Dynamic Compute Scheduler Evidence

**Scheduler Run Time**: 2026-07-05T20:02:35.519148+00:00Z  
**Health Telemetry Freshness**: FRESH  

## Pod Placement Assignments

| Pod ID | Pod Name | State | Assigned Node | Schedule Status | Workload | Secrets | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pod-cyber` | Cyber Pod | `EXECUTING` | **M5-Pro-MBP** | **SCHEDULED** | security | 🔒 YES | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 4. |
| `pod-qa` | QA Pod | `POLICY_CHECK` | **M5-Pro-MBP** | **SCHEDULED** | quality | ✖️ NO | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 2. |
| `pod-builder` | Builder Pod | `TOOL_BOUND` | **M5-Pro-MBP** | **SCHEDULED** | engineering | ✖️ NO | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 1. |
| `pod-revenue` | Revenue Pod | `EVIDENCE_WRITING` | **M5-Pro-MBP** | **SCHEDULED** | monetization | 🔒 YES | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 1. |
| `pod-audit` | Audit Pod | `SUMMONING` | **M5-Pro-MBP** | **SCHEDULED** | governance | ✖️ NO | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 2. |
| `pod-research` | Research Pod | `DORMANT` | **None** | **DORMANT** | research | ✖️ NO | Pod is DORMANT. No compute resources allocated. |
| `pod-deploy` | Deploy Pod | `BLOCKED` | **M5-Pro-MBP** | **SCHEDULED** | operations | 🔒 YES | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 2. |

## Secure Scheduling Controls Compliance
- **Local-First Enforced**: Node preferences favor physical local endpoints.
- **Least Privilege Network Routing**: Network zones map directly to the zero-trust microsegmentation design.
- **Fail-Closed Compute Blocking**: Any pod matching model/tool/secret policy deficits falls back to `BLOCKED_COMPUTE` instead of cloud execution.
