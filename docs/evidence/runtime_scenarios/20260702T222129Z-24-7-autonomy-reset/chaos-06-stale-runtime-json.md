# Chaos Scenario 6: Stale Runtime JSON
 
* **Injected Failure**: Modified `helm_runtime_state.json` timestamp to a value 2 hours in the past.
* **Expected Response**: Freshness gate fails, reporting stale heartbeat.
* **Observed Response**: ❌ HELM heartbeat is stale (10760.6s > 60s)
* **Runtime State Transition**: Runner marked as `STALE`/`DEGRADED`.
* **Task State Transition**: Blocks task processing loop.
* **Recovery Action**: Reverted state file backup.
* **Pass/Fail Result**: **🟢 PASS**
