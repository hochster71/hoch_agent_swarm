# HOCH PODS Compliant Topology

This document details the network topology, boundaries, and security trust zones established for **HOCH PODS** in compliance with zero-trust design standards and NIST SP 800-207.

---

## 1. Node Trust Zones

The HOCH PODS network architecture is segmented into seven logical trust zones. Boundaries are enforced via OS firewalls, Tailscale ACLs, Docker networks, and application-level gateway authentication.

```
+---------------------------------------------------------------------------------------------------+
|                                      COMPLIANT TOPOLOGY OVERVIEW                                  |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [Operator Zone] ----> [Management Zone] ----> [Model Zone]                                       |
|  (Michael Hoch)        (PERT/HASF API)         (LM Studio/Ollama)                                 |
|                               |                                                                   |
|                               v                                                                   |
|                         [Pod Runtime Zone] ----> [Tool Execution Zone]                            |
|                         (Secure Pods)            (CLI, Playwright, DAST)                          |
|                               |                                                                   |
|                               v                                                                   |
|                         [Evidence Zone] <------+                                                  |
|                         (Ledger, Markdown)     |                                                  |
|                                                |                                                  |
|  [Optional Remote Zone] (Cloudflare Tunnels) --+                                                  |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

### 1.1 Operator Zone
- **Entities**: Michael Hoch (Founder/Admin), authorized UI client sessions.
- **Controls**: Multi-Factor Authentication (MFA), local device authentication, administrative email validation matching the `EPIC_FURY_ADMIN_EMAILS` rule.
- **Boundary**: Extends to local UI browsers and authorized terminal sessions.

### 1.2 Management Zone
- **Entities**: HASF Control Plane, PERT server, Uvicorn API gateways.
- **Controls**: Strict API keys, CORS constraints, localhost binding limits (`127.0.0.1:8765`), and secure session cookies.
- **Boundary**: Primarily resides on the M5 Pro MBP primary control node.

### 1.3 Model Zone
- **Entities**: LM Studio (`localhost:1234`), Ollama (`localhost:11434`), local Vector DBs.
- **Controls**: Bound strictly to local loopback adapters. No public routing is allowed. Token-based API authorization is enforced where supported.
- **Boundary**: Spans M5 Pro and M4 MBP local compute nodes.

### 1.4 Pod Runtime Zone
- **Entities**: Ephemeral Docker containers, isolated agent runtime processes, active Pod registries.
- **Controls**: No-root container runtime, cpu/memory constraints, and policy validation prior to startup.
- **Boundary**: Resides in isolated VM enclaves and Docker daemon spaces.

### 1.5 Tool Execution Zone
- **Entities**: Git/GitHub, Playwright test scripts, SAST/DAST security tooling (Trivy, Semgrep, OWASP ZAP).
- **Controls**: Scoped file access, read-only overlays, and tool capability validation gates.
- **Boundary**: Active on iMac 24, Dell Latitude 9440, and local test runtimes.

### 1.6 Evidence Zone
- **Entities**: `swarm_ledger.db` (SQLite), Markdown evidence registries, ConMon freshness trackers.
- **Controls**: Write-once append-only operations, automated SHA-256 integrity checksums, and strict file write permissions.
- **Boundary**: Centralized under `hoch_agent_swarm/has_live_project_tracker/data/` and `docs/evidence/`.

### 1.7 Optional Remote Zone
- **Entities**: Remote Docker Host, Cloud / VPS instances.
- **Controls**: Cloudflare Tunnels (Zero-Trust), Tailscale network keys, fall-closed firewalls block all implicit traffic.
- **Boundary**: Public networks bridged via encrypted point-to-point overlays.

---

## 2. Default-Deny Protocol Flow

Any communication crossing a zone boundary must conform to the following verification pattern:
1. **Request Intake**: A Pod or Node requests access to a model or tool across zones.
2. **Policy Evaluation**: The HASF Policy engine checks the `hoch_pods_registry.json` for mapping allowance (`allowed_models`, `allowed_tools`, `allowed_nodes`).
3. **Execution Gate**: If verified, a short-lived execution token or path is exposed. If not verified, the request is logged as a violation and transitioned to `BLOCKED`.
