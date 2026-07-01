# Runbook: Failover & Secondary VPS Promotion

## 1. Failover Mechanism
The high-availability heartbeat checking is orchestrated by `scripts/failover_check.sh` running on the secondary VPS:
- Pings the primary local host endpoint `/api/v1/operator/health`.
- If 3 consecutive checks fail, it executes the failover promotion hook.

---

## 2. Automatic Failover Drill
To simulate a network or host failure, run:
```bash
bash scripts/failover_check.sh
```
If the primary server is unreachable (or simulating offline via stopping `hoch-app`), the VPS will execute `failover_promote_secondary.sh`.

---

## 3. Manual Failover/Promotion
To manually force promote the secondary VPS to active control mode:
```bash
bash scripts/failover_promote_secondary.sh
```
To restore the primary local server back to active mode after fixing the outage, toggle it back via the UI dashboard button "Toggle Failover Sim", or run the healthcheck script:
```bash
bash scripts/healthcheck_24_7.sh
```

---

## 4. Recovering from Failover State
Once the primary local server is online:
1. Verify Docker container status:
   ```bash
   docker ps
   ```
2. Re-route the Cloudflare tunnel mapping back to the primary local port `8086`.
3. Reset the status registry using the health check script.
