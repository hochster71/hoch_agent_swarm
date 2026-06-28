# Playbook: Google Frontier Policy Block
## Trigger
Outbound cloud AI call blocked due to payload filters, budget cap, or missing approvals.
## Severity
High.
## Immediate Actions
1. Inspect the blocked prompt payload for exfiltration attempts or command injections.
2. Verify task scope and operator intent.
3. Pause agent task queue until payload context is determined to be safe.
## Recovery
Manually approve the escalation token if the request is verified as safe.
