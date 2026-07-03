# Remote Runtime Security Policy

## 1. Network Containment
* Core backend databases, prompt registries, and active engine ports (8000, 1234, 11434) must remain strictly on internal-only Docker network interfaces.
* Only Caddy and cloudflared reverse tunnels face public interfaces.

---

## 2. Authentication & Logging
* Token headers are required for all protected administrative endpoints (e.g. `/relay/status`, `/relay/backup`).
* Access token checks fail closed in case of missing auth headers.
* Secrets are never logged to std-out or disk.
