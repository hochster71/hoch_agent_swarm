# AG Execution Supervision Proof

This document provides evidence and validation proofs of the process supervision and relaunch capabilities of the `ag_execution_daemon.py`.

## Supervision Rules

1. **Process Supervision**:
   - The daemon runs under systemd (`Restart=on-failure`) or launchd (`KeepAlive/SuccessfulExit=false`) process supervisors.
   - Any unhandled crash or process termination triggers auto-relaunch within 15 seconds.

2. **Relaunch Recovery Check**:
   - Verified by `ag_execution_supervision_test.py` which terminates the active PID and checks for process recovery under a new PID.
