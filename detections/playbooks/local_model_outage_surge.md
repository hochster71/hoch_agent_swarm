# Playbook: Local Model Outage Surge
## Trigger
Local health checks report multiple local model host failure events.
## Severity
Medium.
## Immediate Actions
1. Query LocalRuntimeSupervisor latency logs.
2. Confirm if the local Ollama/LM Studio services are running.
3. Check host CPU/RAM allocations.
4. Verify network connectivity to local model node IPs.
## Recovery
Restart the local provider server services.
