# Playbook: DELTA Tier Privilege Escalation Attempt
## Trigger
DELTA caller attempts high-risk capability or receives non-denied verdict.
## Severity
Critical.
## Immediate Actions
1. Disable DELTA tier routing.
2. Revoke affected node credentials.
3. Set escalation.enabled=false.
4. Rotate GOOGLE_API_KEY if frontier escalation was touched.
5. Pull runtime process events for the last 30 minutes.
6. Preserve audit DB and JSONL logs.
7. Restart backend after config lockdown.
## Recovery
Re-enable only after skill registry and caller profile verification.
