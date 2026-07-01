# HASF AI Authority Boundaries

This document defines the clear lines of authority between autonomous AI execution and mandatory human approval gates.

## 1. Autonomous Execution Allowed (Without Human Approval)
AI agents and executives may perform the following tasks autonomously:
- Read-only operations, audit log analysis, and telemetry gathering.
- Internal pod scheduling and workload matching based on node health.
- Local sandboxed test executions and unit testing.
- Telemetry compilation and data-source sync.
- Verification checks and static analysis.

## 2. Mandatory Human Approval Required (Veto Gate: Michael Hoch)
The following actions **MUST NOT** be executed without explicit final approval from Michael Hoch:
- Deployment of code to production (especially Stripe monetization/billing systems).
- Destructive actions on local or remote nodes (file deletions, container termination).
- Allocation of financial budgets or change in API configurations.
- Pricing model modifications and changes in ARPU parameters.
- Re-tagging of candidate releases.
- Any action with a risk score greater than 70 (high-risk).

## 3. Compliance Boundaries
- **Zero Secrets Leakage**: No credentials may ever be committed to Git.
- **Fail-Closed Policy**: If billing integrations are unverified, monetization flows must fail-closed to prevent unauthorized access.
