# Playbook: TEST Approval Misuse
## Trigger
Active use of a test-sourced approval in a non-test environment.
## Severity
Critical.
## Immediate Actions
1. Audit active agent runs.
2. Expire all active test-sourced approvals via POST `/api/v1/prompts/expire-test`.
3. Terminate affected caller agent sessions.
## Recovery
Re-run tests and verify operator session tokens.
