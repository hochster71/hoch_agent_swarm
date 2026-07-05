# HOCH-200 SSH Access Status

This document records the results of SSH access parameters and connection attempts to the primary always-on host.

## Access Audits & Diagnostics

- **SSH Config Entry Present**: True
- **Key File Exists Locally**: True
- **Connection Test Status**: **SUCCESS**
- **Remote Hostname**: `hoch-relay-001`
- **Remote User**: `root`
- **Remote Operating System**: `Ubuntu Linux 6.8.0-134-generic x86_64`
- **Uptime**: up 12 days
- **Network Boundaries**: LAN loopback + Tailscale (verified)
- **Wildcard Bindings Check**: UFW active (no wildcard bindings exposed)

## Verdict

**HOCH200_SSH_ACCESS_GO**
SSH configuration target credentials have been verified. Connection tests succeeded.
