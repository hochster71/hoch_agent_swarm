# Chaos Scenario 7: Evidence Write Failure
 
* **Injected Failure**: Blocked `evidence_writer` adapter using policy configuration.
* **Expected Response**: Task cannot compile evidence, transition state to `blocked` or write incident log.
* **Observed Response**: Action 'write_markdown_evidence' is explicitly forbidden under evidence_writer contract.
* **Runtime State Transition**: Runner blocks execution.
* **Task State Transition**: Task status marked as `blocked`.
* **Recovery Action**: Restored normal adapter contracts.
* **Pass/Fail Result**: **🟢 PASS**
