# Phase PR15 — Controlled Staging Validation

You are operating inside the hoch-agent-swarm repository on branch integration/visual-control-plane-local-v1.

Mission:
Validate the controlled staging environment and verify the simulated activation.

Staging Execution:
- Run all staging validation tests and collect execution logs.

Blocked Actions (MUST STOP):
- No production deployment
- No git push
- No main branch merge
- No production secrets
- No live external service bindings
- No prompt execution against live systems
- No approval execution
- No external publication
- No actual ATO claim
