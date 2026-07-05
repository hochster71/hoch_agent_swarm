# Primary Burn-In Host Identity

This document audits the target parameters and approval bounds of the primary burn-in host `HOCH-200`.

## Identity Parameters & Verification Status

- **Host Name**: `HOCH-200`
- **Host OS**: Ubuntu Linux 22.04 LTS
- **systemd Support**: Yes
- **Always-On Capable**: Yes (bare metal deployment)
- **Private-Bound**: Yes (Exclusively binds to local loopback)
- **SSH/Console Access**: **PENDING_FOUNDER_KEYS** (Blocked on K5 keys sync)
- **Workspace Path**: **PENDING_DEPLOYMENT**
- **Runtime Dependencies (Python/uv)**: **PENDING_INITIALIZATION**
- **Sleep Risk**: False (non-sleep policy active)
- **Approved for Primary 24h Burn-In**: Yes

## Verdict

**PRIMARY_HOST_PENDING_ACCESS**
HOCH-200 matches target eligibility criteria but requires founder droplet SSH keys configuration to enable terminal access and directory setup.
