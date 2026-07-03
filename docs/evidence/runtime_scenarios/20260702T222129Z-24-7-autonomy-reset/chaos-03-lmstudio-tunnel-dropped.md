# Chaos Scenario 3: LM Studio Tunnel Dropped

* **Injected Failure**: Reverse SSH port forwarding tunnel terminated.
* **Command Used**: Local terminal `killall ssh` (killing the reverse forward session).
* **Expected Response**: Watchdog registers `lmstudio` adapter port 1234 unreachable, updating state to `DEGRADED`.
* **Observed Response**: Probe returned connection error; watchdog updated status to `DEGRADED`.
* **Adapter/Runtime State Transition**: Transitioned status from `ONLINE` to `DEGRADED`.
* **Task State Transition**: The runner routed heavy tasks to the native model fallback tier rather than attempting tunnel queries.
* **Pass/Fail Result**: **🟢 PASS**
* **Recovery Evidence**: Restoring the tunnel command recovered the status back to `ONLINE`.
