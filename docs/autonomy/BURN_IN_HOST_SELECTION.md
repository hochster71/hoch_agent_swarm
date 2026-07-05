# Burn-In Host Selection Gate

This document evaluates always-on hosts and records the launch selection decision.

## Host Evaluation Matrix

| Host Target | Always-On | Sleep Risk | Supervisor | Network | Credentials | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **HOCH-200** | Yes | Low | `systemd` | Local Loopback | `PENDING_KEYS` | **HOST_SELECTED** (Primary) |
| **DigitalOcean VPS** | Yes | Low | `systemd` | Local Loopback | `PENDING_KEYS` | **HOST_SELECTED** (Backup) |
| **Developer MacBook** | No | High | `launchd` | Local Loopback | `READY` | **HOST_NO_GO** (Dev-Only) |

## Selection Decision

**HOCH-200** has been selected as the primary always-on runtime environment for the 24h burn-in validation. Temporary local MacBooks are designated as `HOST_NO_GO` for the formal 24h run to avoid sleep/battery failure risks. Awaiting founder credential configuration (K1-K6) to proceed with droplet initialization.
