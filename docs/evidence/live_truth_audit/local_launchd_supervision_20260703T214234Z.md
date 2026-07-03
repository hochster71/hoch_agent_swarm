# macOS launchd Supervision Verification Report

## 1. Overview
- **Timestamp**: `2026-07-03T21:42:34Z`
- **Incident Classification**: `incident_class=infrastructure`
- **Likely Cause of Previous Outage**: Shell/session termination of hand-launched background process.
- **Final Verdict**: **PASS** (Local services successfully migrated to launchd supervision).

---

## 2. launchd Configurations

### com.hoch.has.pert-server.plist
- **Path**: `~/Library/LaunchAgents/com.hoch.has.pert-server.plist`
- **Command**: `/Users/michaelhoch/hoch_agent_swarm/.venv/bin/python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765`
- **KeepAlive**: `SuccessfulExit=false` (restarts on non-zero exit or crash)
- **ThrottleInterval**: `10` seconds (to prevent crash loops)
- **StandardOutPath / StandardErrorPath**: `/tmp/pert_server.log`

### com.hoch.has.live-truth-sidecar.plist
- **Path**: `~/Library/LaunchAgents/com.hoch.has.live-truth-sidecar.plist`
- **Command**: `/Users/michaelhoch/hoch_agent_swarm/.venv/bin/python tools/has_live_truth_sidecar.py`
- **KeepAlive**: `SuccessfulExit=false`
- **ThrottleInterval**: `10` seconds
- **StandardOutPath / StandardErrorPath**: `/Users/michaelhoch/hoch_agent_swarm/logs/has_live_truth_sidecar.log`

---

## 3. Port Binding & Validation Output
- **Bind address**: Bind is strictly locked to loopback (`127.0.0.1`) for both ports. No public ports are exposed.
- **lsof Output**:
```
COMMAND     PID        USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 36524 michaelhoch   10u  IPv4 0x4a107e7e325e2fe6      0t0  TCP localhost:ultraseek-http (LISTEN)
COMMAND     PID        USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 36527 michaelhoch    3u  IPv4 0x6543e3f2681c7562      0t0  TCP localhost:8777 (LISTEN)
```
