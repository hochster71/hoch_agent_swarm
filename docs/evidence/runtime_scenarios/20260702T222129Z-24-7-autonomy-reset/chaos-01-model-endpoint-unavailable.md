# Chaos Scenario 1: Model Endpoint Unavailable

* **Injected Failure**: Target inference port offline.
* **Command Used**: `ssh root@100.87.18.15 "systemctl stop docker"` (which stops the native model container).
* **Expected Response**: Watchdog downgrades native model adapter status to `DEGRADED`.
* **Observed Response**: Watchdog registry updated to `"status": "DEGRADED"` inside `helm_adapter_registry.json`.
* **Adapter/Runtime State Transition**: Transitioned status from `ONLINE` to `DEGRADED`.
* **Task State Transition**: Task execution fallback logic triggered to route to secondary port or remain queued.
* **Pass/Fail Result**: **🟢 PASS**
* **Recovery Evidence**: Starting docker daemon restored the model status to `ONLINE`.
