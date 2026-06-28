# HOCH Agent Swarm Detection Engineering Doctrine
## Principle
Every governed runtime action must be observable, queryable, and alertable.
Detection rules are release artifacts. They must be versioned, tested, and mapped to QA evidence.
## Telemetry Sources
- prompt_usage_ledger
- prompt_approvals
- skill_audit
- audit/model_routing.jsonl
- audit/runtime_process_events.jsonl
- audit/local_outage_queue.jsonl
- audit/detection_events.jsonl
## Required Detection Families
1. DELTA tier privilege escalation attempts.
2. Approval replay and brute-force attempts.
3. TEST approval misuse.
4. Medium-risk rationale evasion.
5. Google frontier blocked payloads.
6. Local model outage surge.
7. Unregistered skill spam.
8. Unexpected paid escalation use.
9. Audit log tamper attempt.
10. Runtime process failure storm.
## Rule Lifecycle
1. Detection rule created.
2. Fixture created.
3. Unit/contract test added.
4. QA evidence matrix updated.
5. Playbook mapped.
6. CI pipeline validates rule presence.
