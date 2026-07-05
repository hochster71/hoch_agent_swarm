# HOCH-200 Remote Proof Commands

This document contains standard commands that must be executed on `HOCH-200` to verify system identity and private configuration states.

---

## Command Matrix

### 1. Identity & OS Audits
Verify host platform parameters:
```bash
hostname
uname -a
cat /etc/os-release
```

### 2. Workspace & Runtime Checks
Verify directories and execution environments:
```bash
pwd
[ -d "/Users/michaelhoch/hoch_agent_swarm" ] && echo "EXISTS"
python3 --version
uv --version
```

### 3. systemd & Script Assets
Verify daemon files and services:
```bash
systemctl --version
[ -f "/etc/systemd/system/hoch-ag-execution-daemon.service" ] && echo "INSTALLED"
[ -f "scripts/ag_execution_daemon.py" ] && echo "DAEMON EXISTS"
```

### 4. Networking & Exposure Checks
Verify that no services are listening on public interfaces:
```bash
# Check loopback bindings
ss -tulpn | grep 127.0.0.1
# Ensure no wildcard / public listeners are active
ss -tulpn | grep -E '0.0.0.0|\*'
```
