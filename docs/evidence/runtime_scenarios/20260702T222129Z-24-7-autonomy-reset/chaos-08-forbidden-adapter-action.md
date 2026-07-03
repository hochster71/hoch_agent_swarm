# Chaos Scenario 8: Forbidden Adapter Action
 
* **Injected Failure**: Attempted forbidden action `git_push_force_main`.
* **Expected Response**: Policy engine blocks action before execution.
* **Observed Response**: Action 'git_push_force_main' is explicitly forbidden under github contract.
* **Runtime State Transition**: Blocks runner action execution.
* **Task State Transition**: Task status marked as `blocked`.
* **Recovery Action**: Reverted attempt; policy rule remains permanently active.
* **Pass/Fail Result**: **🟢 PASS**
