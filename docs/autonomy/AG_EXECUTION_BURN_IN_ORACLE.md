# AG Execution Burn-In Oracle

This document registers the strict requirements and pass/fail thresholds enforced for the 24x7 autonomy daemon burn-in validation.

## Pre-registered Thresholds

*   **Minimum Wall Clock**: **24 hours**
*   **Target Wall Clock**: **72 hours**
*   **Minimum Real Cycles**: **10 cycles**
*   **Max Duplicate Executions**: **0**
*   **Max Unrecovered Stale Leases**: **0**
*   **Max Missing Proofs**: **0**
*   **Max Unsafe Actions**: **0**
*   **Max Failed Cycle Rate**: **<= 1%**

## Verdict States
*   `ORACLE_READY`: Configured thresholds are validated and ready.
*   `ORACLE_INCOMPLETE`: Target execution hours/cycles have not yet been satisfied.
*   `ORACLE_NO_GO`: One or more zero-tolerance thresholds have been breached.
