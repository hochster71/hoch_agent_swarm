# AG Execution Retry Policy

This document defines the retry, backoff, and recovery rules enforced by the `ag_execution_runner` during autonomous execution tasks.

## Rules and Parameters

1. **Maximum Retries**:
   - Every retryable task is allowed a maximum of **3 retries**.
   - If a task fails 3 times, it is written to the permanent failure ledger (`ag_execution_failures.jsonl`).

2. **Exponential Backoff**:
   - Initial wait: **5 seconds**.
   - Multiplier: **2x** for each subsequent failure (e.g., 5s, 10s, 20s).

3. **Non-Retryable Categories**:
   - Tasks classified under restricted policy categories (`monetization`, `release`, `external_outreach`, `investor_engagement`) are strictly **non-retryable** and fail closed immediately.

4. **Crash Recovery Behavior**:
   - Unhandled exceptions or runner crashes result in the immediate release of the active lease and transitions the task to `FAILED` or `RETRY_PENDING` depending on current attempt count.
