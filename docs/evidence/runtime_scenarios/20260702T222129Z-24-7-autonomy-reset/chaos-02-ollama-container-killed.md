# Chaos Scenario 2: Ollama Container Killed

* **Injected Failure**: Ollama container killed.
* **Command Used**: `ssh root@100.87.18.15 "docker kill ollama"`
* **Expected Response**: Container stops, watchdog detects port 11434 unreachable, and marks native model as degraded.
* **Observed Response**: Port 11434 checks timed out; watchdog registry updated to `DEGRADED`.
* **Adapter/Runtime State Transition**: Transitioned status from `ONLINE` to `DEGRADED`.
* **Task State Transition**: Execution fallback triggered to route `task-002` via the LM Studio tunnel.
* **Pass/Fail Result**: **🟢 PASS**
* **Recovery Evidence**: Container restarted automatically due to `--restart always` policy within seconds.
