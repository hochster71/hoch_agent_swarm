# HOCH Compute Node Health Authority Telemetry Evidence

**Collected At**: 2026-07-01T22:37:15.426097+00:00Z  
**Local Hostname**: `Michaels-MacBook-Pro.local`  
**Operating System**: `darwin`  

## Compute Node Status Registry

| Node ID | Name | Role | Status | CPU Cores | Memory | Network Zone | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `m5-pro-mbp` | M5-Pro-MBP | Management Zone | **ONLINE** | 15 | 24.0 GB | Management Zone | Primary local controller fully responsive. |
| `m4-mbp` | M4-MBP | Pod Runtime Zone | **DEGRADED** | 0 | 0 GB | Pod Runtime Zone | Node offline. Daemon inactive. |
| `imac-24` | iMac-24 | Pod Runtime Zone | **DEGRADED** | 0 | 0 GB | Pod Runtime Zone | Node offline. Daemon inactive. |
| `dell-neo` | Dell-Neo | Pod Runtime Zone | **DEGRADED** | 0 | 0 GB | Pod Runtime Zone | Node offline. Daemon inactive. |
| `local-models` | Local-Models | Model Zone | **ONLINE** | 0 | 0 GB | Model Zone | LM Studio / Ollama port responsive. |
| `docker-runtime` | Docker-Runtime | Tool Execution Zone | **ONLINE** | 0 | 0 GB | Tool Execution Zone | Local docker daemon responsive. |
| `optional-remote-vps` | Optional-Remote-VPS | Optional Remote Zone | **UNKNOWN** | 0 | 0 GB | Optional Remote Zone | No telemetry ping response. Manual verification required. |

## Local Host System Checks

| Command / Tool | Detected |
| --- | --- |
| `docker` | ✔️ YES |
| `node` | ✔️ YES |
| `npm` | ✔️ YES |
| `python` | ✔️ YES |
| `git` | ✔️ YES |
| `playwright` | ✔️ YES |
| `ollama/lmstudio ports` | ✔️ YES |

## Zero Trust Control Compliance
- **System integrity**: Local daemon scans system platform and environment configuration.
- **No spoofing**: Remote/manual nodes are never marked online without responsive daemon heartbeats.
