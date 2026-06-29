# Fake-Completion Prevention Playbook

Agents often self-certify their work is "done" or "production ready" when gaps still exist.

## The Defense

1. **Strict Terms Block**: Blacklist claims like "100% complete", "verified", or "secure" unless backed by Runtime Truth.
2. **Closeout Authority**: Only the `scripts/promptops_gate.sh` and related telemetry verification scripts can authorize task closure.
3. **Evidence Validation**: All deliverables must write raw verification logs to a stamped file under `docs/evidence/`.
