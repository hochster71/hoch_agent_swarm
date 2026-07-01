# Evidence: Compute Swarm Scheduler & Resource Utilization (RC33)

## Summary of Verification Gates
All security invariants are preserved while the Swarm Scheduler routes tasks based on capabilities:
- **Local primary worker remains primary runtime node.**
- **Relay node `HAS-WORKER-RELAY-001` remains secure (public 3012 closed).**
- **Tasks matched to worker profiles dynamically.**
- **High-risk tasks paused for operator approval.**

## Verification Run Metrics
```json
{
  "scheduler_state": "ACTIVE",
  "utilization_percent": 20.0,
  "active_workers_count": 1,
  "total_workers_count": 5,
  "cores_allocated": 2,
  "memory_allocated_gb": 4.0
}
```

## E2E Playwright Suite Results
```text
Running 2 tests using 1 worker

  ✓  1 [antigravity-chromium] › tests/e2e/rc33-compute-utilization.spec.ts:5:7 › RC33 Compute Utilization Swarm Scheduler E2E tests › navigates to PERT Command Center and validates Swarm Scheduler panel and metrics (349ms)
  ✓  2 [antigravity-chromium] › tests/e2e/rc33-compute-utilization.spec.ts:49:7 › RC33 Compute Utilization Swarm Scheduler E2E tests › proves that public port 3012 remains unreachable (HOCH-200 constraint) (2.0s)

  2 passed (2.8s)
```
