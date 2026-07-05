# AG Execution Failure Injection

This document defines the failure injection schedule, expected recovery behaviors, and verification checks.

## Failure Injection Scenarios

1. **Forced Lease Expiry**:
   - Injection: Active lease timestamp set to expired.
   - Recovery: Next daemon cycle calls `check_stale_leases` and unblocks queue execution.

2. **Duplicate Task Insert**:
   - Injection: Appends two identical pending tasks.
   - Recovery: Runner locks task queue using fencing token validation.

3. **Operator Hold Flip**:
   - Injection: Toggles hold active flag to true.
   - Recovery: Loop skips running runner tasks and updates state status.
