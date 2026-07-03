# Chaos Scenario 10: GitHub/Vercel Adapter Failure
 
* **Injected Failure**: Simulated vercel adapter failure by querying forbidden release action.
* **Expected Response**: Blocked action to prevent security compromise; error logged without token leakage.
* **Observed Response**: Action 'delete_project' is explicitly forbidden under vercel contract.
* **Runtime State Transition**: Degraded/Blocked adapter state.
* **Task State Transition**: Task status marked as `blocked`.
* **Recovery Action**: Reverted task state.
* **Pass/Fail Result**: **🟢 PASS**
