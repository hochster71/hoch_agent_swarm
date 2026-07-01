# HOCH PODS Dynamic Compute Scheduler Evidence

**Scheduler Run Time**: 2026-07-01T22:15:23.044333+00:00Z  
**Health Telemetry Freshness**: FRESH  

## Pod Placement Assignments

| Pod ID | Pod Name | State | Assigned Node | Schedule Status | Workload | Secrets | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pod-cyber` | Cyber Pod | `EXECUTING` | **M5-Pro-MBP** | **SCHEDULED** | security | 🔒 YES | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 1. |
| `pod-qa` | QA Pod | `POLICY_CHECK` | **M5-Pro-MBP** | **SCHEDULED** | quality | ✖️ NO | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 2. |
| `pod-builder` | Builder Pod | `TOOL_BOUND` | **M5-Pro-MBP** | **SCHEDULED** | engineering | ✖️ NO | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 1. |
| `pod-revenue` | Revenue Pod | `EVIDENCE_WRITING` | **None** | **BLOCKED_COMPUTE** | monetization | ✖️ NO | Scheduling blocked. Constraints violated on all candidate nodes: M5-Pro-MBP: Tool mismatch: node lacks required tools ['stripe-cli', 'curl'].; M4-MBP: Workload mismatch: pod domain 'monetization' not allowed on node.; iMac-24: Workload mismatch: pod domain 'monetization' not allowed on node.; Dell-Neo: Workload mismatch: pod domain 'monetization' not allowed on node.; Local-Models: Workload mismatch: pod domain 'monetization' not allowed on node.; Docker-Runtime: Workload mismatch: pod domain 'monetization' not allowed on node.; Optional-Remote-VPS: Workload mismatch: pod domain 'monetization' not allowed on node. |
| `pod-audit` | Audit Pod | `SUMMONING` | **None** | **BLOCKED_COMPUTE** | governance | ✖️ NO | Scheduling blocked. Constraints violated on all candidate nodes: M5-Pro-MBP: Tool mismatch: node lacks required tools ['sqlite3-cli', 'sha256sum'].; M4-MBP: Workload mismatch: pod domain 'governance' not allowed on node.; iMac-24: Workload mismatch: pod domain 'governance' not allowed on node.; Dell-Neo: Workload mismatch: pod domain 'governance' not allowed on node.; Local-Models: Workload mismatch: pod domain 'governance' not allowed on node.; Docker-Runtime: Workload mismatch: pod domain 'governance' not allowed on node.; Optional-Remote-VPS: Workload mismatch: pod domain 'governance' not allowed on node. |
| `pod-research` | Research Pod | `DORMANT` | **None** | **DORMANT** | research | ✖️ NO | Pod is DORMANT. No compute resources allocated. |
| `pod-deploy` | Deploy Pod | `BLOCKED` | **M5-Pro-MBP** | **SCHEDULED** | operations | 🔒 YES | Assigned to M5-Pro-MBP. Reason: Compatible. Node status: ONLINE, matched tools: 1. |

## Secure Scheduling Controls Compliance
- **Local-First Enforced**: Node preferences favor physical local endpoints.
- **Least Privilege Network Routing**: Network zones map directly to the zero-trust microsegmentation design.
- **Fail-Closed Compute Blocking**: Any pod matching model/tool/secret policy deficits falls back to `BLOCKED_COMPUTE` instead of cloud execution.
