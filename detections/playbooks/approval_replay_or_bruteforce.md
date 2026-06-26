# Playbook: Approval Replay or Brute Force Attempt
## Trigger
SIEM registers multiple denied, expired, or mismatch approvals from same actor or IP.
## Severity
High.
## Immediate Actions
1. Block the source IP in firewall.
2. Invalidate all pending approvals in prompt approvals table.
3. Terminate affected caller agent sessions.
4. Verify if any high-risk tasks were successfully dispatched in the timeframe.
## Recovery
Restore API access only after manual operator confirmation.
