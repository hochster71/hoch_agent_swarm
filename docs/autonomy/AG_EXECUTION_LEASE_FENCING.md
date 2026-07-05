# AG Execution Lease Fencing

This document outlines the design and verification rules for the lease fencing token mechanism, preventing concurrent task mutations or zombie-holder race conditions.

## Fencing Rules

1. **Monotonically Increasing Token**:
   - Each lease acquisition increments the fencing token counter by 1.
   - The token is stamped into the active lease record, execution proof files, and the queue task attributes.

2. **Write Rejection**:
   - The runner rejects task execution if the lease fencing token is stale (i.e. smaller than or equal to the maximum token already recorded in the proof index).

3. **Zombie-Holder Protection**:
   - In case a worker hangs and loses its lease, it cannot commit updates using its old fencing token because the layer enforces monotonically increasing token checks.
