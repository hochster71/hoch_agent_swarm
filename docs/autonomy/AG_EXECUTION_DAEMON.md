# AG Execution Daemon

This document describes the design, heartbeat format, state properties, and override controls for the 24x7 autonomy daemon.

## Runtime Loop

1. **Cycle Polling**:
   - The daemon runs a loop periodically (default every 60 seconds, or 5 seconds in test mode).
   - In each cycle, it updates its heartbeat state and checks operator hold constraints.

2. **Runner Invocation**:
   - Executes `ag_execution_runner.py` if AG execution is allowed and no operator hold is present.
   - Summarizes task outcomes and appends rows to `ag_execution_burn_in_ledger.jsonl`.

3. **CI/Test Relaunch Safety**:
   - Uses `DAEMON_MAX_CYCLES` environment variable to cap execution runs safely in test modes, preventing daemon process orphan runs.
