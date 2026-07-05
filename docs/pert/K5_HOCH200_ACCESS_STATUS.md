# K5 HOCH-200 Access Status

This document tracks SSH connection readiness and access verification evidence for the primary always-on host.

## Control Node Verified Identity

- **Hostname**: `Michaels-MacBook-Pro.local`
- **LAN IP**: `10.0.0.10`

---

## Access Verification Details

- **Host Name / Target**: `hoch-relay-001` (HOCH-200)
- **Public SSH Address**: `root@50.116.41.183`
- **Tailscale Private Address**: `100.87.18.15`
- **OS Details**: `Ubuntu Linux 6.8.0-134-generic x86_64`
- **Relay Health Endpoint**: `http://100.87.18.15:3012/health` (HTTP 200 OK)
- **Relay Dashboard Endpoint**: `http://100.87.18.15:3012/` (HTTP 200 OK)
- **Worker Registry**: `HAS-WORKER-RELAY-001` (ONLINE)
- **Connection Test Status**: **SUCCESS**

## Verdict

**K5_ACCESS_VERIFIED**
The primary host has been reached and confirmed. SSH connection has succeeded, and system environment verification shows a clean virtual environment and active daemon operation.
